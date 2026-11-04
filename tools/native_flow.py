"""Native Graph orchestration for explicit public/synthetic inputs; no remote publication."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

from tools.native_agents import NativeRejected, dispatch


class FlowRejected(RuntimeError):
    pass


def digest(mapping):
    return hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()


def relative(name):
    if (not isinstance(name, str) or not name or not name.isascii() or '\\' in name
            or PurePosixPath(name).is_absolute() or name != PurePosixPath(name).as_posix()
            or any(part in {'', '.', '..'} or part.startswith('.') for part in name.split('/'))):
        raise FlowRejected('unsupported relative product path')
    return name


def snapshot(root):
    """Track infrastructure too; only explicit runtime products are excluded."""
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        if parent == root:
            dirs[:] = [n for n in dirs if n not in {'.git', '.build'}]
            files = [n for n in files if n != '.git']
        if any((parent / n).is_symlink() for n in dirs + files):
            raise FlowRejected('linked instance content')
        for name in files:
            path = parent / name
            if path.stat().st_size > 8 * 1024 * 1024:
                raise FlowRejected('oversized instance file')
            result[path.relative_to(root).as_posix()] = {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'mode': path.stat().st_mode & 0o777}
    return result


def candidate(root):
    mapping = {}
    for name, value in snapshot(root).items():
        if name == 'app/pom.xml' or name.startswith('app/src/'):
            mapping[name] = value['sha256']
    return mapping


def stage_gate(before, after, writes, result, preserve_candidate=False):
    declared = set(writes)
    if len(declared) != len(writes) or not declared:
        raise FlowRejected('unique nonempty output set required')
    for name in writes:
        relative(name)
        if name.startswith(('catalog/', 'validation.json', 'verify.py')):
            raise FlowRejected('reserved output')
    changed = {n for n in set(before) | set(after) if before.get(n) != after.get(n)}
    if changed - declared or declared - set(after):
        raise FlowRejected('undeclared mutation or missing output')
    if (not isinstance(result, dict) or result.get('status') != 'passed'
            or not isinstance(result.get('outputs'), list)
            or len(result['outputs']) != len(writes) or set(result['outputs']) != declared):
        raise FlowRejected('child outputs do not match declared products')
    if preserve_candidate and any(n == 'app/pom.xml' or n.startswith('app/src/') for n in changed):
        raise FlowRejected('frozen candidate changed')


def candidate_evidence_gate(workspace, writes, validation=None, require_documents=True, expected_status='PASSED'):
    """Bind the declared document conclusion and its evidence to exact current source bytes."""
    current = candidate(workspace)
    ident = digest(current)
    if validation is None:
        path = workspace / 'validation.json'
        if path.is_symlink() or not path.is_file():
            raise FlowRejected('current host validation evidence required')
        try:
            validation = json.loads(path.read_text())
        except (ValueError, UnicodeError) as exc:
            raise FlowRejected('unreadable host validation evidence') from exc
    if (not isinstance(validation, dict) or validation.get('status') != expected_status
            or validation.get('source_sha256') != current or validation.get('candidate_id') != ident):
        raise FlowRejected('host validation does not describe current candidate')
    if require_documents:
        for name in writes:
            if name.endswith('.md'):
                lines = (workspace / name).read_text().splitlines()
                if not lines or lines[0] != 'candidate_id: ' + ident:
                    raise FlowRejected('document conclusion uses missing or stale candidate identity')
    return ident


def _catalog(root):
    manifest = root / 'public-manifest.json'
    data = json.loads(manifest.read_text())
    files = {}
    for row in data['files']:
        name = row['path'] if row['path'] == '.github/workflows/ci.yml' else relative(row['path'])
        path = root / name
        if (row.get('status') != 'reviewed_candidate' or name in files or path.is_symlink()
                or not path.resolve(strict=True).is_relative_to(root) or not path.is_file()):
            raise FlowRejected('unreviewed, duplicate, or escaped catalog source')
        # Parent directory links are rejected even when their targets remain in root.
        if any(p.is_symlink() for p in path.parents if p != root and p.is_relative_to(root)):
            raise FlowRejected('linked catalog directory')
        content = path.read_bytes()
        if len(content) > 8 * 1024 * 1024:
            raise FlowRejected('oversized catalog source')
        files[name] = content
    return files


def load_definition(path, root):
    root = Path(root).resolve(strict=True)
    files = _catalog(root)
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(root):
        raise FlowRejected('graph outside public catalog')
    graph_name = path.relative_to(root).as_posix()
    if graph_name not in files:
        raise FlowRejected('graph not in public manifest')
    graph = json.loads(files[graph_name])
    if (set(graph) != {'kind', 'graph_id', 'max_parallel', 'nodes'} or graph['kind'] != 'native_graph'
            or not re.fullmatch('[a-z][a-z0-9_-]{0,63}', graph['graph_id'])
            or type(graph['max_parallel']) is not int or not 1 <= graph['max_parallel'] <= 4
            or not isinstance(graph['nodes'], list) or not 1 <= len(graph['nodes']) <= 32):
        raise FlowRejected('unsupported native Graph')
    workflows, ids = {}, set()
    for node in graph['nodes']:
        if (set(node) != {'id', 'depends_on', 'workflow'}
                or not re.fullmatch('[a-z][a-z0-9_]{0,63}', node['id']) or node['id'] in ids
                or not isinstance(node['depends_on'], list)
                or any(not isinstance(x, str) for x in node['depends_on'])
                or len(set(node['depends_on'])) != len(node['depends_on'])):
            raise FlowRejected('unsupported native node')
        ids.add(node['id'])
        name = relative(node['workflow'])
        if not name.startswith('workflows/') or name not in files:
            raise FlowRejected('missing public native Workflow')
        workflow = json.loads(files[name])
        if (set(workflow) != {'kind', 'role', 'agents', 'writes', 'task', 'preserve_candidate', 'validate'}
                or workflow['kind'] != 'native_workflow'
                or not re.fullmatch('[a-z][a-z0-9_]{0,63}', workflow['role'])
                or not isinstance(workflow['agents'], list) or not workflow['agents']
                or not isinstance(workflow['writes'], list) or not workflow['writes']
                or type(workflow['preserve_candidate']) is not bool or type(workflow['validate']) is not bool
                or not isinstance(workflow['task'], str) or not workflow['task'].strip()):
            raise FlowRejected('unsupported native Workflow contract')
        for contract in workflow['agents']:
            relative(contract)
            if not contract.startswith('agents/') or not contract.endswith('.md') or contract not in files:
                raise FlowRejected('missing Agent responsibility contract')
        for output in workflow['writes']:
            relative(output)
            if output.startswith(('catalog/', 'verify.py', 'validation.json')):
                raise FlowRejected('reserved output')
        if len(set(workflow['writes'])) != len(workflow['writes']):
            raise FlowRejected('duplicate output')
        workflows[node['id']] = workflow
    done = set()
    while len(done) < len(ids):
        ready = [n for n in graph['nodes'] if n['id'] not in done and set(n['depends_on']) <= done]
        if not ready:
            raise FlowRejected('cycle or unknown native dependency')
        occupied = set()
        for n in ready:
            outputs = set(workflows[n['id']]['writes'])
            if occupied & outputs:
                raise FlowRejected('concurrent native output conflict')
            occupied |= outputs
        done.update(n['id'] for n in ready)
    return graph, workflows, files


class NativeFlow:
    def __init__(self, seed_files, catalog_root, definition_path, run_root, codex='codex',
                 timeout=600, prepare=None, validate=None, *, resume=False):
        self.catalog_root = Path(catalog_root).resolve(strict=True)
        self.graph, self.workflows, self.catalog = load_definition(definition_path, self.catalog_root)
        self.root = Path(run_root).resolve()
        self.resume = resume
        if ((self.root.exists() and not resume) or (resume and not self.root.is_dir())
                or self.root.is_relative_to(self.catalog_root)):
            raise FlowRejected('new private run root outside catalog required')
        if not isinstance(seed_files, dict) or not seed_files or len(seed_files) > 512:
            raise FlowRejected('explicit bounded synthetic seed required')
        for name, value in seed_files.items():
            relative(name)
            if not isinstance(value, bytes) or len(value) > 1024 * 1024:
                raise FlowRejected('bounded seed bytes required')
            if name.split('/')[0] in {'catalog', 'verify.py', 'validation.json'}:
                raise FlowRejected('reserved seed name')
        self.seed = dict(seed_files)
        self.codex, self.timeout, self.prepare, self.validate = codex, timeout, prepare, validate
        self.source = self.root / 'source'
        self.state = {'status': 'PENDING', 'graph_id': self.graph['graph_id'],
                      'catalog_id': digest({n: hashlib.sha256(v).hexdigest() for n, v in self.catalog.items()}),
                      'seed_id': digest({n: hashlib.sha256(v).hexdigest() for n, v in self.seed.items()}),
                      'stages': {n['id']: {'status': 'PENDING'} for n in self.graph['nodes']}}

    def _save(self):
        path = self.root / 'state.json'
        temporary = self.root / 'state.json.tmp'
        temporary.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)

    def _git(self, cwd, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                    'GIT_TERMINAL_PROMPT': '0'})
        command = ['git', '-c', 'core.hooksPath=' + os.devnull, '-c', 'commit.gpgsign=false',
                   '-c', 'user.name=Synthetic Workflow', '-c', 'user.email=workflow@example.invalid',
                   '-c', 'init.defaultBranch=main', *args]
        p = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
        if p.returncode:
            raise FlowRejected('private fixture Git operation failed')
        return p.stdout.strip()

    def _instance(self, node, base, *, execution_id=None, workflow=None):
        ident = node['id']
        workspace = self.root / 'instances' / (execution_id or ident)
        self._git(self.source, 'worktree', 'add', '--detach', str(workspace), base)
        for name, content in self.catalog.items():
            path = workspace / 'catalog' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        workflow = workflow or self.workflows[ident]
        agents = workspace / '.codex/agents'
        agents.mkdir(parents=True)
        instructions = ('You are the native stage role for this public synthetic task. Read these actual '
                        'responsibility contracts and consume their linked Skills and Standards: ' +
                        ', '.join('catalog/' + n for n in workflow['agents']) + '. '
                        'Only work in this new workspace and the exact task output set. Do not run Git, '
                        'access unrelated private data, call company services, publish or deploy. '
                        'Report actual commands, limits, and methods used. Final response must be only JSON '
                        'with status (passed or failed), summary (string), outputs (relative paths array).')
        role = workflow['role']
        (agents / (role + '.toml')).write_text('name = ' + json.dumps(role) + '\n'
            + 'description = "Native public synthetic Workflow stage."\ndeveloper_instructions = '
            + json.dumps(instructions) + '\n')
        if self.prepare:
            self.prepare(workspace, node, workflow)
        return workspace

    def _execute(self, node, workspace, *, execution_id=None, workflow=None, allow_failure=False, timeout=None):
        ident = node['id']
        workflow = workflow or self.workflows[ident]
        before, code_before = snapshot(workspace), candidate(workspace)
        started = time.time()
        if workflow['preserve_candidate'] and not workflow['validate']:
            candidate_evidence_gate(workspace, [], require_documents=False)
        task = (workflow['task'] + '\nRead task.md and relevant prior-stage products in this workspace. '
                'Use the registered responsibility contracts and their actual methods. '
                'Allowed and required outputs exactly: ' + json.dumps(workflow['writes']) + '. '
                'Do not edit other sources, fixed acceptance tests, catalog, verify.py, native configuration '
                'or runtime tool configuration. .build is private build output only. '
                'Do not use Git or contact real services. Describe actual method choices in your output documents. '
                'For every Markdown output in a preserve_candidate or validate stage, the FIRST line must be '
                '"candidate_id: <exact current candidate SHA256>". Verification obtains this identity from '
                'the actual .build/validation.json after its final build. Review and delivery obtain it '
                'from host validation.json and must verify it describes current app/POM+src bytes. '
                'Do not invent, reuse or merely label a candidate identity. '
                'Return only JSON status, summary, outputs; outputs must equal the declared list.')
        options = {'accept_failed': True} if allow_failure else {}
        native = dispatch(workspace, workflow['role'], task, self.root / 'private' / (execution_id or ident),
                          codex=self.codex, timeout=timeout or self.timeout, **options)
        after = snapshot(workspace)
        # Confirmed failed children still need the exact same write-set and output gates.
        result = native['result']
        if allow_failure and result.get('status') == 'failed':
            result = {**result, 'status': 'passed'}
        stage_gate(before, after, workflow['writes'], result, workflow['preserve_candidate'])
        validation = None
        failed = native['result']['status'] == 'failed'
        if workflow['validate']:
            if not self.validate:
                raise FlowRejected('real host validation callback required')
            validation = self.validate(workspace, node, workflow)
            current = candidate(workspace)
            if (snapshot(workspace) != after or validation.get('status') not in {'PASSED', 'FAILED'}
                    or validation.get('source_sha256') != current or validation.get('candidate_id') != digest(current)):
                raise FlowRejected('host validation failed or source drifted')
            if validation['status'] == 'FAILED':
                if (not allow_failure or type(validation.get('process_exit')) is not int
                        or validation['process_exit'] <= 0
                        or validation.get('category') != 'junit_or_source_mismatch'):
                    raise FlowRejected('validation failure is not a confirmed build/test result')
                failed = True
        if workflow['preserve_candidate'] or workflow['validate']:
            candidate_evidence_gate(workspace, workflow['writes'], validation=validation,
                                    expected_status=validation['status'] if validation else 'PASSED')
        return {'status': 'FAILED' if failed else 'SUCCEEDED', 'started': started, 'ended': time.time(),
                'input_candidate_id': digest(code_before), 'candidate_id': digest(candidate(workspace)),
                'native': native, 'snapshot_id': digest(after), 'outputs_sha256': {n: after[n]['sha256'] for n in workflow['writes']},
                'validation': validation}

    def run(self):
        if self.resume:
            raise FlowRejected('resume requires the checkpoint recovery controller')
        self.root.mkdir(parents=True, mode=0o700)
        self.source.mkdir()
        (self.root / 'instances').mkdir()
        for name, content in self.seed.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self._git(self.source, 'init')
        self._git(self.source, 'add', '--', *sorted(self.seed))
        self._git(self.source, 'commit', '-m', 'Initialize independent synthetic seed')
        self.state['status'] = 'RUNNING'
        self._save()
        done = set()
        try:
            while len(done) < len(self.graph['nodes']):
                ready = [n for n in self.graph['nodes'] if n['id'] not in done and set(n['depends_on']) <= done]
                base = self._git(self.source, 'rev-parse', 'HEAD')
                workspaces = {}
                for node in ready:
                    workspaces[node['id']] = self._instance(node, base)
                    self.state['stages'][node['id']] = {'status': 'RUNNING', 'base': base}
                self._save()
                results, failed = {}, False
                with ThreadPoolExecutor(max_workers=self.graph['max_parallel']) as pool:
                    futures = {n['id']: pool.submit(self._execute, n, workspaces[n['id']]) for n in ready}
                    for node in ready:
                        ident = node['id']
                        try:
                            results[ident] = futures[ident].result()
                            self.state['stages'][ident] = results[ident]
                        except Exception as exc:
                            failed = True
                            status = 'UNKNOWN' if isinstance(exc, NativeRejected) else 'FAILED'
                            self.state['stages'][ident] = {'status': status, 'failure_type': type(exc).__name__, 'failure': str(exc)[:500]}
                self._save()
                if failed:
                    self.state['status'] = ('UNKNOWN' if any(s['status'] == 'UNKNOWN' for s in self.state['stages'].values()) else 'FAILED')
                    break
                for node in ready:
                    ident, workspace = node['id'], workspaces[node['id']]
                    names = list(self.workflows[ident]['writes'])
                    # Recheck bytes and claimed evidence at promotion after all tasks have stopped.
                    workflow = self.workflows[ident]
                    if workflow['preserve_candidate'] or workflow['validate']:
                        candidate_evidence_gate(workspace, names, validation=results[ident]['validation'])
                    actual = snapshot(workspace)
                    if digest(actual) != results[ident]['snapshot_id'] or any(actual[n]['sha256'] != results[ident]['outputs_sha256'][n] for n in names):
                        raise FlowRejected('output drift before promotion')
                    for name in names:
                        output = self.source / name
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.write_bytes((workspace / name).read_bytes())
                    if results[ident]['validation'] is not None:
                        (self.source / 'validation.json').write_text(json.dumps(results[ident]['validation'], indent=2) + '\n')
                        names.append('validation.json')
                    self._git(self.source, 'add', '--', *names)
                    self._git(self.source, 'commit', '--allow-empty', '-m', 'Accept synthetic stage ' + ident)
                    done.add(ident)
                self._save()
            else:
                self.state['status'] = 'SUCCEEDED'
                self.state['candidate_id'] = digest(candidate(self.source))
                self.state['products_sha256'] = {n: v['sha256'] for n, v in snapshot(self.source).items()}
        except Exception as exc:
            self.state['status'] = 'FAILED'
            self.state['failure_type'] = type(exc).__name__
        self._save()
        return self.state
