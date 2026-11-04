"""Real Graph -> Loop -> local fixture adapters -> Gate -> closure, no model/service."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest

from tools import goal_graph_loops as adapters
from tools.goal_graph import GoalGraphRejected
from tools.goal_graph_run import GoalGraphRun

ROOT = Path(__file__).resolve().parents[1]


class LoopGraphTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def run_case(self, scenario='complete', *, case_root=adapters.CASE, pause_after=None, resume=False, label='run'):
        fixture = adapters.fixture_graph(scenario, case_root=case_root)
        state = GoalGraphRun(fixture.definition, fixture.handlers, fixture.context, self.root / label,
                             budget_seconds=20, pause_after=pause_after, resume=resume).run()
        return fixture, state

    def test_actual_loop_calls_and_current_gate_products_close_all_goals(self):
        with patch.object(adapters, 'inspect', wraps=adapters.inspect) as inspection, \
             patch.object(adapters, 'run_defect', wraps=adapters.run_defect) as defect:
            fixture, state = self.run_case()
        self.assertEqual(inspection.call_count, 1)
        self.assertEqual(defect.call_count, 1)
        self.assertEqual(state['status'], 'SUCCEEDED')
        self.assertEqual(state['attempts'], 5)
        self.assertEqual(state['nodes']['inspection']['result']['rounds_used'], 2)
        self.assertEqual(state['nodes']['defect']['result']['rounds_used'], 2)
        self.assertEqual(len(state['nodes']['inspection']['result']['adapter_calls']), 4)
        self.assertEqual(set(state['nodes']['close']['result']['targets']),
                         {'inspection', 'defect', 'review-inspection', 'review-defect'})
        for ident in ('inspection', 'defect'):
            record = state['nodes'][ident]
            path = self.root / 'run' / record['workspace'] / record['payload_path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['products'][record['payload_path']]['sha256'])
            self.assertEqual(json.loads(path.read_text()), record['result'])
            self.assertTrue(record['result']['synthetic'])
        self.assertEqual(fixture.context['candidate_id'], hashlib.sha256((adapters.CASE / 'candidate.json').read_bytes()).hexdigest())

    def test_partial_keeps_full_scope_while_independent_defect_finishes(self):
        fixture, state = self.run_case('partial')
        self.assertEqual(state['status'], 'PARTIAL')
        self.assertEqual(state['nodes']['inspection']['status'], 'PARTIAL')
        self.assertEqual(state['nodes']['inspection']['result']['missing'], ['api-response', 'build-report'])
        self.assertEqual(len(state['goals']['inspection']['required']), 3)
        self.assertEqual(state['nodes']['review-inspection']['status'], 'BLOCKED')
        self.assertEqual(state['nodes']['defect']['status'], 'SUCCEEDED')
        self.assertEqual(state['nodes']['review-defect']['status'], 'SUCCEEDED')
        self.assertEqual(state['nodes']['close']['status'], 'BLOCKED')
        self.assertNotIn('api-response.json', fixture.read_files)
        self.assertNotIn('build-report.json', fixture.read_files)

    def test_denied_or_future_sources_are_not_eagerly_opened(self):
        original = Path.read_bytes
        def read(path):
            if path.parent == adapters.CASE and path.name in {'api-response.json', 'build-report.json'}:
                self.fail('unadmitted/future fixture must not be read')
            return original(path)
        with patch.object(Path, 'read_bytes', read):
            _, state = self.run_case('partial')
        self.assertEqual(state['status'], 'PARTIAL')

    def test_unknown_effect_keeps_required_operation_and_never_retries_loop(self):
        _, state = self.run_case('unknown-effect')
        self.assertEqual(state['status'], 'UNKNOWN')
        result = state['nodes']['defect']['result']
        self.assertEqual(result['status'], 'HOLD')
        self.assertEqual(result['rounds_used'], 1)
        self.assertEqual(result['required_operations'], ['demo-effect'])
        self.assertEqual(state['goals']['defect']['required_operations'], ['demo-effect'])
        self.assertEqual(state['attempts'], 2)
        self.assertNotEqual(state['nodes']['close']['status'], 'SUCCEEDED')
        with self.assertRaises(GoalGraphRejected):
            self.run_case('unknown-effect', resume=True)

    def test_pause_resume_reuses_both_completed_loops_and_original_deadline(self):
        with patch.object(adapters, 'inspect', wraps=adapters.inspect) as inspection, \
             patch.object(adapters, 'run_defect', wraps=adapters.run_defect) as defect:
            _, first = self.run_case(pause_after='inspection')
            self.assertEqual(first['status'], 'PAUSED')
            _, second = self.run_case(resume=True)
        self.assertEqual(second['status'], 'SUCCEEDED')
        self.assertEqual(second['deadline'], first['deadline'])
        self.assertEqual(second['run_id'], first['run_id'])
        self.assertEqual(inspection.call_count, 1)
        self.assertEqual(defect.call_count, 1)

    def test_changed_fixture_identity_rejects_resume(self):
        _, state = self.run_case(pause_after='inspection')
        copied = self.root / 'changed-inputs'; shutil.copytree(adapters.CASE, copied)
        path = copied / 'defect-evidence.json'; data = json.loads(path.read_text())
        data['handoff']['recipient'] = 'another-recipient'; path.write_text(json.dumps(data))
        with self.assertRaises(GoalGraphRejected):
            self.run_case(case_root=copied, resume=True)
        saved = json.loads((self.root / 'run/state.json').read_text())
        self.assertEqual(saved['attempts'], state['attempts'])

    def test_passing_tests_with_wrong_business_behavior_cannot_close_graph(self):
        copied = self.root / 'wrong-behavior'; shutil.copytree(adapters.CASE, copied)
        path = copied / 'defect-evidence.json'; data = json.loads(path.read_text())
        data['behavior']['normalized'] = ['wrong']; path.write_text(json.dumps(data))
        _, state = self.run_case(case_root=copied)
        self.assertEqual(state['status'], 'PARTIAL')
        self.assertEqual(state['nodes']['defect']['result']['missing_criteria'], ['behavior'])
        self.assertEqual(state['nodes']['inspection']['status'], 'SUCCEEDED')
        self.assertNotEqual(state['nodes']['close']['status'], 'SUCCEEDED')

    def test_original_issue_is_not_closed_when_fixture_still_violates_it(self):
        copied = self.root / 'still-broken'; shutil.copytree(adapters.CASE, copied)
        path = copied / 'defect-evidence.json'; data = json.loads(path.read_text())
        data['behavior']['invalid_input_status'] = 200; path.write_text(json.dumps(data))
        _, state = self.run_case(case_root=copied)
        self.assertEqual(state['status'], 'PARTIAL')
        findings = state['nodes']['defect']['result']['finding_ledger']['findings']
        self.assertTrue(all(f['status'] == 'OPEN' for f in findings.values()))

    def test_malformed_scenario_cannot_silently_broaden_read_policy(self):
        copied = self.root / 'invalid-policy'; shutil.copytree(adapters.CASE, copied)
        path = copied / 'scenarios.json'; data = json.loads(path.read_text())
        data['cases']['complete']['unknown_effect'] = 'false'; path.write_text(json.dumps(data))
        with self.assertRaises(GoalGraphRejected):
            adapters.fixture_graph(case_root=copied)

    def test_frontend_exit_codes_and_cross_process_checkpoint_resume(self):
        command = [sys.executable, '-B', str(ROOT / 'scripts/run_goal_graph.py')]
        def run(*args):
            return subprocess.run(command + list(args), capture_output=True, text=True, timeout=20)
        root = str(self.root / 'cli')
        paused = run('--run-root', root, '--pause-after', 'inspection')
        self.assertEqual(paused.returncode, 3, paused.stdout + paused.stderr)
        renewed = run('--run-root', root, '--resume', '--budget-seconds', '30')
        self.assertEqual(renewed.returncode, 2)
        resumed = run('--run-root', root, '--resume')
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)['status'], 'SUCCEEDED')
        partial = run('--run-root', str(self.root / 'cli-partial'), '--scenario', 'partial')
        self.assertEqual(partial.returncode, 1, partial.stdout + partial.stderr)
        self.assertEqual(json.loads(partial.stdout)['status'], 'PARTIAL')
        rejected = run('--run-root', str(ROOT))
        self.assertEqual(rejected.returncode, 2)

    def test_aggregate_example_preserves_negative_graph_outcomes(self):
        examples = runpy.run_path(str(ROOT / 'graphs/examples/goal-loops/run.py'))['run_examples']()
        self.assertEqual({name: state['status'] for name, state in examples.items()},
                         {'complete': 'SUCCEEDED', 'partial': 'PARTIAL', 'unknown-effect': 'UNKNOWN'})


if __name__ == '__main__':
    unittest.main()
