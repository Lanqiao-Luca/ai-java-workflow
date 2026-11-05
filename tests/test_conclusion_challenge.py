"""Meaningful negative controls for report identity and false completion claims."""
from copy import deepcopy
from pathlib import Path
import json
import runpy
import unittest
from tools.conclusion_challenge import ChallengeError, check

CASE = Path(__file__).resolve().parents[1] / 'workflows/examples/conclusion-challenge'


class ConclusionChallengeTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((CASE / 'review.json').read_text())
        self.runner = runpy.run_path(str(CASE / 'run.py'))
        self.digest = self.runner['candidate_sha256']()

    def check(self):
        return check(self.report, self.digest)

    def test_actual_counterexample_retains_store_write_and_exposes_stale_cache(self):
        result = self.runner['run_case']()
        observed = result['observed']
        self.assertEqual(observed['stored_after_write'], observed['after_clear'])
        self.assertNotEqual(observed['stored_after_write'], observed['cached_after_write'])
        self.assertEqual(result['independent_review'], 'NOT_RUN')
        self.assertEqual(result['source_requests'], 0)

    def test_valid_structure_never_accepts_meaning_or_authorizes_action(self):
        result = self.check()
        self.assertEqual(result['status'], 'STRUCTURE_VALID')
        self.assertEqual(result['semantic_acceptance'], 'NOT_ASSESSED')
        self.assertEqual(result['action_authorization'], 'NOT_ASSESSED')

    def test_candidate_drift_rejected(self):
        self.report['candidate_sha256'] = '0' * 64
        with self.assertRaisesRegex(ChallengeError, 'candidate drift'):
            self.check()

    def test_missing_matrix_cell_rejected(self):
        self.report['matrix'].pop()
        with self.assertRaisesRegex(ChallengeError, 'incomplete matrix'):
            self.check()

    def test_duplicate_matrix_cell_cannot_replace_missing_pair(self):
        self.report['matrix'][-1] = deepcopy(self.report['matrix'][0])
        with self.assertRaisesRegex(ChallengeError, 'duplicate matrix'):
            self.check()

    def test_unknown_evidence_reference_rejected(self):
        self.report['matrix'][0]['evidence'] = 'not-found'
        with self.assertRaises(ChallengeError):
            self.check()

    def test_missing_sensitivity_rejected(self):
        self.report['sensitivity'].pop()
        with self.assertRaisesRegex(ChallengeError, 'missing critical'):
            self.check()

    def test_completed_probe_requires_observation_reference(self):
        self.report['probes'][0]['evidence'] = []
        with self.assertRaises(ChallengeError):
            self.check()

    def test_not_run_preserves_pending_and_cannot_claim_evidence(self):
        probe = self.report['probes'][0]
        probe.update(state='NOT_RUN', evidence=[], result='No run; permission unavailable.')
        self.assertEqual(self.check()['pending_checks'], ['P-store'])
        probe['evidence'] = ['E-runtime']
        with self.assertRaisesRegex(ChallengeError, 'unexecuted'):
            self.check()

    def test_unavailable_is_not_completed(self):
        self.report['probes'][0].update(state='UNAVAILABLE', evidence=[], result='Source unavailable.')
        self.assertEqual(self.check()['pending_checks'], ['P-store'])

    def test_initial_preferred_must_be_challenged(self):
        self.report['probes'][0]['hypothesis'] = 'H-cache'
        with self.assertRaisesRegex(ChallengeError, 'unchallenged'):
            self.check()

    def test_correlated_observations_do_not_become_independent_chains(self):
        for evidence in self.report['evidence']:
            evidence['source_group'] = 'one-source'
        self.assertEqual(self.check()['declared_source_groups'], 1)
        self.assertEqual(self.check()['semantic_acceptance'], 'NOT_ASSESSED')

    def test_unsupported_strength_cannot_become_numeric_confidence(self):
        self.report['matrix'][0]['effect'] = '99%'
        with self.assertRaises(ChallengeError):
            self.check()

    def test_duplicate_hypothesis_not_a_competing_explanation(self):
        self.report['hypotheses'][1]['explanation'] = self.report['hypotheses'][0]['explanation']
        with self.assertRaisesRegex(ChallengeError, 'duplicate explanation'):
            self.check()

    def test_blank_limits_and_implicit_critical_flags_rejected(self):
        for key, value in (('limits', ''), ('critical', 1)):
            with self.subTest(key=key):
                original = self.report['evidence'][0][key]
                self.report['evidence'][0][key] = value
                with self.assertRaises(ChallengeError):
                    self.check()
                self.report['evidence'][0][key] = original

    def test_malformed_inputs_fail_as_contract_errors(self):
        for value in (None, [], {}, 'report'):
            with self.subTest(value=value), self.assertRaises(ChallengeError):
                check(value, self.digest)
        with self.assertRaises(ChallengeError):
            check(self.report, 'not-a-digest')


if __name__ == '__main__':
    unittest.main()
