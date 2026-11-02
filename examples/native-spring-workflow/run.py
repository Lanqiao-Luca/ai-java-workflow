"""Run an opt-in synthetic Spring Graph with actual native Codex Agents."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.native_flow import NativeFlow


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--maven-home', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--native-timeout', type=int, default=600)
    parser.add_argument('--public-synthetic-input', action='store_true')
    args = parser.parse_args()
    if not args.public_synthetic_input:
        parser.error('explicit acknowledgment required before sending this synthetic fixture to the model')
    for home, executable in [(args.java_home, 'bin/java'), (args.maven_home, 'bin/mvn')]:
        if not (home.resolve() / executable).is_file():
            parser.error('missing explicitly selected public tool')
    seed = {}
    for path in sorted((CASE / 'seed').rglob('*')):
        if path.is_symlink():
            parser.error('linked seed rejected')
        if path.is_file():
            seed[path.relative_to(CASE / 'seed').as_posix()] = path.read_bytes()
    seed['app/src/test/java/example/nativeflow/LabelContractTest.java'] = (CASE / 'acceptance/LabelContractTest.java').read_bytes()
    frozen_runner = (ROOT / 'tools/native_build.py').read_bytes()
    warmups = []

    def build(workspace, offline):
        command = [sys.executable, '-B', 'verify.py'] + (['--offline'] if offline else [])
        result = subprocess.run(command, cwd=workspace, stdin=subprocess.DEVNULL, timeout=270)
        report = json.loads((workspace / '.build/validation.json').read_text())
        if result.returncode != 0 or report['status'] != 'PASSED':
            raise RuntimeError('synthetic build/test failed; inspect private instance evidence')
        return report

    def prepare(workspace, node, workflow):
        if not workflow['validate']:
            return
        (workspace / 'verify.py').write_bytes(frozen_runner)
        (workspace / '.run-config.json').write_text(json.dumps({
            'java_home': str(args.java_home.resolve()), 'maven_home': str(args.maven_home.resolve()),
            'repository': str(workspace / '.build/repository')}, indent=2) + '\n')
        report = build(workspace, offline=False)
        warmups.append({'stage': node['id'], 'candidate_id': report['candidate_id'],
                        'tests': report['tests'], 'status': report['status'], 'scope': 'online public dependency preparation before independent verifier changes'})

    def validate(workspace, node, workflow):
        if (workspace / 'verify.py').read_bytes() != frozen_runner:
            raise RuntimeError('frozen build runner changed')
        return build(workspace, offline=True)

    flow = NativeFlow(seed, ROOT, ROOT / 'graphs/native-java-spring.json', args.run_root,
                      codex=args.codex, timeout=args.native_timeout, prepare=prepare, validate=validate)
    state = flow.run()
    if state['status'] != 'SUCCEEDED':
        print('Native Spring Graph:', state['status'], '; original private state retained, no retry or publication')
        return 1
    validation = json.loads((flow.source / 'validation.json').read_text())
    source_names = ['tools/native_agents.py', 'tools/native_flow.py', 'tools/native_build.py',
                    'graphs/native-java-spring.json', 'examples/native-spring-workflow/run.py']
    source_names += [n['workflow'] for n in flow.graph['nodes']]
    source_names += [n for n in flow.catalog if n.split('/')[0] in {'agents', 'skills', 'standards'}]
    source_hashes = {n: hashlib.sha256(flow.catalog[n]).hexdigest() for n in sorted(set(source_names))}
    stages = {}
    for ident, stage in state['stages'].items():
        native = stage['native']
        stages[ident] = {key: stage[key] for key in ['status', 'started', 'ended', 'input_candidate_id', 'candidate_id', 'outputs_sha256']}
        stages[ident]['native'] = {key: native[key] for key in ['role', 'protocol', 'parent_id_sha256', 'child_id_sha256', 'spawn_calls', 'native_completed']}
    reviews = [stages[n] for n in ['code_review', 'principle_review']]
    overlap = max(x['started'] for x in reviews) < min(x['ended'] for x in reviews)
    if not overlap or stages['code_review']['input_candidate_id'] != stages['principle_review']['input_candidate_id']:
        raise RuntimeError('concurrent review evidence or frozen identity mismatch')
    receipt = {'kind': 'native_spring_graph_receipt', 'status': 'SUCCEEDED', 'synthetic': True,
               'candidate_id': state['candidate_id'], 'seed_id': state['seed_id'],
               'historical_catalog_input_id': state['catalog_id'], 'source_sha256': source_hashes,
               'stages': stages, 'review_overlap': overlap, 'validation': validation,
               'public_dependency_warmups': warmups,
               'environment': {'controller': sys.platform, 'codex': subprocess.check_output([args.codex, '--version'], text=True).strip()},
               'scope': 'six actual native roles; Spring context/MockMvc; no live HTTP, database, deployment or automatic GitHub publication'}
    (flow.root / 'public-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print('Native Spring Graph SUCCEEDED:', len(stages), 'native roles;', validation['tests'], 'real tests; review overlap:', overlap)
    print('Public receipt prepared outside repository; privacy review and explicit commit delivery still required')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
