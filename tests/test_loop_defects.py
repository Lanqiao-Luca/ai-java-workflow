"""Whole-goal counterexamples with fabricated Workflow packets, never business writes."""
from copy import deepcopy
from pathlib import Path
import runpy
import unittest

from tools import finding_ledger as ledger
from tools.defect_loop import run_defect


CONTEXT = {'candidate_id': 'a' * 64, 'requirements_id': 'b' * 64, 'rules_id': 'c' * 64}


def plan():
    return {'goal_id': 'synthetic-defect', 'requirements_id': CONTEXT['requirements_id'],
            'rules_id': CONTEXT['rules_id'], 'criteria': [{'id': key, 'kind': key} for key in ['tests', 'behavior', 'handoff']],
            'operation_ids': [], 'max_rounds': 3, 'budget_seconds': 30, 'deadline': 130, 'not_before': 90}


def packet(keys=('tests',), *, phase='observe', bindings=None):
    bindings = bindings or CONTEXT
    return {'context': dict(bindings), 'finding_ledger': ledger.create(bindings),
            'checks': [{'criterion_id': key, 'kind': key, 'context': dict(bindings), 'status': 'PASSED',
                        'evidence_id': 'synthetic-' + key, 'artifact_sha256': 'd' * 64, 'observed_at': 100} for key in keys],
            'operations': [], 'next_phase': phase}


