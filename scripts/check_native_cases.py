"""Static native Spring case consistency checks. Never invoke models or builds."""
from pathlib import Path
import hashlib
import json
import math
import os
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from tools.native_flow import digest

KIND = 'native_spring_workflow_case'
OLD_KINDS = {'role_case', 'workflow_case', 'graph_case', 'spring_build_graph_case', 'docker_spring_graph_case'}
NODES = {'requirements', 'implementation', 'verification', 'code_review', 'principle_review', 'delivery'}
HEX = re.compile(r'[0-9a-f]{64}')
# The published six-agent receipt describes these immutable pre-recovery sources.
# Never relabel its hashes as proof that the current controller ran native models.
HISTORICAL_SOURCES = {name: 'docs/native-baseline/' + name.split('/')[-1] + '.txt'
                      for name in ('tools/native_agents.py', 'tools/native_flow.py')}

HISTORICAL_CATALOG_SHA256 = '698c774e74f99e40e68a33bca08e58a01e8d0597f3bc60a05d497178097bb682'

def demand(condition, message):
    if not condition:
        raise ValueError('native case: ' + message)


def relative(name):
    demand(isinstance(name, str) and bool(name) and '\\' not in name, 'invalid relative path')
    p = Path(name)
    demand(not p.is_absolute() and p.as_posix() == name
           and all(part not in {'', '.', '..'} and not part.startswith('.') for part in name.split('/')),
           'hidden, unnormalized or escaped path')
    return name


def local(root, name):
    relative(name)
    path = root / name
    demand(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()) and path.is_file(),
           'missing, linked or escaped file')
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_file(root, name):
    return json.loads(local(root, name).read_text())


def file_set(root):
    files = set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            relative(path.relative_to(root).as_posix())
            mode = path.lstat().st_mode
            demand(not path.is_symlink() and (stat.S_ISDIR(mode) or stat.S_ISREG(mode)),
                   'linked or special carrier')
        files.update((Path(directory) / name).relative_to(root).as_posix() for name in names)
    return files


def identity(value):
    demand(isinstance(value, str) and HEX.fullmatch(value) is not None, 'invalid identity')
    return value


def safe_summary(value):
    """A limited carrier check, not a semantic privacy or rights clearance."""
    text = json.dumps(value, ensure_ascii=False)
    demand(re.search(r'(?<!\w)/(?:Users|home|private|tmp|var|opt|Library|Applications|Volumes|mnt|root)/', text) is None,
           'absolute machine path in public summary')
    demand(re.search(r'[A-Za-z]:\\\\|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_|sk-proj-', text) is None,
           'private carrier in public summary')


