"""Trusted foreground callbacks with private durable state, not an OS sandbox."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import fcntl
import hashlib
import json
import math
import os
import stat
import time

from tools.finding_ledger import context as validate_context, identity
from tools.goal_graph import GoalGraphRejected, demand, validate_definition
from tools.native_flow import FlowRejected, digest, relative


@dataclass(frozen=True)
class Handler:
    run: object
    identity: str  # Caller binds actual adapter code/config; never a credential.


def products(workspace, declared):
    demand(workspace.is_dir() and not workspace.is_symlink(), 'invalid product workspace')
    found, total = {}, 0
    for directory, dirs, files in os.walk(workspace, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            try:
                relative(path.relative_to(workspace).as_posix())
            except FlowRejected as exc:
                raise GoalGraphRejected('unsafe product path') from exc
            demand(not path.is_symlink(), 'linked product')
            mode = path.stat().st_mode
            demand(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'special product')
        for name in files:
            path = Path(directory) / name
            relative_name = path.relative_to(workspace).as_posix()
            demand(relative_name in declared, 'undeclared product')
            total += path.stat().st_size
            demand(total <= 8 * 1024 * 1024 and path.stat().st_nlink == 1, 'oversized or aliased products')
            found[relative_name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                    'mode': stat.S_IMODE(path.stat().st_mode)}
    return found


class GoalGraphRun:
    def __init__(self, definition, handlers, context, run_root, *, budget_seconds,
                 deadline=None, resume=False, pause_after=None, clock=time.time):
        self.definition = validate_definition(definition)
        validate_context(context)
        demand(type(budget_seconds) in (int, float) and math.isfinite(budget_seconds)
               and 0 < budget_seconds <= 3600, 'finite explicit Graph budget required')
        demand(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline) and deadline > 0,
               'finite deadline required')
        self.nodes = {n['id']: n for n in self.definition['nodes']}
        needed = {n['handler'] for n in self.nodes.values() if n['handler'] is not None}
        demand(isinstance(handlers, dict) and set(handlers) == needed, 'exact admitted handler registry required')
        for handler in handlers.values():
            demand(isinstance(handler, Handler) and callable(handler.run), 'registered Handler required')
            identity(handler.identity)
        demand(pause_after is None or pause_after in self.nodes, 'unknown pause boundary')
        self.context, self.handlers = deepcopy(context), dict(handlers)
        self.root = Path(run_root).resolve()
        repository = Path(__file__).resolve().parents[1]
        demand(not self.root.is_relative_to(repository) and not repository.is_relative_to(self.root), 'private run root outside repository required')
        self.resume, self.pause_after, self.clock = resume, pause_after, clock
        self.policy = {'budget_seconds': budget_seconds, 'deadline': deadline,
                       'handlers': {name: handler.identity for name, handler in handlers.items()}}
        self.controller_id = digest({name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                     for name in ('goal_graph.py', 'goal_graph_run.py')})
        if resume:
            self._read()  # Admission before creating a lock in an unrelated directory.
        else:
            demand(not self.root.exists(), 'new run root required')
        self.state = None

    def _read(self):
        path = self.root / 'state.json'
        demand(self.root.is_dir() and not path.is_symlink() and path.is_file()
               and path.stat().st_size <= 16 * 1024 * 1024, 'bounded private checkpoint required')
        data = json.loads(path.read_text())
        demand(isinstance(data, dict) and data.get('kind') == 'goal_graph_run'
               and data.get('version') == 1, 'not a goal Graph checkpoint')
        return data

    def _now(self):
        value = self.clock()
        demand(type(value) in (int, float) and math.isfinite(value)
               and value >= self.state.get('last_at', 0), 'clock moved backwards')
        self.state['last_at'] = value
        return value

    def _save(self):
        path = self.root / 'state.json.tmp'
        descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as output:
            json.dump(self.state, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write('\n'); output.flush(); os.fsync(output.fileno())
        path.replace(self.root / 'state.json')
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _event(self, kind, node=None, **details):
        self.state['events'].append({'sequence': len(self.state['events']) + 1,
                                     'at': self._now(), 'kind': kind, 'node': node, **details})

    def _workspace(self, record):
        path = self.root / record['workspace']
        demand(path.resolve().is_relative_to(self.root / 'products') and not (self.root / 'products').is_symlink(),
               'escaped product workspace')
        return path

    def _verify_accepted(self):
        for ident, record in self.state['nodes'].items():
            if record['status'] == 'SUCCEEDED':
                actual = products(self._workspace(record), self.nodes[ident]['writes'])
                demand(actual == record['products'], 'accepted product drift')

    def _initialize(self):
        if self.resume:
            saved = self._read()
            demand(saved.get('definition_id') == digest(self.definition) and saved.get('context') == self.context
                   and saved.get('controller_id') == self.controller_id and saved.get('policy') == self.policy,
                   'checkpoint definition, context, code or policy drift')
            demand(saved['status'] in {'READY', 'PAUSED', 'SUCCEEDED'}, 'in-flight, unknown or terminal failure cannot replay')
            self.state = saved
            self._now()
            self._verify_accepted()
            return
        now = self.clock()
        demand(type(now) in (int, float) and math.isfinite(now) and now >= 0, 'finite clock required')
        (self.root / 'products').mkdir()
        self.state = {'kind': 'goal_graph_run', 'version': 1, 'graph_id': self.definition['graph_id'],
            'definition_id': digest(self.definition), 'controller_id': self.controller_id,
            'policy': self.policy, 'context': self.context, 'status': 'READY', 'started_at': now,
            'last_at': now, 'deadline': min(now + self.policy['budget_seconds'], self.policy['deadline'] or float('inf')),
            'attempts': 0, 'events': [], 'nodes': {key: {'status': 'PENDING'} for key in self.nodes}}
        self._event('INITIALIZED')
        self._save()

    def _request(self, node, record):
        return {'node': deepcopy(node), 'context': deepcopy(self.context),
                'execution_id': record['execution_id'], 'workspace': str(self._workspace(record)),
                'deadline': self.state['deadline'], 'remaining_seconds': max(0, self.state['deadline'] - self.clock()),
                'inputs': {dep: {'record': deepcopy(self.state['nodes'][dep]),
                                 'workspace': str(self._workspace(self.state['nodes'][dep]))}
                           for dep in node['depends_on']}}

    def _invoke(self, node, record):
        started = self.clock()
        workspace = self._workspace(record)
        workspace.mkdir()
        request = self._request(node, record)
        demand(request['remaining_seconds'] > 0, 'budget expired before callback')
        if node['kind'] == 'closure':
            self._verify_accepted()
            demand(all(self.state['nodes'][ident]['status'] == 'SUCCEEDED'
                       for ident, spec in self.nodes.items() if spec['required'] and ident != node['id']), 'required branch incomplete')
            result = {'status': 'SUCCEEDED', 'context': self.context, 'payload_path': None,
                      'result': {'closed_goals': [g['id'] for g in self.definition['goals']]}}
        else:
            result = self.handlers[node['handler']].run(request)
        demand(isinstance(result, dict) and set(result) == {'status', 'context', 'result', 'payload_path'}, 'exact callback envelope required')
        demand(isinstance(result['status'], str) and result['status'] in {'SUCCEEDED', 'FAILED', 'PARTIAL', 'UNKNOWN', 'SKIPPED'}
               and result['context'] == self.context and isinstance(result['result'], dict), 'callback status/context mismatch')
        demand(result['status'] != 'SKIPPED' or not node['required'], 'required node cannot be skipped')
        try:
            demand(len(json.dumps(result, allow_nan=False).encode()) <= 128 * 1024, 'oversized callback envelope')
        except (TypeError, ValueError) as exc:
            raise GoalGraphRejected('non-JSON callback envelope') from exc
        actual = products(workspace, node['writes'])
        if result['status'] == 'SUCCEEDED':
            demand(set(actual) == set(node['writes']), 'missing required product')
        if node['kind'] == 'loop' and result['status'] in {'SUCCEEDED', 'PARTIAL', 'FAILED'}:
            demand(isinstance(result['payload_path'], str) and result['payload_path'] in actual, 'physical Loop result required')
            payload = json.loads((workspace / result['payload_path']).read_text())
            demand(payload == result['result'], 'Loop payload/envelope mismatch')
        else:
            demand(result['payload_path'] is None, 'unexpected payload for read-only/unknown result')
        return {**deepcopy(result), 'products': actual, 'started_at': started, 'ended_at': self.clock()}

    def _block_descendants(self):
        changed = True
        while changed:
            changed = False
            for ident, node in self.nodes.items():
                if self.state['nodes'][ident]['status'] != 'PENDING':
                    continue
                failed = [dep for dep in node['depends_on'] if self.state['nodes'][dep]['status'] not in {'PENDING', 'RUNNING', 'SUCCEEDED'}]
                if failed:
                    self.state['nodes'][ident] = {'status': 'BLOCKED', 'blocked_by': failed}
                    self._event('BLOCKED', ident, dependencies=failed)
                    changed = True

    def _finish(self):
        statuses = {r['status'] for r in self.state['nodes'].values()}
        closure = next(n['id'] for n in self.nodes.values() if n['kind'] == 'closure')
        if 'UNKNOWN' in statuses:
            status = 'UNKNOWN'
        elif self.state['nodes'][closure]['status'] == 'SUCCEEDED':
            status = 'SUCCEEDED'
        elif self._now() >= self.state['deadline']:
            status = 'BUDGET_EXHAUSTED'
        elif any(self.nodes[key]['required'] and row['status'] == 'FAILED' for key, row in self.state['nodes'].items()):
            status = 'FAILED'
        else:
            status = 'PARTIAL'
        self.state['status'] = status
        self.state['goals'] = {g['id']: {'required': list(g['required']), 'owner': next(
            n['id'] for n in self.nodes.values() if n['goal_id'] == g['id']), 'status': next(
            self.state['nodes'][n['id']]['status'] for n in self.nodes.values() if n['goal_id'] == g['id'])}
            for g in self.definition['goals']}
        self._event('FINISHED', status=status)
        self._save()

    def run(self):
        if not self.resume:
            self.root.mkdir(parents=True, mode=0o700)
        descriptor = os.open(self.root / 'controller.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise GoalGraphRejected('another controller owns this run') from exc
            self._initialize()
            if self.state['status'] == 'SUCCEEDED':
                return self.state
            pool = ThreadPoolExecutor(max_workers=self.definition['max_parallel'])
            futures = {}
            try:
                while True:
                    self._verify_accepted()
                    self._block_descendants()
                    if self._now() >= self.state['deadline'] or any(r['status'] == 'UNKNOWN' for r in self.state['nodes'].values()):
                        break
                    ready = [n for n in self.definition['nodes'] if self.state['nodes'][n['id']]['status'] == 'PENDING'
                             and all(self.state['nodes'][d]['status'] == 'SUCCEEDED' for d in n['depends_on'])]
                    if not ready:
                        break
                    ready = ready[:self.definition['max_parallel']]
                    self.state['status'] = 'RUNNING'
                    for node in ready:
                        self.state['attempts'] += 1
                        execution = 'attempt-' + str(self.state['attempts']) + '-' + node['id']
                        self.state['nodes'][node['id']] = {'status': 'RUNNING', 'execution_id': execution,
                            'workspace': 'products/' + execution}
                        self._event('RESERVED', node['id'], execution_id=execution)
                    self._save()  # Must be durable before any callback or product creation.
                    futures = {n['id']: pool.submit(self._invoke, n, deepcopy(self.state['nodes'][n['id']])) for n in ready}
                    for node in ready:
                        ident = node['id']
                        try:
                            result = futures[ident].result(timeout=max(0, self.state['deadline'] - self._now()))
                            if result['status'] == 'SUCCEEDED' and result['ended_at'] > self.state['deadline']:
                                result.update(status='PARTIAL', late_result=True)
                        except GoalGraphRejected as exc:
                            result = {'status': 'FAILED', 'failure_type': type(exc).__name__}
                        except Exception as exc:
                            result = {'status': 'UNKNOWN', 'failure_type': type(exc).__name__}
                        self.state['nodes'][ident].update(result)
                        self._event('RETURNED', ident, status=result['status'])
                        self._save()
                    self._verify_accepted()
                    self.state['status'] = 'READY'
                    self._save()
                    if self.pause_after in {n['id'] for n in ready} and not any(r['status'] == 'UNKNOWN' for r in self.state['nodes'].values()):
                        self.state['status'] = 'PAUSED'
                        self._event('PAUSED')
                        self._save()
                        return self.state
                self._finish()
            except (Exception, KeyboardInterrupt) as exc:
                self.state['status'] = 'UNKNOWN' if any(not f.done() for f in futures.values()) else 'FAILED'
                self.state['failure_type'] = type(exc).__name__
                self._save()
            finally:
                # Unknown callbacks may still be running. Never claim termination or
                # recycle this run; adapters must enforce their own inner timeouts.
                pool.shutdown(wait=False, cancel_futures=True)
            return self.state
