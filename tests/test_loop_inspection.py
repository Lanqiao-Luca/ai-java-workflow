"""Synthetic source callbacks; no live logs, APIs, build or scheduler."""
from copy import deepcopy
from pathlib import Path
import hashlib
import runpy
import unittest

from tools.inspection_loop import inspect


def plan():
    return {'scope_id': 'synthetic-inspection', 'context': {'candidate_id': 'a' * 64,
            'requirements_id': 'b' * 64, 'rules_id': 'c' * 64},
            'requirements': [{'id': key, 'source': key, 'kind': key} for key in ['log', 'api', 'build']],
            'authorized_sources': ['log', 'api', 'build'], 'max_rounds': 3,
            'budget_seconds': 30, 'deadline': 130, 'not_before': 90}


def report(requirement, *, status='OBSERVED', step=None, sha='d' * 64, finding=None):
    return {'requirement_id': requirement['id'], 'source': requirement['source'], 'kind': requirement['kind'],
            'context': plan()['context'], 'status': status, 'evidence_id': 'synthetic-' + requirement['id'],
            'artifact_sha256': sha, 'observed_at': 100, 'finding': finding, 'next_step': step}


class InspectionTests(unittest.TestCase):
    def run_plan(self, p=None, collector=None, clock=lambda: 100):
        return inspect(p or plan(), collector or (lambda r, step, seconds: report(r)), clock=clock)

    def test_complete_evidence_can_contain_anomaly(self):
        result = self.run_plan(collector=lambda r, step, seconds: report(r, finding='Synthetic error observed'))
        self.assertEqual(result['status'], 'CONVERGED')
        self.assertEqual(len(result['findings']), 3)
        self.assertEqual(result['missing'], [])

    def test_distinct_followup_fills_gap_without_repeating_covered_sources(self):
        calls = []
        def collect(r, step, seconds):
            calls.append((r['id'], step))
            return report(r, status='MISSING', step='read-tail') if r['id'] == 'log' and step == 'initial' else report(r, sha='e' * 64)
        result = self.run_plan(collector=collect)
        self.assertEqual(result['status'], 'CONVERGED')
        self.assertEqual(result['rounds_used'], 2)
        self.assertEqual(calls.count(('api', 'initial')), 1)

    def test_denied_source_retains_scope_and_independent_work_continues(self):
        p = plan(); p['authorized_sources'].remove('api')
        calls = []
        result = self.run_plan(p, lambda r, step, seconds: (calls.append(r['id']) or report(r)))
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['missing'], ['api'])
        self.assertEqual(len(result['required']), 3)
        self.assertEqual(calls, ['log', 'build'])

    def test_unknown_and_future_observation_do_not_poll(self):
        for status in ['UNKNOWN', 'FUTURE', 'CHANGE_REQUIRED', 'DENIED']:
            with self.subTest(status=status):
                result = self.run_plan(collector=lambda r, step, seconds: report(r, status=status, step='again'))
                self.assertEqual(result['status'], 'PARTIAL')
                self.assertEqual(len(result['observations']), 3)

    def test_same_bytes_under_new_handle_are_not_information_gain(self):
        def collect(r, step, seconds):
            data = report(r, status='MISSING', step=step + '-next')
            data['evidence_id'] += step
            return data
        result = self.run_plan(collector=collect)
        self.assertEqual(result['rounds_used'], 2)
        self.assertEqual(set(result['reasons'].values()), {'NO_INFORMATION_GAIN'})

    def test_failure_is_not_zero_results_and_does_not_stop_other_sources(self):
        def collect(r, step, seconds):
            if r['id'] == 'api':
                raise OSError('synthetic unavailable')
            return report(r)
        result = self.run_plan(collector=collect)
        self.assertEqual(result['covered'], ['build', 'log'])
        self.assertEqual(result['reasons']['api'], 'UNKNOWN_OR_INVALID_REPORT')

    def test_stale_or_wrong_context_and_source_do_not_cover_scope(self):
        for change in [{'source': 'different'}, {'observed_at': 89}, {'observed_at': 101}, {'context': {**plan()['context'], 'candidate_id': 'f' * 64}}]:
            with self.subTest(change=change):
                result = self.run_plan(collector=lambda r, step, seconds: {**report(r), **change})
                self.assertEqual(result['status'], 'PARTIAL')
                self.assertEqual(result['covered'], [])

    def test_round_limit_keeps_original_missing_set(self):
        p = plan(); p['max_rounds'] = 1
        result = self.run_plan(p, lambda r, step, seconds: report(r, status='MISSING', step='followup'))
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['rounds_used'], 1)
        self.assertEqual(set(result['reasons'].values()), {'ROUND_LIMIT'})

    def test_late_result_is_retained_but_cannot_cover(self):
        ticks = [100]
        def collect(r, step, seconds):
            ticks[0] = 131
            return report(r)
        result = self.run_plan(collector=collect, clock=lambda: ticks[0])
        self.assertEqual(result['covered'], [])
        self.assertEqual(len(result['observations']), 1)
        self.assertEqual(result['reasons']['log'], 'LATE_EVIDENCE')

    def test_callback_cannot_modify_original_scope(self):
        p = plan(); original = deepcopy(p)
        def collect(r, step, seconds):
            result = report(r)
            r['id'] = 'changed'
            p['requirements'].clear()
            return result
        result = self.run_plan(p, collect)
        self.assertEqual(result['required'], [r['id'] for r in original['requirements']])
        self.assertEqual(result['status'], 'CONVERGED')

    def test_expired_budget_starts_no_collection(self):
        p = plan(); p['deadline'] = 100
        result = self.run_plan(p, collector=lambda *args: self.fail('must not collect'))
        self.assertEqual(result['rounds_used'], 0)
        self.assertEqual(result['status'], 'PARTIAL')

    def test_invalid_budget_or_duplicate_scope_rejected(self):
        for changes in [{'max_rounds': True}, {'budget_seconds': float('nan')}, {'requirements': []},
                        {'requirements': [plan()['requirements'][0]] * 2}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_plan({**plan(), **changes})

    def test_actual_fixture_reads_supplement_and_partial(self):
        root = Path(__file__).resolve().parents[1]
        run = runpy.run_path(str(root / 'loops/examples/inspection/run.py'))['run_examples']
        result = run()
        complete, partial = result['supplement'], result['partial']
        self.assertEqual(complete['status'], 'CONVERGED')
        self.assertEqual(complete['rounds_used'], 2)
        self.assertEqual(len(complete['observations']), 4)
        self.assertEqual(len(complete['findings']), 2)
        self.assertEqual(partial['status'], 'PARTIAL')
        self.assertEqual(partial['missing'], ['api-response', 'build-report'])
        self.assertFalse(any(r.get('source') == 'api' for r in partial['observations']))
        expected = hashlib.sha256((root / 'loops/examples/inspection/service-tail.log').read_bytes()).hexdigest()
        self.assertEqual(complete['observations'][-1]['artifact_sha256'], expected)

    def test_malformed_optional_evidence_becomes_unknown_without_replay(self):
        result = self.run_plan(collector=lambda r, step, seconds: {
            **report(r, status='UNKNOWN'), 'artifact_sha256': {'invalid': True}})
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(len(result['observations']), 3)


if __name__ == '__main__':
    unittest.main()