def check_native_case(folder):
    from tools.native_build import EXPECTED, CONTRACT_CLASS
    folder = Path(folder)
    actual = file_set(folder)
    required = {'case.json', 'README.md', 'trace.md', 'result.md', 'run.py',
                'acceptance/LabelContractTest.java', 'evidence/runtime.json', 'artifact-manifest.json'}
    demand(required <= actual, 'missing required case products')
    case = json_file(folder, 'case.json')
    demand(case.get('kind') == KIND and case.get('case_id') == folder.name
           and case.get('synthetic') is True and case.get('graph') == 'graphs/native-java-spring.json', 'case identity')
    demand(case.get('export') == {'kind': 'reversible_method_rebase', 'from': 'catalog/', 'to': '../../../'},
           'method export transformation contract')
    manifest = json_file(folder, 'artifact-manifest.json')['files']
    demand(isinstance(manifest, list), 'manifest rows')
    names = [relative(row['path']) for row in manifest]
    demand(len(names) == len(set(names)) and set(names) == actual - {'artifact-manifest.json'}, 'manifest coverage')
    for row in manifest:
        demand(identity(row['sha256']) == sha(local(folder, row['path'])), 'artifact byte drift')
    seed = {name[5:]: sha(local(folder, name)) for name in actual if name.startswith('seed/')}
    demand(seed and 'task.md' in seed and 'app/pom.xml' in seed, 'missing independent seed')
    demand(not any(name.endswith('.java') for name in seed), 'production Java hidden in seed')
    contract = 'app/src/test/java/example/nativeflow/LabelContractTest.java'
    demand(contract not in seed, 'duplicate fixed contract source')
    seed[contract] = sha(local(folder, 'acceptance/LabelContractTest.java'))
    runtime = json_file(folder, 'evidence/runtime.json')
    safe_summary(runtime)
    demand(set(runtime) == {'kind', 'status', 'synthetic', 'candidate_id', 'seed_id',
                           'historical_catalog_input_id', 'source_sha256', 'stages', 'review_overlap',
                           'validation', 'public_dependency_warmups', 'environment', 'scope'},
           'unexpected public receipt fields')
    demand(runtime.get('kind') == 'native_spring_graph_receipt' and runtime.get('status') == 'SUCCEEDED'
           and runtime.get('synthetic') is True, 'runtime status')
    demand(runtime.get('seed_id') == digest(seed), 'seed input identity')
    identity(runtime.get('historical_catalog_input_id'))  # Historical input; do not recompute from later docs.
    candidate = identity(runtime.get('candidate_id'))
    sources = runtime.get('source_sha256')
    demand(isinstance(sources, dict), 'source identities absent')
    expected_sources = {'tools/native_agents.py', 'tools/native_flow.py', 'tools/native_build.py',
                        case['graph'], 'examples/' + case['case_id'] + '/run.py'}
    # Bind this published receipt to its original catalog, not future directory additions.
    catalog_path = local(ROOT, 'docs/native-baseline/catalog-sources.json')
    demand(sha(catalog_path) == HISTORICAL_CATALOG_SHA256, 'historical catalog index drift')
    catalog = json.loads(catalog_path.read_text())['sources']
    actual_catalog = {n: v for n, v in sources.items()
                      if n.split('/')[0] in {'agents', 'skills', 'standards'}}
    demand(actual_catalog == {n: row['sha256'] for n, row in catalog.items()},
           'historical catalog coverage or identity drift')
    expected_sources.update(catalog)
    graph = json_file(ROOT, case['graph'])
    demand(graph.get('kind') == 'native_graph' and graph.get('graph_id') == 'native-java-spring'
           and graph.get('max_parallel') == 2, 'graph identity')
    nodes = graph['nodes']
    demand(len(nodes) == 6 and {n['id'] for n in nodes} == NODES, 'six node declarations required')
    dependencies = {'requirements': [], 'implementation': ['requirements'],
                    'verification': ['implementation'], 'code_review': ['verification'],
                    'principle_review': ['verification'], 'delivery': ['code_review', 'principle_review']}
    for node in nodes:
        demand(node['workflow'] == 'workflows/native-' + node['id'].replace('_', '-') + '.json'
               and node['depends_on'] == dependencies[node['id']], 'native DAG declaration drift')
    expected_sources.update(n['workflow'] for n in nodes)
    demand(expected_sources <= set(sources), 'consumed source map incomplete')
    for name, value in sources.items():
        source_path = catalog[name]['path'] if name in catalog else HISTORICAL_SOURCES.get(name, name)
        demand(identity(value) == sha(local(ROOT, source_path)), 'consumed historical source drift')
    demand(sources['examples/' + case['case_id'] + '/run.py'] == sha(local(folder, 'run.py')), 'case runner differs from consumed source')
    stages = runtime.get('stages')
    demand(isinstance(stages, dict) and set(stages) == NODES, 'stage set')
    parents, composites = set(), set()
    workflow_defs = {n['id']: json_file(ROOT, n['workflow']) for n in nodes}
    declared_markdown = {name for wf in workflow_defs.values() for name in wf['writes'] if name.endswith('.md')}
    validation_links = case.get('validation_link_rebase', [])
    abstracts = case.get('public_document_abstracts', {})
    demand(isinstance(validation_links, list) and all(isinstance(n, str) for n in validation_links)
           and len(validation_links) == len(set(validation_links))
           and set(validation_links) <= declared_markdown, 'validation link export declarations')
    demand(isinstance(abstracts, dict) and set(abstracts) <= declared_markdown,
           'abstract declarations must name Markdown workflow outputs only')
    demand(not set(validation_links) & set(abstracts), 'abstract is not a reversible link export')
    for name in set(validation_links) | set(abstracts):
        relative(name)
        demand('/' not in name, 'document export limited to final root Markdown')
    for meta in abstracts.values():
        demand(isinstance(meta, dict) and set(meta) == {'kind', 'native_sha256', 'public_sha256'}
               and meta.get('kind') == 'independent_public_summary', 'unsafe abstract metadata structure')
        identity(meta.get('native_sha256')); identity(meta.get('public_sha256'))
    product_names = set(seed) | {'validation.json'}
    for node in nodes:
        workflow = workflow_defs[node['id']]
        stage = stages[node['id']]
        demand(set(stage) == {'status', 'started', 'ended', 'input_candidate_id', 'candidate_id',
                              'outputs_sha256', 'native'}, 'unexpected stage receipt fields')
        product_names.update(workflow['writes'])
        demand(workflow.get('kind') == 'native_workflow' and workflow.get('role') == 'workflow_' + node['id'] and stage.get('status') == 'SUCCEEDED', 'workflow or stage status')
        native = stage.get('native', {})
        demand(set(native) == {'role', 'protocol', 'parent_id_sha256', 'child_id_sha256',
                               'spawn_calls', 'native_completed'}, 'unexpected native receipt fields')
        demand(native.get('role') == workflow.get('role') and native.get('protocol') == 'codex-collaboration-rollout-v1'
               and type(native.get('spawn_calls')) is int and native['spawn_calls'] == 1
               and native.get('native_completed') is True, 'native role/call/completion')
        parent, child = identity(native.get('parent_id_sha256')), identity(native.get('child_id_sha256'))
        parents.add(parent); composites.add((parent, child))
        start, end = stage.get('started'), stage.get('ended')
        demand(all(type(v) in {int, float} and math.isfinite(v) and v > 0 for v in [start, end])
               and start < end, 'stage time interval')
        for dependency in node['depends_on']:
            demand(dependency in stages and stages[dependency]['ended'] <= start, 'dependency ordering')
        outputs = stage.get('outputs_sha256')
        demand(isinstance(outputs, dict) and set(outputs) == set(workflow['writes'])
               and len(workflow['writes']) == len(set(workflow['writes'])), 'workflow write set')
        for name, value in outputs.items():
            target = local(folder, 'final/' + relative(name))
            if name in abstracts:
                # This is an explicitly derived public document, not a byte-preserving export.
                meta = abstracts[name]
                demand(identity(value) == meta['native_sha256'] and sha(target) == meta['public_sha256'],
                       'abstract native/public identity mapping')
                lines = target.read_text().splitlines()
                demand(lines and lines[0] == 'candidate_id: ' + candidate, 'abstract candidate identity')
            else:
                if name.endswith('.md'):
                    demand('/' not in name, 'method rebasing limited to final root Markdown')
                    exported = target.read_bytes()
                    demand(b'catalog/' not in exported, 'incomplete method link export')
                    if name in validation_links:
                        demand(b'](.build/validation.json)' not in exported, 'incomplete validation link export')
                        exported = exported.replace(b'](validation.json)', b'](.build/validation.json)')
                        lines = target.read_text().splitlines()
                        demand(lines and lines[0] == 'candidate_id: ' + candidate, 'validation-link document candidate')
                    restored = exported.replace(b'../../../', b'catalog/')
                    output_sha = hashlib.sha256(restored).hexdigest()
                else:
                    output_sha = sha(target)
                demand(identity(value) == output_sha, 'native stage output drift after inverse export')
        for field in ['input_candidate_id', 'candidate_id']:
            identity(stage.get(field))
        if workflow['preserve_candidate'] or workflow['validate']:
            demand(stage['candidate_id'] == candidate, 'frozen stage candidate')
            for name in workflow['writes']:
                if name.endswith('.md'):
                    lines = local(folder, 'final/' + name).read_text().splitlines()
                    demand(lines and lines[0] == 'candidate_id: ' + candidate, 'document candidate drift')
    demand({name for name in actual if name.startswith('final/')} == {'final/' + name for name in product_names},
           'unexpected or missing final source product')
    demand(actual == required | {'seed/' + name for name in seed if name != contract}
           | {'final/' + name for name in product_names}, 'unexpected public case carrier')
    demand(len(parents) == len(composites) == 6, 'distinct native parent contexts')
    demand(stages['requirements']['input_candidate_id'] == digest({n: v for n, v in seed.items() if n == 'app/pom.xml' or n.startswith('app/src/')})
           and stages['requirements']['input_candidate_id'] == stages['requirements']['candidate_id'], 'requirements changed source')
    demand(stages['implementation']['input_candidate_id'] == stages['requirements']['candidate_id']
           and stages['verification']['input_candidate_id'] == stages['implementation']['candidate_id']
           and stages['verification']['candidate_id'] == candidate, 'candidate handoff order')
    for name in ['code_review', 'principle_review', 'delivery']:
        demand(stages[name]['input_candidate_id'] == stages[name]['candidate_id'] == candidate, 'review/delivery candidate mismatch')
    left, right = stages['code_review'], stages['principle_review']
    demand(runtime.get('review_overlap') is True and max(left['started'], right['started']) < min(left['ended'], right['ended']),
           'native review overlap')
    validation = json_file(folder, 'final/validation.json')
    demand(runtime.get('validation') == validation, 'public and final validation differ')
    final_sources = {name[6:]: sha(local(folder, name)) for name in actual
                     if name == 'final/app/pom.xml' or name.startswith('final/app/src/')}
    demand(final_sources and validation.get('source_sha256') == final_sources
           and validation.get('candidate_id') == candidate == digest(final_sources), 'final candidate identity')
    demand(validation.get('status') == 'PASSED' and type(validation.get('process_exit')) is int
           and validation['process_exit'] == 0 and validation.get('offline') is True
           and validation.get('contract_complete') is True
           and all(validation.get(k) == [] for k in ['failures', 'errors', 'skipped']), 'validation not passing offline')
    tests = validation.get('test_names')
    demand(isinstance(tests, list) and all(isinstance(n, str) for n in tests)
           and type(validation.get('tests')) is int and validation['tests'] == len(tests)
           and len(tests) == len(set(tests)), 'JUnit names/counts')
    contract_names = [n[len(CONTRACT_CLASS) + 1:] for n in tests if n.startswith(CONTRACT_CLASS + '#')]
    demand(len(contract_names) == 13 and set(contract_names) == EXPECTED, 'fixed contract methods incomplete')
    demand(isinstance(runtime.get('public_dependency_warmups'), list) and runtime['public_dependency_warmups']
           and all(isinstance(x, dict) for x in runtime['public_dependency_warmups']), 'warmup record absent')
    demand(isinstance(runtime.get('environment'), dict) and bool(runtime['environment'])
           and isinstance(runtime.get('scope'), str) and bool(runtime['scope']), 'runtime boundaries absent')


def main():
    count = 0
    for folder in sorted((ROOT / 'examples').iterdir()):
        if not folder.is_dir(): continue
        if folder.name == 'bookmark-title':
            demand(not (folder / 'case.json').exists(), 'legacy example kind mismatch')
            continue
        case = json_file(folder, 'case.json')
        kind = case.get('kind', 'role_case' if 'agent' in case and 'skill' in case else None)
        demand(kind in OLD_KINDS | {KIND}, 'unknown example kind')
        if kind == KIND:
            check_native_case(folder)
            count += 1
    print(f'PASS: {count} native Spring cases; static source/record/identity consistency only; no models or builds executed')


if __name__ == '__main__':
    main()
