"""Negative controls for supplied observation quality; never contact a real source."""
from copy import deepcopy
from pathlib import Path
import json
import runpy
import unittest
from tools.evidence_coverage import CoverageError, assess
ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'workflows/examples/evidence-coverage'


class EvidenceCoverageTests(unittest.TestCase):
    def setUp(self):
        cases = json.loads((CASE / 'scenarios.json').read_text())['cases']
        self.cases = {case['name']: case for case in cases}

    def result(self, name):
        case = self.cases[name]
        return assess(case['scope'], case['pages'])

    def test_complete_empty_is_bounded_and_needs_control(self):
        result = self.result('bounded_empty')
        self.assertEqual(result['absence'], 'bounded_empty')
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(result['pages_observed'], 2)
        self.assertEqual(self.result('zero_without_control')['absence'], 'unknown')

    def test_sample_match_cannot_claim_full_coverage(self):
        result = self.result('sample_match')
        self.assertEqual(result['match_ids'], ['match-one'])
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(result['absence'], 'unknown')

    def test_budget_and_truncation_preserve_partial(self):
        for name in ('budget_partial', 'truncated'):
            with self.subTest(name=name):
                self.assertEqual(self.result(name)['status'], 'PARTIAL')
                self.assertEqual(self.result(name)['absence'], 'unknown')

    def test_failure_and_unknown_are_not_successful_zero(self):
        for name in ('unknown', 'denied'):
            with self.subTest(name=name):
                self.assertEqual(self.result(name)['absence'], 'unknown')
                self.assertFalse(self.result(name)['coverage_complete'])

    def test_unexecuted_is_not_empty_query(self):
        result = assess(self.cases['bounded_empty']['scope'], [])
        self.assertEqual(result['status'], 'NOT_RUN')
        self.assertEqual(result['absence'], 'unknown')

    def test_source_snapshot_and_query_must_match(self):
        for field in ('source_id', 'snapshot', 'needle'):
            with self.subTest(field=field):
                case = deepcopy(self.cases['bounded_empty'])
                case['pages'][1][field] = 'different'
                with self.assertRaises(CoverageError):
                    assess(case['scope'], case['pages'])

    def test_cursor_gap_is_rejected(self):
        case = self.cases['bounded_empty']
        case['pages'][1]['cursor_in'] = 'unrelated'
        with self.assertRaises(CoverageError):
            assess(case['scope'], case['pages'])

    def test_row_identity_reuse_is_rejected(self):
        case = self.cases['bounded_empty']
        case['pages'][1]['rows'] = case['pages'][0]['rows'][:]
        with self.assertRaises(CoverageError):
            assess(case['scope'], case['pages'])

    def test_sample_stops_without_consuming_extra_page(self):
        case = self.cases['sample_match']
        case['pages'].append(deepcopy(self.cases['bounded_empty']['pages'][1]))
        with self.assertRaises(CoverageError):
            assess(case['scope'], case['pages'])

    def test_failed_query_cannot_carry_success_rows(self):
        case = self.cases['unknown']
        case['pages'][0]['rows'] = [{'id': 'fake', 'text': 'ALPHA'}]
        with self.assertRaises(CoverageError):
            assess(case['scope'], case['pages'])

    def test_page_budget_cannot_be_silently_broadened(self):
        case = self.cases['bounded_empty']
        case['scope']['max_pages'] = 1
        with self.assertRaises(CoverageError):
            assess(case['scope'], case['pages'])

    def test_fixture_program_executes_all_eight_outcomes_without_requests(self):
        result = runpy.run_path(str(CASE / 'run.py'))['run_examples']()
        self.assertEqual(result['source_requests'], 0)
        self.assertEqual(len(result['results']), 8)
        self.assertEqual(result['results']['complete_match']['status'], 'COMPLETE_MATCH')


if __name__ == '__main__':
    unittest.main()
