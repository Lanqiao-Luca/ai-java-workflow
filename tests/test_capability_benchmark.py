"""Check metric directions, unknowns, bounded restores and fixed input identity."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from tools.capability_benchmark import evaluate, summarize, source_hashes, run_benchmark

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'workflows/examples/capability-benchmark'
BASE = ROOT / 'workflows/examples/conclusion-challenge'


class CapabilityBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((CASE / 'cases.json').read_text())['cases']
        self.base = json.loads((BASE / 'review.json').read_text())
        self.candidate = self.base['candidate_sha256']

    def test_actual_fixed_comparison_detects_missing_contract_checks(self):
        result = run_benchmark()
        self.assertEqual(result['status'], 'COMPLETED')
        strong = result['results']['contract_checker']['metrics']
        weak = result['results']['minimal_fields']['metrics']
        self.assertEqual((strong['tasks'], strong['correct'], strong['misses'], strong['false_alarms']), (8, 8, 0, 0))
        self.assertEqual((weak['correct'], weak['misses'], weak['false_alarms']), (3, 5, 0))
        self.assertEqual(result['human_rework'], 'NOT_MEASURED')

    def test_false_alarm_and_miss_directions_have_separate_denominators(self):
        result = evaluate(self.cases, self.base, self.candidate,
                          {'reject_all': lambda r, c: False, 'accept_all': lambda r, c: True})
        reject = result['reject_all']['metrics']
        accept = result['accept_all']['metrics']
        self.assertEqual((reject['false_alarms'], reject['misses'], reject['recall']), (3, 0, 1))
        self.assertEqual((accept['false_alarms'], accept['misses'], accept['precision']), (0, 5, None))
        self.assertIsNone(summarize([])['accuracy'])

    def test_same_input_and_actual_scripted_restore_calls_are_counted(self):
        calls = []
        def strategy(report, candidate):
            calls.append((deepcopy(report), candidate))
            return True
        result = evaluate(self.cases, self.base, self.candidate, {'recording': strategy})
        self.assertEqual(len(calls), len(self.cases) + 5)
        self.assertEqual(result['recording']['metrics']['scripted_restores'], 5)
        self.assertTrue(all('expected_valid' not in report and 'edit' not in report for report, _ in calls))
        self.assertEqual(self.base['candidate_sha256'], self.candidate)

    def test_unknown_strategy_cannot_be_zero_cost_or_correct(self):
        def crash(report, candidate):
            raise RuntimeError('simulated')
        result = evaluate(self.cases, self.base, self.candidate, {'crash': crash})['crash']
        self.assertEqual(result['metrics']['unknown'], 8)
        self.assertEqual(result['metrics']['correct'], 0)
        self.assertIsNone(result['metrics']['accuracy'])
        self.assertEqual(result['metrics']['scripted_restores'], 0)

    def test_non_boolean_strategy_result_remains_unknown(self):
        result = evaluate(self.cases, self.base, self.candidate, {'invalid': lambda r, c: 'yes'})
        self.assertEqual(result['invalid']['metrics']['unknown'], 8)

    def test_failed_restoration_is_recorded_instead_of_claimed_complete(self):
        result = evaluate(self.cases, self.base, self.candidate, {'reject': lambda r, c: False})['reject']
        self.assertEqual(result['metrics']['scripted_restores'], 5)
        self.assertEqual(result['metrics']['restore_failures'], 5)
        self.assertEqual(result['metrics']['restore_unknowns'], 0)

    def test_duplicate_task_or_non_boolean_label_rejected(self):
        cases = deepcopy(self.cases)
        cases[1]['id'] = cases[0]['id']
        with self.assertRaises(ValueError):
            evaluate(cases, self.base, self.candidate)
        cases = deepcopy(self.cases)
        cases[0]['expected_valid'] = 1
        with self.assertRaises(ValueError):
            evaluate(cases, self.base, self.candidate)

    def test_invalid_or_negative_elapsed_measurement_is_rejected(self):
        row = {'state': 'DONE', 'decision': 'VALID', 'expected_valid': True,
               'nanoseconds': 10, 'repair': {'attempts': 0}}
        for value in (None, '10', -1, True):
            row['nanoseconds'] = value
            with self.assertRaises(ValueError):
                summarize([row])

    def test_published_observations_recompute_and_bind_current_inputs(self):
        receipt = json.loads((CASE / 'result.json').read_text())
        self.assertEqual(receipt['source_sha256'], source_hashes())
        for group in receipt['results'].values():
            self.assertEqual(group['metrics'], summarize(group['observations']))
        self.assertEqual(receipt['source_requests'], 0)


if __name__ == '__main__':
    unittest.main()
