"""Bind new Spring receipts to their actual source; do not rerun Java in portable CI."""
from pathlib import Path
import hashlib
import json
import runpy
import unittest
from tools.module_plan import validate_plan
CASE = Path(__file__).resolve().parents[1] / 'examples/design-to-spring'


class DesignSpringEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(CASE / 'run.py'))
        self.result = json.loads((CASE / 'result.json').read_text())

    def test_receipt_is_bound_to_current_design_plan_and_application(self):
        actual = self.runner['source_hashes']()
        self.assertEqual(actual, self.result['source_sha256'])
        self.assertEqual(self.runner['candidate_id'](actual), self.result['candidate_id'])
        self.assertEqual(hashlib.sha256((CASE / 'run.py').read_bytes()).hexdigest(), self.result['runner_sha256'])

    def test_design_contract_and_single_writer_plan_are_consistent(self):
        contract = json.loads((CASE / 'contract.json').read_text())
        plan = json.loads((CASE / 'plan.json').read_text())
        self.assertEqual(contract['sha256'], hashlib.sha256((CASE / 'design.md').read_bytes()).hexdigest())
        self.assertEqual(validate_plan(plan, contract)['requirement_count'], 5)
        owned = {p for m in plan['modules'] for p in m['writes']}
        self.assertEqual(owned, {p for p in self.result['source_sha256'] if p.startswith('app/')})

    def test_red_and_green_receipts_have_complete_non_skipped_tests(self):
        self.assertEqual(self.result['status'], 'PASSED')
        for variant in self.result['variants']:
            self.assertEqual(set(variant['test_names']), self.runner['TESTS'])
            self.assertEqual(variant['tests'], len(self.runner['TESTS']))
            self.assertEqual(variant['errors'], [])
            self.assertEqual(variant['skipped'], [])
            self.assertTrue(variant['accepted'])
            wanted = self.runner['RED_FAILURES'] if variant['variant'] == 'red' else set()
            self.assertEqual(set(variant['failures']), wanted)
            self.assertEqual(variant['process_exit'], 1 if wanted else 0)

    def test_compiled_variants_match_their_respective_actual_bytes(self):
        service = self.runner['SERVICE']
        for variant in self.result['variants']:
            for name, digest in variant['compiled_source_sha256'].items():
                path = CASE / ('fixtures/ReadingListService-red.java.txt' if variant['variant'] == 'red' and name == service else 'app/' + name)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

    def test_independent_acceptance_matches_the_same_candidate_and_actual_run(self):
        review = json.loads((CASE / 'implementation-review.json').read_text())
        self.assertEqual(review['candidate_id'], self.result['candidate_id'])
        self.assertEqual(review['verdict'], 'IMPLEMENTATION_ACCEPTED_WITHIN_SCOPE')
        self.assertEqual(review['findings'], [])
        self.assertEqual(review['independent_run']['status'], 'PASSED')
        self.assertEqual(review['independent_run']['green_tests'], len(self.runner['TESTS']))


if __name__ == '__main__':
    unittest.main()