class DefectTests(unittest.TestCase):
    def run_packets(self, packets, p=None, clock=lambda: 100):
        self.requests = []
        def workflow(request):
            self.requests.append(request)
            return deepcopy(packets[min(len(self.requests) - 1, len(packets) - 1)])
        return run_defect(p or plan(), workflow, clock=clock)

    def test_tests_passed_is_not_whole_goal_complete(self):
        result = self.run_packets([packet(phase='none')])
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['missing_criteria'], ['behavior', 'handoff'])
        self.assertFalse(result['goal_met'])

    def test_next_phase_fills_obligations_and_reuses_current_tests(self):
        result = self.run_packets([packet(), packet(['behavior', 'handoff'], phase='none')])
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(result['rounds_used'], 2)
        self.assertEqual(self.requests[1]['resume_phase'], 'observe')
        self.assertEqual(self.requests[1]['missing_criteria'], ['behavior', 'handoff'])

    def test_candidate_change_invalidates_tests_but_not_accepted_side_effect(self):
        p = plan(); p['operation_ids'] = ['effect']
        first = packet()
        first['operations'] = [{'operation_id': 'effect', 'status': 'SUCCEEDED', 'handle': 'synthetic-original', 'artifact_sha256': 'e' * 64}]
        second = packet(['behavior', 'handoff'], phase='none', bindings={**CONTEXT, 'candidate_id': 'f' * 64})
        result = self.run_packets([first, second], p)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['missing_criteria'], ['tests'])
        self.assertEqual(result['missing_operations'], [])
        self.assertEqual(result['operations']['effect']['handle'], 'synthetic-original')
        self.assertEqual(result['checks']['tests']['status'], 'STALE')
        self.assertEqual(result['checks']['tests']['previous_status'], 'PASSED')

    def test_unknown_effect_holds_without_second_workflow_call(self):
        p = plan(); p['operation_ids'] = ['effect']
        first = packet(['tests', 'behavior', 'handoff'])
        first['operations'] = [{'operation_id': 'effect', 'status': 'UNKNOWN', 'handle': 'synthetic-pending', 'artifact_sha256': None}]
        result = self.run_packets([first], p)
        self.assertEqual(result['status'], 'HOLD')
        self.assertEqual(len(self.requests), 1)

    def test_missing_operation_receipt_cannot_complete(self):
        p = plan(); p['operation_ids'] = ['effect']
        result = self.run_packets([packet(['tests', 'behavior', 'handoff'], phase='none')], p)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['missing_operations'], ['effect'])

    def test_operation_handle_cannot_change_on_next_round(self):
        p = plan(); p['operation_ids'] = ['effect']
        first = packet()
        first['operations'] = [{'operation_id': 'effect', 'status': 'SUCCEEDED', 'handle': 'first', 'artifact_sha256': 'e' * 64}]
        second = packet(['behavior', 'handoff'])
        second['operations'] = [{**first['operations'][0], 'handle': 'different'}]
        result = self.run_packets([first, second], p)
        self.assertEqual(result['reason'], 'INVALID_OR_UNAVAILABLE_WORKFLOW_RESULT')
        self.assertEqual(result['operations']['effect']['handle'], 'first')

    def test_unchanged_evidence_stops_without_using_all_rounds(self):
        result = self.run_packets([packet()])
        self.assertEqual(result['status'], 'NO_PROGRESS')
        self.assertEqual(len(self.requests), 2)

    def test_original_acceptance_cannot_be_narrowed_or_rebound(self):
        for change in [{'requirements_id': 'f' * 64}, {'rules_id': 'f' * 64}]:
            result = self.run_packets([packet(bindings={**CONTEXT, **change})])
            self.assertEqual(result['status'], 'PARTIAL')
            self.assertEqual(result['missing_criteria'], ['tests', 'behavior', 'handoff'])

    def test_open_finding_blocks_even_all_acceptance_receipts_pass(self):
        value = packet(['tests', 'behavior', 'handoff'], phase='none')
        failure = {'id': 'failure', 'kind': 'code_review', 'actor': 'original-reviewer', 'context': CONTEXT,
                   'artifact_sha256': 'd' * 64, 'status': 'FAILED', 'depends_on': sorted(CONTEXT), 'checked_findings': []}
        value['finding_ledger'] = ledger.add_evidence(value['finding_ledger'], failure)
        item = {'finding_id': None, 'key': 'null-input', 'summary': 'Null input accepted', 'location': 'Demo.normalize', 'criterion': 'Reject null input'}
        value['finding_ledger'] = ledger.observe(value['finding_ledger'], 'failure', [item])
        result = self.run_packets([value])
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(len(result['unresolved_findings']), 1)
        # A following Workflow cannot drop the issue/history to manufacture COMPLETE.
        value['next_phase'] = 'repair'
        result = self.run_packets([value, packet(['tests', 'behavior', 'handoff'], phase='none')])
        self.assertEqual(result['reason'], 'INVALID_OR_UNAVAILABLE_WORKFLOW_RESULT')

    def test_forged_closed_string_without_proofs_is_rejected(self):
        value = packet(['tests', 'behavior', 'handoff'], phase='none')
        value['finding_ledger']['findings']['F-forged'] = {'id': 'F-forged', 'status': 'CLOSED', 'observations': ['missing']}
        result = self.run_packets([value])
        self.assertFalse(result['goal_met'])

    def test_deadline_and_late_workflow_result_cannot_complete(self):
        ticks = [100]
        def workflow(request):
            ticks[0] = 131
            return packet(['tests', 'behavior', 'handoff'])
        result = run_defect(plan(), workflow, clock=lambda: ticks[0])
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertFalse(result['goal_met'])
        self.assertEqual(len(result['history']), 1)

    def test_round_cap_and_no_budget_renewal(self):
        p = plan(); p['max_rounds'] = 1
        result = self.run_packets([packet()], p)
        self.assertEqual(result['reason'], 'ROUND_LIMIT')
        self.assertEqual(result['deadline'], 130)

    def test_actual_fixture_packets_reach_three_distinct_outcomes(self):
        root = Path(__file__).resolve().parents[1]
        examples = runpy.run_path(str(root / 'loops/examples/defect/run.py'))['run_examples']()
        self.assertEqual({key: value['status'] for key, value in examples.items()},
                         {'tests_only': 'PARTIAL', 'complete': 'COMPLETE', 'unknown_effect': 'HOLD'})
        self.assertEqual(examples['complete']['rounds_used'], 2)
        self.assertEqual(examples['unknown_effect']['rounds_used'], 1)
        self.assertTrue(all(f['status'] == 'CLOSED' for f in examples['complete']['finding_ledger']['findings'].values()))

    def test_closed_receipt_cannot_hide_same_author_or_rewritten_failure(self):
        root = Path(__file__).resolve().parents[1]
        completed = runpy.run_path(str(root / 'loops/examples/defect/run.py'))['run_examples']()['complete']
        p = {**plan(), 'requirements_id': completed['context']['requirements_id'],
             'rules_id': completed['context']['rules_id'], 'deadline': 1030, 'not_before': 1000}
        value = {'context': completed['context'], 'finding_ledger': completed['finding_ledger'],
                 'checks': list(completed['checks'].values()), 'operations': [], 'next_phase': 'none'}
        for change in ['same_author', 'rewrite_failure', 'unbound_review']:
            altered = deepcopy(value)
            if change == 'same_author':
                altered['finding_ledger']['evidence']['code_review']['actor'] = 'simulated-context-repair'
            elif change == 'rewrite_failure':
                altered['finding_ledger']['evidence']['original-review']['status'] = 'PASSED'
            else:
                altered['finding_ledger']['evidence']['code_review']['depends_on'] = []
            result = self.run_packets([altered], p, clock=lambda: 1005)
            self.assertFalse(result['goal_met'])
            self.assertEqual(result['reason'], 'INVALID_OR_UNAVAILABLE_WORKFLOW_RESULT')

    def test_invalid_plan_is_rejected_before_workflow(self):
        for change in [{'max_rounds': True}, {'budget_seconds': float('nan')},
                       {'criteria': [{'id': 'tests', 'kind': 'tests'}]}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_packets([packet()], {**plan(), **change})


if __name__ == '__main__':
    unittest.main()
