"""Curated case entry with persistent safe checkpoints; not a general agent scheduler."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import sys
import uuid
from tools.module_plan import load_json

ROOT = Path(__file__).resolve().parents[1]
JOBS = {
    'local-evidence': ('workflows/examples/local-evidence', 'run_examples', 'agents/evidence-collector.md'),
    'conclusion-challenge': ('workflows/examples/conclusion-challenge', 'run_case', 'workflows/conclusion-challenge.md'),
    'module-plan': ('workflows/examples/design-to-modules', 'run_examples', 'workflows/design-to-modules.md'),
    'spring-archive': ('examples/design-to-spring', 'build', 'workflows/design-to-modules.md'),
    'capability-benchmark': ('workflows/examples/capability-benchmark', 'run_benchmark', 'agents/capability-evaluator.md'),
}
GOALS = {'collect': 'local-evidence', 'challenge': 'conclusion-challenge',
         'plan': 'module-plan', 'spring': 'spring-archive', 'benchmark': 'capability-benchmark'}
TOOLS = {
    'local-evidence': ['tools/local_evidence.py', 'tools/evidence_coverage.py'],
    'conclusion-challenge': ['tools/conclusion_challenge.py'],
    'module-plan': ['tools/module_plan.py'],
    'spring-archive': ['tools/module_plan.py'],
    'capability-benchmark': ['tools/capability_benchmark.py', 'tools/conclusion_challenge.py',
                             'workflows/examples/conclusion-challenge/run.py',
                             'workflows/examples/conclusion-challenge/requirements.md',
                             'workflows/examples/conclusion-challenge/cache_demo.py',
                             'workflows/examples/conclusion-challenge/review.json'],
}


class EntryError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise EntryError(message)


def choose(goal):
    require(goal in GOALS, 'unsupported goal')
    job = GOALS[goal]
    return {'job': job, 'entry': JOBS[job][2], 'kind': 'explicit_goal_mapping',
            'authorization': 'caller_must_supply', 'scope': 'curated_case_only'}


def request(path):
    value = load_json(path)
    require(isinstance(value, dict) and set(value) == {'job', 'options'}, 'request fields')
    require(isinstance(value['job'], str) and value['job'] in JOBS and isinstance(value['options'], dict), 'supported job')
    options = value['options']
    if value['job'] == 'spring-archive':
        require(set(options) == {'java_home', 'maven_home', 'repository', 'offline'}, 'spring options')
        require(type(options['offline']) is bool, 'explicit dependency download mode')
        require(all(isinstance(options[k], str) and Path(options[k]).is_absolute()
                    for k in ('java_home', 'maven_home', 'repository')), 'explicit absolute tool paths')
        require(not Path(options['repository']).resolve().is_relative_to(ROOT), 'external dependency cache')
    else:
        require(options == {}, 'this curated job takes no arbitrary options')
    return value


def doctor(value=None):
    checks = {'python_39_plus': sys.version_info >= (3, 9), 'posix': os.name == 'posix'}
    if value and value['job'] == 'spring-archive':
        options = value['options']
        checks['java_file'] = (Path(options['java_home']) / 'bin/java').is_file()
        checks['maven_file'] = (Path(options['maven_home']) / 'bin/mvn').is_file()
    return {'status': 'READY' if all(checks.values()) else 'NOT_READY', 'checks': checks,
            'scope': 'structural prerequisites; actual tool probes and acceptance occur during run',
            'jobs': sorted(JOBS)}


def fingerprint(path, value):
    folder = ROOT / JOBS[value['job']][0]
    paths = [ROOT / 'tools/workflow_entry.py', ROOT / 'scripts/workflow.py', ROOT / 'tools/module_plan.py']
    paths += [ROOT / p for p in TOOLS[value['job']]]
    # Only the reviewed public manifest grants candidate membership. Unexpected
    # local files are rejected before their contents or hashes are read.
    manifest = load_json(ROOT / 'public-manifest.json')['files']
    prefix = folder.relative_to(ROOT).as_posix() + '/'
    declared = {row['path'] for row in manifest if row['path'].startswith(prefix)}
    actual = {p.relative_to(ROOT).as_posix() for p in folder.rglob('*') if p.is_file()}
    require(actual == declared, 'case file set drift')
    paths += [ROOT / name for name in declared]
    require(not any(p.is_symlink() for p in folder.rglob('*')), 'case symlink')
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    data = {'request_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'sources': sources,
            'python': list(sys.version_info[:2])}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def run_root(path):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink(), 'absolute non-link run root')
    resolved = path.resolve()
    require(not resolved.is_relative_to(ROOT), 'runtime files must be outside public repository')
    return resolved


def save(root, state):
    temporary = root / ('state-' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x') as stream:
        json.dump(state, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, root / 'state.json')


def status(path):
    root = run_root(path)
    state = load_json(root / 'state.json')
    require(isinstance(state, dict) and state.get('version') == 1, 'state version')
    return state


def execute(value, root):
    folder, function, _ = JOBS[value['job']]
    handler = runpy.run_path(str(ROOT / folder / 'run.py'))[function]
    if value['job'] == 'spring-archive':
        options = value['options']
        return handler(options['java_home'], options['maven_home'], options['repository'],
                       offline=options['offline'], log_path=root / 'maven.log')
    return handler()


def _advance(root, state, value):
    require(state['status'] == 'READY' and state['steps'] == ['preflight'], 'no executable checkpoint')
    state['status'] = 'RUNNING'
    save(root, state)  # Persist before initiating even a local action.
    try:
        result = execute(value, root)
    except Exception as error:
        state['status'] = 'UNKNOWN'
        state['failure_category'] = type(error).__name__
        save(root, state)
        return state
    except BaseException:
        state['status'] = 'UNKNOWN'
        save(root, state)
        raise
    state['result'] = result
    state['steps'].append('execute')
    if isinstance(result, dict) and result.get('status') in {'FAILED', 'UNKNOWN'}:
        state['status'] = result['status']
    else:
        state['status'] = 'SUCCEEDED'
    save(root, state)
    return state


def run(path, root, pause=False):
    value = request(path)
    require(doctor(value)['status'] == 'READY', 'environment not ready')
    identity = fingerprint(path, value)
    root = run_root(root)
    root.mkdir(parents=True, exist_ok=False)
    lock = root / 'writer.lock'
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        state = {'version': 1, 'run_id': uuid.uuid4().hex, 'job': value['job'], 'fingerprint': identity,
                 'status': 'READY', 'steps': ['preflight'], 'result': None}
        save(root, state)
        return state if pause else _advance(root, state, value)
    finally:
        os.close(fd)
        lock.unlink()


def resume(path, root):
    value = request(path)
    root = run_root(root)
    lock = root / 'writer.lock'
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise EntryError('writer present; do not steal or replay')
    try:
        state = status(root)
        require(state['job'] == value['job'] and state['fingerprint'] == fingerprint(path, value), 'input or implementation drift')
        if state['status'] in {'RUNNING', 'UNKNOWN'}:
            return dict(state, status='UNKNOWN', recovery='check original action; automatic replay forbidden')
        if state['status'] in {'SUCCEEDED', 'FAILED'}:
            return state
        require(doctor(value)['status'] == 'READY', 'environment not ready')
        return _advance(root, state, value)
    finally:
        os.close(fd)
        lock.unlink()
