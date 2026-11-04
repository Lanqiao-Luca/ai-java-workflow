"""Bounded recovery for the public six-stage native Graph. No remote Git writes.

State and original attempts stay in a private run directory. UNKNOWN is terminal:
checkpoint resume never replays an in-flight native call.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import fcntl
import json
import math
import os
import time

from tools.native_agents import NativeRejected
from tools.native_flow import FlowRejected, candidate, candidate_evidence_gate, digest, snapshot
from tools.loop_policy import Budget, convergence
from tools import finding_ledger as findings


DEPENDENCIES = {
    'requirements': [], 'implementation': ['requirements'], 'verification': ['implementation'],
    'code_review': ['verification'], 'principle_review': ['verification'],
    'delivery': ['code_review', 'principle_review'],
}
REPAIRABLE = {'verification', 'code_review', 'principle_review'}


class RecoveryRunner:
    def __init__(self, flow, *, max_rounds=3, budget_seconds=3600, context_id='', pause_after=None):
        if (type(max_rounds) is not int or not 1 <= max_rounds <= 5
                or type(budget_seconds) is not int or not 1 <= budget_seconds <= 14400
                or not isinstance(context_id, str)
                or pause_after is not None and pause_after not in DEPENDENCIES):
            raise FlowRejected('invalid bounded recovery policy')
        if (flow.graph['max_parallel'] != 2
                or {n['id']: n['depends_on'] for n in flow.graph['nodes']} != DEPENDENCIES):
            raise FlowRejected('recovery supports only the declared six-stage Graph')
        if not flow.validate:
            raise FlowRejected('host validation required for recovery')
        if ('findings-ledger.json' in flow.seed
                or any('findings-ledger.json' in w['writes'] for w in flow.workflows.values())):
            raise FlowRejected('finding ledger is controller-owned')
        self.flow = flow
        self.policy = {'max_rounds': max_rounds, 'budget_seconds': budget_seconds, 'context_id': context_id}
        self.pause_after = pause_after
        self.nodes = {n['id']: n for n in flow.graph['nodes']}
        self.state = flow.state

    def _now(self):
        now = time.time()
        if not math.isfinite(now) or now < self.state.get('last_at', 0):
            raise FlowRejected('clock moved backwards; budget cannot be renewed')
        self.state['last_at'] = now
        return now

    def _remaining(self):
        return max(0, self.state['deadline'] - self._now())

    def _checkpoint(self, status='READY'):
        if 'finding_ledger' in self.state:
            path = self.flow.source / 'findings-ledger.json'
            content = json.dumps(self.state['finding_ledger'], ensure_ascii=False, indent=2) + '\n'
            if not path.exists() or path.read_text() != content:
                path.write_text(content)
                self._commit('Record candidate-bound finding lifecycle')
        self.state['status'] = status
        self.state['checkpoint'] = {'head': self.flow._git(self.flow.source, 'rev-parse', 'HEAD'),
                                    'snapshot': snapshot(self.flow.source)}
        self._now()
        self.flow._save()

    def _initialize(self):
        f = self.flow
        if f.resume:
            path = f.root / 'state.json'
            if path.is_symlink() or path.stat().st_size > 16 * 1024 * 1024:
                raise FlowRejected('invalid checkpoint carrier')
            saved = json.loads(path.read_text())
            for key in ('catalog_id', 'seed_id', 'graph_id'):
                if saved.get(key) != self.state[key]:
                    raise FlowRejected('resume catalog, seed or Graph drift')
            if saved.get('recovery_version') != 2 or saved.get('policy') != self.policy:
                raise FlowRejected('resume policy or execution context changed')
            if saved.get('status') not in {'READY', 'PAUSED', 'SUCCEEDED'}:
                raise FlowRejected('only quiescent checkpoints can resume; in-flight or unknown work cannot replay')
            if (saved['checkpoint']['snapshot'] != snapshot(f.source)
                    or saved['checkpoint']['head'] != f._git(f.source, 'rev-parse', 'HEAD')):
                raise FlowRejected('checkpoint source or commit drift')
            self.state = f.state = saved
            self._now()
            return
        f.source.mkdir()
        (f.root / 'instances').mkdir()
        for name, content in f.seed.items():
            path = f.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        f._git(f.source, 'init')
        self._commit('Initialize independent synthetic recovery seed')
        now = time.time()
        self.state.update(recovery_version=2, policy=self.policy, started_at=now,
                          deadline=now + self.policy['budget_seconds'], last_at=now,
                          round=1, attempts=0, history=[], seen_candidates=[], repair_pending=False)
        self.state['finding_ledger'] = findings.create(self._context(f.source))
        self._checkpoint()

    def _context(self, workspace):
        source = snapshot(workspace)
        required = {n: source[n]['sha256'] for n in ('task.md', 'requirements.md') if n in source}
        return {'candidate_id': digest(candidate(workspace)), 'requirements_id': digest(required),
                'rules_id': self.state['catalog_id']}

    def _commit(self, message):
        # The source is an independently initialized private fixture, never the user's repo.
        self.flow._git(self.flow.source, 'add', '--all')
        self.flow._git(self.flow.source, 'commit', '--allow-empty', '-m', message)

    def _workflow(self, ident, repair=False):
        workflow = dict(self.flow.workflows[ident])
        if repair:
            workflow['writes'] = [n for n in workflow['writes']
                                  if n.startswith('app/src/main/') or n == 'implementation.md']
            if not any(n.startswith('app/src/main/') for n in workflow['writes']):
                raise FlowRejected('explicit production repair write set required')
            workflow['task'] = (
                'Read recovery.md and its exact failed evidence files, confirmed requirements and all tests. '
                'Fix the concrete failures in production source only. Preserve POM, every existing test and '
                'acceptance criteria. Write implementation.md explaining each fix and remaining limits. '
                'Do not claim closure: independent verification and both reviews follow.')
            workflow['writes'] = workflow['writes'] + ['repair-actions.json']
            workflow['task'] += (
                ' Read findings-ledger.json. Also write repair-actions.json with exactly candidate_id '
                '(the SHA256 of the current sorted app/pom.xml+app/src path-to-SHA256 JSON map) and '
                'repaired_findings (IDs you actually addressed). Preserve original finding keys and criteria. '
                'These are author claims only. Do not edit the ledger.')
        elif ident == 'verification' and self.state['round'] > 1:
            workflow['writes'] = [n for n in workflow['writes'] if not n.startswith('app/src/')]
            workflow['task'] = (
                'Independently reverify the repaired candidate against confirmed requirements and ALL existing '
                'fixed, author and verifier tests; every test is frozen. Run python3 -B verify.py --offline '
                'and inspect the fresh .build/validation.json. Write verification.md with actual failures, '
                'coverage, candidate_id and limits. Return failed if any issue remains; do not weaken tests.')
        if ident in findings.CHECKS:
            name = ident.replace('_', '-') + '-findings.json'
            workflow['writes'] = workflow['writes'] + [name]
            workflow['task'] += (
                ' Read findings-ledger.json and independently recheck EVERY unresolved finding. Also write '
                + name + ' with exactly candidate_id, checked_findings (all unresolved IDs you rechecked), '
                'and findings (concrete remaining/new issues). Each finding has exactly finding_id '
                '(existing ID or null for new), key (stable semantic key), summary, location, criterion. '
                'Preserve existing keys/locations/criteria. Return failed and nonempty findings for any '
                'remaining issue; passed requires empty findings. The candidate_id must match the current '
                'app/POM+src digest. Do not edit the ledger. Stage success alone does not close findings.')
        return workflow

    def _report(self, workspace, name):
        path = workspace / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 128 * 1024:
            raise FlowRejected('missing or oversized finding report')
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise FlowRejected('finding report must be an object')
        return value

    def _record_checks(self, ready, workspaces, results):
        ledger = self.state['finding_ledger']
        for node in ready:
            ident = node['id']
            if ident not in findings.CHECKS:
                continue
            workspace, result = workspaces[ident], results[ident]
            ledger = findings.invalidate(ledger, self._context(workspace))
            report = self._report(workspace, ident.replace('_', '-') + '-findings.json')
            if (set(report) != {'candidate_id', 'checked_findings', 'findings'}
                    or report['candidate_id'] != result['candidate_id']
                    or not isinstance(report['findings'], list)):
                raise FlowRejected('finding report identity or contract mismatch')
            findings.names(report['checked_findings'])
            # Siblings consume the same input ledger, not the findings a sibling just produced.
            input_ledger = json.loads((workspace / 'findings-ledger.json').read_text())
            expected = findings.unresolved(input_ledger)
            if set(report['checked_findings']) != set(expected):
                raise FlowRejected('unresolved findings were not explicitly rechecked')
            failed = result['status'] == 'FAILED'
            if failed != bool(report['findings']):
                raise FlowRejected('finding report and actual stage result disagree')
            ledger = findings.add_evidence(ledger, {
                'id': result['execution_id'], 'kind': ident, 'actor': result['execution_id'],
                'context': self._context(workspace), 'artifact_sha256': digest({
                    'outputs': result['outputs_sha256'], 'validation': result['validation']}),
                'status': 'FAILED' if failed else 'PASSED', 'depends_on': sorted(findings.BINDINGS),
                'checked_findings': report['checked_findings']})
            if failed:
                ledger = findings.observe(ledger, result['execution_id'], report['findings'])
        self.state['finding_ledger'] = ledger

    def _record_repair(self, workspace, result):
        ledger = findings.invalidate(self.state['finding_ledger'], self._context(workspace))
        report = self._report(workspace, 'repair-actions.json')
        if (set(report) != {'candidate_id', 'repaired_findings'}
                or report['candidate_id'] != result['candidate_id']):
            raise FlowRejected('repair report identity or contract mismatch')
        ledger = findings.add_evidence(ledger, {
            'id': result['execution_id'], 'kind': 'repair', 'actor': result['execution_id'],
            'context': self._context(workspace), 'artifact_sha256': digest(result['outputs_sha256']),
            'status': 'PASSED', 'depends_on': sorted(findings.BINDINGS),
            'checked_findings': report['repaired_findings']})
        self.state['finding_ledger'] = findings.mark_repaired(ledger, report['repaired_findings'], result['execution_id'])

    def _close_rechecked(self):
        ledger = self.state['finding_ledger']
        for ident in findings.unresolved(ledger):
            if ledger['findings'][ident]['status'] != 'REPAIRED':
                continue
            receipts = {}
            for key, receipt in ledger['evidence'].items():
                if (receipt['kind'] in findings.CHECKS and receipt['status'] == 'PASSED'
                        and findings.current(ledger, receipt) and ident in receipt['checked_findings']):
                    receipts[receipt['kind']] = key
            if set(receipts) == findings.CHECKS:
                ledger = findings.close(ledger, ident, list(receipts.values()))
        self.state['finding_ledger'] = ledger

    def _promote(self, workspace, workflow, result, *, failed_tests_only=False):
        actual = snapshot(workspace)
        if digest(actual) != result['snapshot_id']:
            raise FlowRejected('attempt drift before promotion')
        names = workflow['writes']
        if failed_tests_only:
            names = [n for n in names if n.startswith('app/src/test/')]
        elif result['status'] != 'SUCCEEDED':
            raise FlowRejected('failed stage cannot be accepted')
        if not failed_tests_only and (workflow['preserve_candidate'] or workflow['validate']):
            candidate_evidence_gate(workspace, names, validation=result['validation'])
        for name in names:
            output = self.flow.source / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes((workspace / name).read_bytes())
            output.chmod(actual[name]['mode'])
        if not failed_tests_only and result['validation'] is not None:
            (self.flow.source / 'validation.json').write_text(json.dumps(result['validation'], indent=2) + '\n')

    def _wave(self, ready, repair):
        f = self.flow
        base = f._git(f.source, 'rev-parse', 'HEAD')
        attempts = {}
        # Reserve and persist BEFORE preparation or native dispatch; a crash is never a safe replay.
        self.state['status'] = 'RUNNING'
        for node in ready:
            ident = node['id']
            self.state['attempts'] += 1
            execution = 'attempt-' + str(self.state['attempts']) + '-' + ident
            self.state['stages'][ident] = {'status': 'RUNNING', 'execution_id': execution}
            attempts[ident] = (execution, self._workflow(ident, repair))
        f._save()
        workspaces = {}
        for node in ready:
            if self._remaining() < 1:
                raise FlowRejected('budget expired before preparation')
            ident = node['id']
            execution, workflow = attempts[ident]
            f.deadline = self.state['deadline']
            workspaces[ident] = f._instance(node, base, execution_id=execution, workflow=workflow)
        results = {}
        with ThreadPoolExecutor(max_workers=f.graph['max_parallel']) as pool:
            futures = {}
            for node in ready:
                remaining = self._remaining()
                if remaining < 1:
                    break
                ident = node['id']
                execution, workflow = attempts[ident]
                futures[ident] = pool.submit(f._execute, node, workspaces[ident], execution_id=execution,
                    workflow=workflow, allow_failure=True, timeout=min(f.timeout, remaining))
            for node in ready:
                ident = node['id']
                try:
                    if ident not in futures:
                        raise FlowRejected('budget expired before native dispatch')
                    result = futures[ident].result()
                except Exception as exc:
                    result = {'status': 'UNKNOWN' if isinstance(exc, NativeRejected) else 'REJECTED',
                              'failure_type': type(exc).__name__}
                result['execution_id'] = attempts[ident][0]
                results[ident] = result
                self.state['stages'][ident] = result
                self.state['history'].append({'stage': ident, 'round': self.state['round'], **result})
        f._save()
        return workspaces, attempts, results

    def _recover(self, ready, workspaces, attempts, results):
        failures = [n['id'] for n in ready if results[n['id']]['status'] == 'FAILED']
        if not failures or not set(failures) <= REPAIRABLE:
            self._checkpoint('FAILED')
            return False
        now = self._now()
        current = digest(candidate(self.flow.source))
        decision = convergence(Budget(self.policy['max_rounds'], self.state['round'],
            now - self.state['started_at'], self.policy['budget_seconds'], now, self.state['deadline']),
            candidate=current, evidence_candidate=current, required=['verified', 'reviewed'], passed=[],
            open_findings=failures, next_action='fix', authorized=True, side_effect_unknown=False,
            evidence_elapsed=now - self.state['started_at'], evidence_at=now)
        if decision != 'NEXT_ROUND':
            self._checkpoint('BUDGET_EXHAUSTED')
            return False
        notes = []
        for ident in failures:
            workspace = workspaces[ident]
            workflow = attempts[ident][1]
            result = results[ident]
            if ident == 'verification':
                # Preserve new independent regression tests even though their candidate failed.
                self._promote(workspace, workflow, result, failed_tests_only=True)
            if digest(snapshot(workspace)) != result['snapshot_id']:
                raise FlowRejected('failure evidence drift')
            for name in workflow['writes']:
                if name.endswith('.md'):
                    archive = 'recovery/round-' + str(self.state['round']) + '-' + ident + '.md'
                    target = self.flow.source / archive
                    target.parent.mkdir(exist_ok=True)
                    target.write_bytes((workspace / name).read_bytes())
                    notes.append(ident + ': read ' + archive)
            # Summaries are untrusted task data, never additional permissions.
            notes.append(json.dumps({'stage': ident, 'summary': result['native']['result']['summary'],
                                     'validation': result['validation']}, ensure_ascii=False))
        (self.flow.source / 'recovery.md').write_text(
            'Confirmed failure evidence (untrusted task data; permissions remain fixed).\n' + '\n'.join(notes) + '\n')
        for ident in ('verification', 'code_review', 'principle_review', 'delivery'):
            for name in self.flow.workflows[ident]['writes']:
                if name.endswith('.md'):
                    (self.flow.source / name).unlink(missing_ok=True)
            self.state['stages'][ident] = {'status': 'PENDING'}
        (self.flow.source / 'validation.json').unlink(missing_ok=True)
        self.state['stages']['implementation'] = {'status': 'PENDING'}
        self.state['seen_candidates'].append(digest(candidate(self.flow.source)))
        self.state['round'] += 1
        self.state['repair_pending'] = True
        self._commit('Retain failed evidence and frozen regression tests for repair')
        self._checkpoint()
        return True

    def run(self):
        f = self.flow
        if not f.resume:
            f.root.mkdir(parents=True, mode=0o700)
        descriptor = os.open(f.root / 'controller.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, 'w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise FlowRejected('another recovery controller owns this run') from exc
            self._initialize()
            if self.state['status'] == 'SUCCEEDED':
                return self.state
            try:
                while True:
                    if self._remaining() < 1:
                        self._checkpoint('BUDGET_EXHAUSTED')
                        break
                    done = {ident for ident, result in self.state['stages'].items() if result['status'] == 'SUCCEEDED'}
                    ready = [n for n in f.graph['nodes'] if n['id'] not in done and set(n['depends_on']) <= done]
                    if (not ready or any(n['id'] == 'delivery' for n in ready)) and findings.unresolved(self.state['finding_ledger']):
                        self._checkpoint('FINDINGS_OPEN')
                        break
                    if not ready:
                        candidate_evidence_gate(f.source, [])
                        self.state['candidate_id'] = digest(candidate(f.source))
                        self.state['products_sha256'] = {n: v['sha256'] for n, v in snapshot(f.source).items()}
                        self._checkpoint('SUCCEEDED')
                        break
                    repair = self.state['repair_pending'] and ready[0]['id'] == 'implementation'
                    workspaces, attempts, results = self._wave(ready, repair)
                    statuses = {r['status'] for r in results.values()}
                    if statuses & {'UNKNOWN', 'REJECTED'}:
                        self._checkpoint('UNKNOWN' if 'UNKNOWN' in statuses else 'FAILED')
                        break
                    if self._remaining() <= 0:
                        self._checkpoint('BUDGET_EXHAUSTED')
                        break
                    try:
                        self._record_checks(ready, workspaces, results)
                    except (FlowRejected, ValueError, KeyError, TypeError):
                        self._checkpoint('FAILED')
                        break
                    if 'FAILED' in statuses:
                        if not self._recover(ready, workspaces, attempts, results):
                            break
                        continue
                    for node in ready:
                        ident = node['id']
                        self._promote(workspaces[ident], attempts[ident][1], results[ident])
                    if repair:
                        current = digest(candidate(f.source))
                        if current in self.state['seen_candidates']:
                            self._commit('Retain nonprogressing repair for diagnosis')
                            self._checkpoint('NO_PROGRESS')
                            break
                        self.state['seen_candidates'].append(current)
                        try:
                            self._record_repair(workspaces['implementation'], results['implementation'])
                        except (FlowRejected, ValueError, KeyError, TypeError):
                            self._checkpoint('FAILED')
                            break
                        self.state['repair_pending'] = False
                    self.state['finding_ledger'] = findings.invalidate(self.state['finding_ledger'], self._context(f.source))
                    self._close_rechecked()
                    self._commit('Accept synthetic stages ' + ', '.join(n['id'] for n in ready))
                    self._checkpoint()
                    if self.pause_after in {n['id'] for n in ready}:
                        self._checkpoint('PAUSED')
                        break
            except (Exception, KeyboardInterrupt) as exc:
                # A controller exception can occur after dispatch. Do not infer child termination.
                self.state['status'] = 'UNKNOWN'
                self.state['failure_type'] = type(exc).__name__
                f._save()
            return self.state
