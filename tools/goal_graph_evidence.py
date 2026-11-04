"""Typed Loop admission and deterministic Gate receipts, not model review claims."""
from pathlib import Path
import json
import math

from tools.defect_loop import _ledger
from tools.finding_ledger import identity, names
from tools.goal_graph import GoalGraphRejected, demand
from tools.native_flow import digest


def named(values):
    try:
        names(values)
    except ValueError as exc:
        raise GoalGraphRejected('invalid evidence references') from exc


def sha(value):
    try:
        identity(value)
    except ValueError as exc:
        raise GoalGraphRejected('invalid evidence SHA256') from exc


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_loop(node, record, goal, context, deadline):
    result = record['result']
    expected = goal['required'] if goal else []
    named(result.get('required')); named(expected)
    demand(set(result['required']) == set(expected), 'original goal scope was reduced or changed')
    if node['contract'] == 'task':
        named(result.get('completed'))
        demand(result.get('complete') is True and result.get('goal_id') == node['goal_id']
               and set(result['completed']) == set(expected), 'task evidence is incomplete')
        return
    demand(result.get('context') == context and finite(result.get('deadline'))
           and result['deadline'] <= deadline and finite(result.get('elapsed')), 'Loop identity/time budget mismatch')
    demand(finite(result.get('started_at')) and result['started_at'] <= record['ended_at']
           and result['elapsed'] <= result['deadline'] - result['started_at']
           and type(result.get('rounds_used')) is int and 1 <= result['rounds_used'] <= 10,
           'Loop budget/round accounting is not current finite evidence')
    if node['contract'] == 'inspection':
        named(result.get('covered')); named(result.get('missing'))
        demand(result.get('scope_id') == node['goal_id'] and result.get('status') == 'CONVERGED'
               and result.get('scope_complete') is True and result['missing'] == []
               and set(result['covered']) == set(expected) and result.get('reasons') == {}, 'inspection has unresolved scope')
        observations = result.get('observations')
        demand(isinstance(observations, list), 'inspection observations required')
        observed = set()
        for row in observations:
            demand(isinstance(row, dict) and row.get('requirement_id') in expected, 'observation outside frozen goal')
            if row.get('status') == 'OBSERVED':
                sha(row.get('artifact_sha256'))
                demand(row.get('context') == context and isinstance(row.get('evidence_id'), str)
                       and bool(row['evidence_id']) and finite(row.get('observed_at'))
                       and row['observed_at'] <= min(result['deadline'], record['ended_at']), 'stale/late inspection evidence')
                observed.add(row['requirement_id'])
        demand(observed == set(expected), 'coverage has no actual observation evidence')
        # Findings may be nonempty: coverage completion never means healthy service.
    else:
        demand(result.get('goal_id') == node['goal_id'] and result.get('status') == 'COMPLETE'
               and result.get('goal_met') is True and result.get('missing_criteria') == []
               and result.get('missing_operations') == [] and result.get('unresolved_findings') == [], 'defect goal is incomplete')
        checks = result.get('checks')
        demand(isinstance(checks, dict) and set(checks) == set(expected), 'original defect acceptance evidence missing')
        for ident, row in checks.items():
            sha(row.get('artifact_sha256'))
            demand(row.get('criterion_id') == ident and row.get('context') == context
                   and row.get('status') == 'PASSED' and isinstance(row.get('evidence_id'), str)
                   and bool(row['evidence_id']) and finite(row.get('observed_at'))
                   and row['observed_at'] <= min(result['deadline'], record['ended_at']), 'invalid current defect receipt')
        demand({'tests', 'behavior', 'handoff'} <= {row.get('kind') for row in checks.values()}, 'whole defect obligations missing')
        named(result.get('required_operations'))
        operations = result.get('operations')
        demand(set(result['required_operations']) == set(goal.get('operations', []))
               and isinstance(operations, dict) and set(operations) == set(result['required_operations']), 'required side effect disappeared')
        for ident, operation in operations.items():
            sha(operation.get('artifact_sha256'))
            demand(operation.get('operation_id') == ident and operation.get('status') == 'SUCCEEDED'
                   and isinstance(operation.get('handle'), str) and bool(operation['handle']), 'unknown or unproven side effect')
        try:
            _, unresolved = _ledger(None, result.get('finding_ledger'), context)
        except (ValueError, TypeError, KeyError) as exc:
            raise GoalGraphRejected('invalid independent finding closure evidence') from exc
        demand(not unresolved, 'unclosed finding')


def review_metadata(node, inputs, context, run_id, reviewer_identity, execution_id):
    targets = {}
    for ident, item in inputs.items():
        record = item['record']
        demand(record['status'] == 'SUCCEEDED' and record['context'] == context, 'gate input is not current success')
        path = record['payload_path']
        demand(path in record['products'], 'gate input lacks physical evidence')
        targets[ident] = {'execution_id': record['execution_id'], 'contract': item['node']['contract'],
                         'payload_sha256': record['products'][path]['sha256'],
                         'products_id': digest(record['products'])}
    demand(set(targets) == set(node['depends_on']), 'gate omitted declared dependency')
    snapshot = {'run_id': run_id, 'gate_id': node['id'], 'gate_execution_id': execution_id,
                'context': context, 'targets': targets}
    return {'reviewer': {'handler': node['handler'], 'identity': reviewer_identity},
            'context': context, 'run_id': run_id, 'gate_id': node['id'], 'gate_execution_id': execution_id,
            'snapshot_id': digest(snapshot), 'targets': targets}


def closure_metadata(definition, records, context, run_id):
    targets = {n['id']: {'execution_id': records[n['id']]['execution_id'],
                        'products_id': digest(records[n['id']]['products']),
                        'result_id': digest(records[n['id']]['result'])}
               for n in definition['nodes'] if n['required'] and n['kind'] != 'closure'}
    binding = {'run_id': run_id, 'context': context, 'goals': definition['goals'], 'targets': targets}
    return {'closed_goals': [g['id'] for g in definition['goals']], 'targets': targets,
            'run_id': run_id, 'snapshot_id': digest(binding)}


def review_inputs(request):
    """Actual deterministic file/contract reviewer. No model or external audit."""
    from tools.goal_graph_run import products
    for item in request['inputs'].values():
        record, node = item['record'], item['node']
        workspace = Path(item['workspace'])
        demand(products(workspace, node['writes']) == record['products'], 'gate product drift')
        demand(json.loads((workspace / record['payload_path']).read_text()) == record['result'], 'gate payload drift')
        validate_loop(node, record, item['goal'], request['context'], request['deadline'])
    return {'status': 'SUCCEEDED', 'context': request['context'], 'payload_path': None,
            'result': {'verdict': 'PASS', **request['review_metadata']}}
