"""Execute synthetic whole-goal packets and ledger transitions, never model/deploy."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[2]
sys.path.insert(0, str(ROOT))
from tools import finding_ledger as ledger
from tools.defect_loop import run_defect


def sha(content):
    return hashlib.sha256(content).hexdigest()


def run_examples():
    raw = (CASE / 'evidence.json').read_bytes()
    data = json.loads(raw)
    if data.get('synthetic') is not True:
        raise ValueError('explicitly synthetic evidence required')
    criteria = [{'id': key, 'kind': key} for key in ['tests', 'behavior', 'handoff']]
    bindings = {'candidate_id': sha((CASE / 'candidate.json').read_bytes()),
                'requirements_id': sha(json.dumps(criteria, sort_keys=True).encode()),
                'rules_id': sha((ROOT / 'tools/defect_loop.py').read_bytes())}
    before = {**bindings, 'candidate_id': sha((CASE / 'before-candidate.json').read_bytes())}
    finding_state = ledger.create(before)

    def proof(ident, kind, status, checked, ctx):
        return {'id': ident, 'kind': kind, 'actor': 'simulated-context-' + ident,
                'context': ctx, 'artifact_sha256': sha(raw), 'status': status,
                'depends_on': sorted(ctx), 'checked_findings': checked}

    finding_state = ledger.add_evidence(finding_state, proof('original-review', 'code_review', 'FAILED', [], before))
    finding_state = ledger.observe(finding_state, 'original-review', [data['finding']])
    ids = ledger.unresolved(finding_state)
    finding_state = ledger.invalidate(finding_state, bindings)
    finding_state = ledger.add_evidence(finding_state, proof('repair', 'repair', 'PASSED', ids, bindings))
    finding_state = ledger.mark_repaired(finding_state, ids, 'repair')
    checks = ['verification', 'code_review', 'principle_review']
    for stage in checks:
        finding_state = ledger.add_evidence(finding_state, proof(stage, stage, 'PASSED', ids, bindings))
    for ident in ids:
        finding_state = ledger.close(finding_state, ident, checks)
    valid = {'tests': data['tests'] == {'process_exit': 0, 'tests': 4, 'failures': 0, 'errors': 0, 'skipped': 0},
             'behavior': data['behavior'] == {'normalized': ['alpha'], 'invalid_input_status': 400},
             'handoff': data['handoff'] == {'recipient': 'demo-recipient', 'remaining_obligations': []}}

    def packet(keys, next_phase='none', operations=None):
        return {'context': bindings, 'finding_ledger': finding_state,
                'checks': [{'criterion_id': key, 'kind': key, 'context': bindings,
                            'status': 'PASSED' if valid[key] else 'FAILED', 'evidence_id': 'synthetic:' + key,
                            'artifact_sha256': sha(raw), 'observed_at': 1001} for key in keys],
                'operations': operations or [], 'next_phase': next_phase}

    plan = {'goal_id': 'synthetic-label-defect', 'requirements_id': bindings['requirements_id'],
            'rules_id': bindings['rules_id'], 'criteria': criteria, 'operation_ids': [],
            'max_rounds': 3, 'budget_seconds': 20, 'deadline': 1025, 'not_before': 1000}
    results = {}
    cases = {'tests_only': [packet(['tests'])],
             'complete': [packet(['tests'], 'observe'), packet(['behavior', 'handoff'])],
             'unknown_effect': [packet(['tests', 'behavior', 'handoff'], 'observe', [
                 {'operation_id': 'demo-effect', 'status': 'UNKNOWN', 'handle': 'synthetic:pending-1', 'artifact_sha256': None}])]}
    for name, packets in cases.items():
        local_plan = {**plan, 'operation_ids': ['demo-effect'] if name == 'unknown_effect' else []}
        result = run_defect(local_plan, lambda request: packets[min(request['round'] - 1, len(packets) - 1)], clock=lambda: 1005)
        expected = {'tests_only': 'PARTIAL', 'complete': 'COMPLETE', 'unknown_effect': 'HOLD'}[name]
        if result['status'] != expected:
            raise ValueError('unexpected whole-goal result')
        results[name] = result
    return results


if __name__ == '__main__':
    print(json.dumps({'synthetic': True, 'execution': 'fixture packets and simulated review contexts only', 'results': run_examples()}, indent=2))
