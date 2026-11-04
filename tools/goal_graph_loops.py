"""Explicit synthetic adapters calling the real Loop controllers. No live services."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import time

from tools import finding_ledger as ledger
from tools.defect_loop import run_defect
from tools.goal_graph import demand, validate_definition
from tools.goal_graph_evidence import review_inputs
from tools.goal_graph_run import Handler
from tools.inspection_loop import inspect
from tools.native_flow import digest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'graphs/examples/goal-loops'


@dataclass(frozen=True)
class FixtureGraph:
    definition: dict
    handlers: dict
    context: dict
    expected_status: str
    read_files: tuple


def sha(content):
    return hashlib.sha256(content).hexdigest()


def fixture_graph(scenario='complete', *, case_root=CASE, clock=time.time):
    case = Path(case_root).resolve(strict=True)
    inputs = {}

    def read(name):
        demand('/' not in name and not name.startswith('.'), 'unadmitted fixture path')
        path = case / name
        demand(not path.is_symlink() and path.is_file() and path.stat().st_size <= 16384, 'invalid bounded fixture')
        content = path.read_bytes()
        inputs[name] = content
        return content

    scenarios = json.loads(read('scenarios.json'))
    demand(scenarios.get('synthetic') is True and scenario in scenarios['cases'], 'unknown synthetic scenario')
    config = scenarios['cases'][scenario]
    demand(isinstance(config, dict) and set(config) == {'authorized_sources', 'build_future', 'initial_log_complete', 'unknown_effect', 'expected_status'},
           'exact synthetic scenario policy required')
    ledger.names(config['authorized_sources'])
    demand(set(config['authorized_sources']) <= {'logs', 'api', 'build'}
           and all(type(config[key]) is bool for key in ('build_future', 'initial_log_complete', 'unknown_effect'))
           and config['expected_status'] in {'SUCCEEDED', 'PARTIAL', 'UNKNOWN'}, 'invalid source/control policy')
    candidate = json.loads(read('candidate.json'))
    before = json.loads(read('before-candidate.json'))
    demand(candidate.get('synthetic') is True and before.get('synthetic') is True, 'synthetic candidate required')
    candidate_id = sha(inputs['candidate.json'])
    defect = json.loads(read('defect-evidence.json'))
    demand(defect.get('synthetic') is True and defect.get('candidate_id') == candidate_id
           and defect.get('before_candidate_id') == sha(inputs['before-candidate.json']), 'defect fixture identity mismatch')
    # Only admitted sources are read, even during identity preparation. A future
    # observation is not made current by eagerly loading its fixture.
    if 'logs' in config['authorized_sources']:
        read('service-head.log'); read('service-tail.log')
    if 'api' in config['authorized_sources']:
        read('api-response.json')
    if 'build' in config['authorized_sources'] and not config['build_future']:
        read('build-report.json')
    read_at = clock()
    definition = json.loads((ROOT / 'graphs/evidence-goals.json').read_text())
    if config['unknown_effect']:
        definition['goals'][1]['operations'] = ['demo-effect']
    definition = validate_definition(definition)
    code_names = ('goal_graph.py', 'goal_graph_run.py', 'goal_graph_evidence.py', 'goal_graph_loops.py',
                  'finding_ledger.py', 'inspection_loop.py', 'defect_loop.py', 'native_flow.py')
    code_ids = {name: sha((ROOT / 'tools' / name).read_bytes()) for name in code_names}
    context = {'candidate_id': candidate_id,
               'requirements_id': digest({'goals': definition['goals'], 'scenario': config}),
               'rules_id': digest(code_ids)}
    input_ids = {name: sha(content) for name, content in inputs.items()}

    def publish(request, result, successful, *, unknown=False):
        result['synthetic'] = True
        result['execution_scope'] = 'actual Loop controller over frozen local fixtures; no model/service/build/deploy'
        result['input_sha256'] = dict(input_ids)
        path = request['node']['writes'][0]
        (Path(request['workspace']) / path).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return {'status': 'UNKNOWN' if unknown else 'SUCCEEDED' if successful else 'PARTIAL',
                'context': context, 'result': result, 'payload_path': None if unknown else path}

    def inspection(request):
        requirements = [{'id': 'log-window', 'source': 'logs', 'kind': 'log'},
                        {'id': 'api-response', 'source': 'api', 'kind': 'api'},
                        {'id': 'build-report', 'source': 'build', 'kind': 'build'}]
        calls = []
        def collect(requirement, step, remaining):
            calls.append({'requirement_id': requirement['id'], 'step': step})
            report = {'requirement_id': requirement['id'], 'source': requirement['source'], 'kind': requirement['kind'],
                      'context': context, 'status': 'OBSERVED', 'evidence_id': None, 'artifact_sha256': None,
                      'observed_at': read_at, 'finding': None, 'next_step': None}
            if requirement['kind'] == 'build' and config['build_future']:
                report['status'] = 'FUTURE'
                return report
            if requirement['kind'] == 'log':
                name = 'service-tail.log' if step == 'tail' or config['initial_log_complete'] else 'service-head.log'
                text = inputs[name].decode()
                demand(text.startswith('candidate_id: ' + candidate_id + '\n'), 'log fixture candidate mismatch')
                if 'WINDOW_COMPLETE' not in text:
                    report.update(status='MISSING', next_step='tail')
                if '[ERROR]' in text:
                    report['finding'] = 'Synthetic error observed in stored log window'
            else:
                name = 'api-response.json' if requirement['kind'] == 'api' else 'build-report.json'
                data = json.loads(inputs[name])
                demand(data.get('synthetic') is True and data.get('candidate_id') == candidate_id, 'source fixture candidate mismatch')
                if requirement['kind'] == 'api' and data['http_status'] >= 400:
                    report['finding'] = 'Synthetic HTTP ' + str(data['http_status'])
                if requirement['kind'] == 'build' and data['process_exit'] != 0:
                    report['finding'] = 'Synthetic stored build failure'
            report.update(evidence_id='synthetic:' + name, artifact_sha256=sha(inputs[name]))
            return report
        plan = {'scope_id': request['node']['goal_id'], 'context': context, 'requirements': requirements,
                'authorized_sources': list(config['authorized_sources']), 'max_rounds': 2,
                'budget_seconds': min(10, request['remaining_seconds']), 'deadline': request['deadline'], 'not_before': read_at - 1}
        result = inspect(plan, collect, clock=clock)
        result['adapter_calls'] = calls
        return publish(request, result, result['status'] == 'CONVERGED')

    def defect_loop(request):
        prior = {**context, 'candidate_id': sha(inputs['before-candidate.json'])}
        finding_state = ledger.create(prior)
        actor_prefix = 'simulated-' + request['run_id'] + '-' + request['execution_id'] + '-'
        def proof(ident, kind, status, checked, ctx):
            return {'id': ident, 'kind': kind, 'actor': actor_prefix + ident, 'context': ctx,
                    'artifact_sha256': sha(inputs['defect-evidence.json']), 'status': status,
                    'depends_on': sorted(ctx), 'checked_findings': checked}
        finding_state = ledger.add_evidence(finding_state, proof('original', 'code_review', 'FAILED', [], prior))
        finding_state = ledger.observe(finding_state, 'original', [defect['finding']])
        ids = ledger.unresolved(finding_state)
        finding_state = ledger.invalidate(finding_state, context)
        finding_state = ledger.add_evidence(finding_state, proof('repair', 'repair', 'PASSED', ids, context))
        finding_state = ledger.mark_repaired(finding_state, ids, 'repair')
        reviews = ['verification', 'code_review', 'principle_review']
        null_rejected = type(defect['behavior'].get('invalid_input_status')) is int and defect['behavior']['invalid_input_status'] == 400
        for stage in reviews:
            finding_state = ledger.add_evidence(finding_state, proof(stage, stage, 'PASSED' if null_rejected else 'FAILED', ids, context))
            if not null_rejected:
                finding_state = ledger.observe(finding_state, stage, [{**defect['finding'], 'finding_id': ids[0]}])
        if null_rejected:
            for ident in ids:
                finding_state = ledger.close(finding_state, ident, reviews)
        tests = defect['tests']
        valid_tests = (set(tests) == {'process_exit', 'tests', 'failures', 'errors', 'skipped'}
                       and all(type(value) is int for value in tests.values())
                       and tests == {'process_exit': 0, 'tests': 4, 'failures': 0, 'errors': 0, 'skipped': 0})
        valid = {'tests': valid_tests,
                 'behavior': null_rejected and defect['behavior'] == {'normalized': ['alpha'], 'invalid_input_status': 400},
                 'handoff': defect['handoff'] == {'recipient': 'demo-recipient', 'remaining_obligations': []}}
        calls = []
        def workflow(current):
            calls.append({'round': current['round'], 'resume_phase': current['resume_phase']})
            keys = ['tests', 'behavior', 'handoff'] if config['unknown_effect'] else ['tests'] if current['round'] == 1 else ['behavior', 'handoff']
            return {'context': context, 'finding_ledger': finding_state,
                    'checks': [{'criterion_id': key, 'kind': key, 'context': context,
                                'status': 'PASSED' if valid[key] else 'FAILED', 'evidence_id': 'synthetic:' + key,
                                'artifact_sha256': sha(inputs['defect-evidence.json']), 'observed_at': read_at} for key in keys],
                    'operations': [{'operation_id': 'demo-effect', 'status': 'UNKNOWN', 'handle': 'synthetic:pending-effect',
                                    'artifact_sha256': None}] if config['unknown_effect'] else [],
                    'next_phase': 'observe' if current['round'] == 1 else 'none'}
        plan = {'goal_id': request['node']['goal_id'], 'requirements_id': context['requirements_id'], 'rules_id': context['rules_id'],
                'criteria': [{'id': key, 'kind': key} for key in ['tests', 'behavior', 'handoff']],
                'operation_ids': list(definition['goals'][1].get('operations', [])), 'max_rounds': 2,
                'budget_seconds': min(10, request['remaining_seconds']), 'deadline': request['deadline'], 'not_before': read_at - 1}
        result = run_defect(plan, workflow, clock=clock)
        result['adapter_calls'] = calls
        return publish(request, result, result['status'] == 'COMPLETE', unknown=result['status'] == 'HOLD')

    registry = {
        'fixture-inspection': Handler(inspection, digest({'code': code_ids, 'inputs': input_ids, 'config': config, 'role': 'inspection'})),
        'fixture-defect': Handler(defect_loop, digest({'code': code_ids, 'inputs': input_ids, 'config': config, 'role': 'defect'})),
        'review-loop-evidence': Handler(review_inputs, digest({'code': code_ids, 'role': 'deterministic-review'})),
    }
    return FixtureGraph(definition, registry, context, config['expected_status'], tuple(sorted(inputs)))


def summary(state, scenario):
    return {'synthetic': True, 'scenario': scenario, 'status': state['status'], 'attempts': state['attempts'],
            'goals': state['goals'], 'scope': 'actual Graph/Loop programs; local fictional data and simulated review contexts only'}
