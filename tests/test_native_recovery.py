"""Controlled native outcomes with real private Git worktrees; no model or Maven."""
from pathlib import Path
from unittest.mock import patch
import fcntl
import json
import tempfile
import unittest

from test_native_flow import make_catalog
from tools.native_agents import NativeRejected, native_completion
from test_native_agents import fixture
from tools.native_flow import FlowRejected, NativeFlow, candidate, digest
from tools.native_recovery import RecoveryRunner


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.catalog = self.root / 'catalog'
        stages = [
            ('requirements', [], ['requirements.md'], False, False),
            ('implementation', ['requirements'], ['app/src/main/Code.java', 'app/src/test/Author.java', 'implementation.md'], False, False),
            ('verification', ['implementation'], ['app/src/test/Independent.java', 'verification.md'], False, True),
            ('code_review', ['verification'], ['code-review.md'], True, False),
            ('principle_review', ['verification'], ['principle-review.md'], True, False),
            ('delivery', ['code_review', 'principle_review'], ['delivery.md'], True, False),
        ]
        self.definition = make_catalog(self.catalog, stages)
        self.seed = {'task.md': b'Independent controlled task; not model evidence.',
                     'app/pom.xml': b'<project/>', 'app/src/test/Fixed.java': b'fixed contract'}
        self.calls = []
        self.mode = 'pass'

    def flow(self, resume=False):
        return NativeFlow(self.seed, self.catalog, self.definition, self.root / 'private',
                          validate=self.validate, resume=resume)

    def validate(self, workspace, node, workflow):
        mapping = candidate(workspace)
        failed = self.mode in {'verification', 'no_progress', 'always_fail'} and (workspace / 'app/src/main/Code.java').read_text() != 'fixed'
        return {'status': 'FAILED' if failed else 'PASSED', 'source_sha256': mapping,
                'candidate_id': digest(mapping), 'process_exit': 1 if failed else 0,
                'category': 'junit_or_source_mismatch' if failed else 'passed',
                'tests': 1, 'failures': ['synthetic#assertion'] if failed else []}

    def dispatch(self, workspace, role, task, private, **kwargs):
        ident = role.removeprefix('workflow_')
        repair = 'Fix the concrete failures' in task
        self.calls.append((ident, repair))
        if self.mode == 'unknown' and ident == 'verification':
            raise NativeRejected('controlled unconfirmed timeout')
        writes = json.loads(task.split('Allowed and required outputs exactly: ', 1)[1].split('. Do not edit', 1)[0])
        for name in writes:
            output = workspace / name
            output.parent.mkdir(parents=True, exist_ok=True)
            content = 'Controlled document.'
            if name.startswith('app/src/main/'):
                content = 'fixed' if repair and self.mode not in {'no_progress', 'always_fail'} else 'bad'
                if repair and self.mode == 'always_fail':
                    content = 'bad-' + str(len(self.calls))
            elif name.startswith('app/src/test/'):
                content = 'frozen independent regression' if 'Independent' in name else 'frozen author test'
            output.write_text(content)
        if ident in {'verification', 'code_review', 'principle_review', 'delivery'}:
            for name in writes:
                if name.endswith('.md'):
                    (workspace / name).write_text('candidate_id: ' + digest(candidate(workspace)) + '\nConcrete controlled finding or bounded approval.')
        if self.mode == 'mutate_test' and repair:
            (workspace / 'app/src/test/Fixed.java').write_text('weakened')
        if self.mode == 'stale_review' and ident == 'code_review':
            (workspace / 'code-review.md').write_text('candidate_id: stale\nFinding.')
        bad_code = (workspace / 'app/src/main/Code.java').exists() and (workspace / 'app/src/main/Code.java').read_text() == 'bad'
        failed = ((ident == 'verification' and self.mode in {'verification', 'no_progress', 'always_fail', 'mutate_test'} and bad_code)
                  or ident == 'code_review' and self.mode in {'review', 'stale_review'} and bad_code)
        return {'status': 'FAILED' if failed else 'SUCCEEDED', 'native_completed': True,
                'result': {'status': 'failed' if failed else 'passed', 'summary': 'Concrete synthetic failure' if failed else 'Controlled success',
                           'outputs': writes}}

    def run_flow(self, flow=None, **options):
        flow = flow or self.flow()
        with patch('tools.native_flow.dispatch', side_effect=self.dispatch):
            return RecoveryRunner(flow, **options).run()

    def test_successful_first_round(self):
        result = self.run_flow()
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(result['attempts'], 6)
        self.assertEqual(result['round'], 1)

    def test_failed_verification_repairs_and_reruns_frozen_tests_and_reviews(self):
        self.mode = 'verification'
        flow = self.flow()
        result = self.run_flow(flow)
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(result['round'], 2)
        self.assertEqual(self.calls.count(('requirements', False)), 1)
        self.assertEqual(self.calls.count(('verification', False)), 2)
        self.assertIn(('implementation', True), self.calls)
        self.assertEqual((flow.source / 'app/src/test/Independent.java').read_text(), 'frozen independent regression')
        self.assertEqual((flow.source / 'app/src/test/Fixed.java').read_bytes(), self.seed['app/src/test/Fixed.java'])
        self.assertEqual(result['stages']['verification']['candidate_id'], result['candidate_id'])
        self.assertTrue((flow.root / 'instances/attempt-3-verification/verification.md').exists())
        for ident in ['code_review', 'principle_review', 'delivery']:
            self.assertEqual(result['stages'][ident]['candidate_id'], result['candidate_id'])

    def test_review_finding_invalidates_both_reviews_and_validation(self):
        self.mode = 'review'
        result = self.run_flow()
        self.assertEqual(result['status'], 'SUCCEEDED')
        for ident in ('verification', 'code_review', 'principle_review'):
            self.assertEqual(self.calls.count((ident, False)), 2)
        self.assertEqual(self.calls.count(('delivery', False)), 1)
        self.assertEqual(len([h for h in result['history'] if h['stage'] == 'code_review' and h['status'] == 'FAILED']), 1)

    def test_round_limit_includes_initial_attempt(self):
        self.mode = 'verification'
        result = self.run_flow(max_rounds=1)
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertNotIn(('implementation', True), self.calls)
        self.assertNotIn(('delivery', False), self.calls)

    def test_nonprogressing_repair_stops_without_delivery(self):
        self.mode = 'no_progress'
        result = self.run_flow()
        self.assertEqual(result['status'], 'NO_PROGRESS')
        self.assertEqual(self.calls.count(('implementation', True)), 1)
        self.assertNotIn(('delivery', False), self.calls)

    def test_changing_but_still_failing_repairs_exhaust_shared_round_budget(self):
        self.mode = 'always_fail'
        result = self.run_flow(max_rounds=2)
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertEqual(result['round'], 2)
        self.assertEqual(self.calls.count(('implementation', True)), 1)
        self.assertNotIn(('delivery', False), self.calls)

    def test_timeout_or_drifted_host_report_cannot_trigger_repair(self):
        self.mode = 'verification'
        original = self.validate
        for change in ({'category': 'build_timeout'}, {'candidate_id': 'stale'}, {'process_exit': 0}):
            with self.subTest(change=change):
                # Each trial owns a different new run; no rejected call is replayed.
                flow = NativeFlow(self.seed, self.catalog, self.definition,
                    self.root / ('trial-' + next(iter(change))),
                    validate=lambda *args: {**original(*args), **change})
                count = len(self.calls)
                result = self.run_flow(flow)
                self.assertEqual(result['status'], 'FAILED')
                self.assertNotIn(('implementation', True), self.calls[count:])

    def test_clock_rollback_rejects_resume(self):
        first = self.run_flow(pause_after='implementation')
        with patch('tools.native_recovery.time.time', return_value=first['started_at'] - 1):
            with self.assertRaises(FlowRejected):
                self.run_flow(self.flow(resume=True))

    def test_unknown_native_result_is_never_retried_or_resumed(self):
        self.mode = 'unknown'
        result = self.run_flow()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(self.calls.count(('verification', False)), 1)
        with self.assertRaises(FlowRejected):
            self.run_flow(self.flow(resume=True))

    def test_repair_cannot_weaken_existing_tests(self):
        self.mode = 'mutate_test'
        result = self.run_flow()
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn(('delivery', False), self.calls)

    def test_failed_review_with_stale_identity_cannot_trigger_repair(self):
        self.mode = 'stale_review'
        result = self.run_flow()
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn(('implementation', True), self.calls)

    def test_resume_skips_accepted_prefix_and_preserves_budget_and_history(self):
        first = self.run_flow(pause_after='implementation')
        self.assertEqual(first['status'], 'PAUSED')
        second = self.run_flow(self.flow(resume=True))
        self.assertEqual(second['status'], 'SUCCEEDED')
        self.assertEqual(second['deadline'], first['deadline'])
        self.assertEqual(second['attempts'], 6)
        self.assertEqual(self.calls.count(('implementation', False)), 1)
        self.assertEqual(len(second['history']), 6)

    def test_resume_after_round_two_preserves_frozen_independent_test(self):
        self.mode = 'verification'
        first = self.run_flow(pause_after='verification')
        self.assertEqual(first['status'], 'PAUSED')
        self.assertEqual(first['round'], 2)
        second = self.run_flow(self.flow(resume=True))
        self.assertEqual(second['status'], 'SUCCEEDED')
        self.assertEqual(second['round'], 2)
        self.assertEqual(self.calls.count(('requirements', False)), 1)

    def test_checkpoint_source_drift_is_rejected(self):
        self.run_flow(pause_after='implementation')
        (self.root / 'private/source/app/src/main/Code.java').write_text('drift')
        with self.assertRaises(FlowRejected):
            self.run_flow(self.flow(resume=True))

    def test_resume_cannot_renew_policy_or_execution_context(self):
        self.run_flow(pause_after='implementation')
        for options in ({'max_rounds': 4}, {'budget_seconds': 4000}, {'context_id': 'new tools'}):
            with self.assertRaises(FlowRejected):
                self.run_flow(self.flow(resume=True), **options)

    def test_expired_resume_dispatches_nothing(self):
        first = self.run_flow(pause_after='implementation')
        count = len(self.calls)
        with patch('tools.native_recovery.time.time', return_value=first['deadline'] + 1):
            result = self.run_flow(self.flow(resume=True))
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertEqual(len(self.calls), count)

    def test_inflight_checkpoint_cannot_replay(self):
        self.run_flow(pause_after='implementation')
        path = self.root / 'private/state.json'
        data = json.loads(path.read_text())
        data['status'] = 'RUNNING'
        path.write_text(json.dumps(data))
        with self.assertRaises(FlowRejected):
            self.run_flow(self.flow(resume=True))

    def test_concurrent_controller_is_rejected(self):
        self.run_flow(pause_after='implementation')
        with (self.root / 'private/controller.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(FlowRejected):
                self.run_flow(self.flow(resume=True))

    def test_resume_rejects_changed_catalog(self):
        self.run_flow(pause_after='implementation')
        (self.catalog / 'agents/example.md').write_text('different methods')
        with self.assertRaises(FlowRejected):
            self.run_flow(self.flow(resume=True))

    def test_invalid_policy_rejected_before_run(self):
        for options in ({'max_rounds': 0}, {'max_rounds': True}, {'budget_seconds': 0}, {'max_rounds': 6}):
            with self.assertRaises(FlowRejected):
                RecoveryRunner(self.flow(), **options)


class ConfirmedNativeFailureTests(unittest.TestCase):
    def test_opt_in_accepts_only_actual_confirmed_failure(self):
        data = fixture()
        output = json.loads(data[3]['payload']['output'])
        result = json.loads(output['agents'][0]['agent_status']['completed'])
        result['status'] = 'failed'
        output['agents'][0]['agent_status']['completed'] = json.dumps(result)
        data[3]['payload']['output'] = json.dumps(output)
        receipt = native_completion(data, 'workflow_probe', accept_failed=True)
        self.assertTrue(receipt['native_completed'])
        self.assertEqual(receipt['result']['status'], 'failed')
        with self.assertRaises(NativeRejected):
            native_completion(data, 'workflow_probe')
        with self.assertRaises(NativeRejected):
            native_completion(data[:-1], 'workflow_probe', accept_failed=True)


if __name__ == '__main__':
    unittest.main()
