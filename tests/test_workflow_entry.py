"""Real process checkpoints and negative controls for the bounded public CLI."""
from pathlib import Path
from unittest.mock import patch
import json
import subprocess
import sys
import tempfile
import unittest
from tools import workflow_entry as entry
ROOT = Path(__file__).resolve().parents[1]


class WorkflowEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.request = self.root / 'request.json'
        self.request.write_text(json.dumps({'job': 'conclusion-challenge', 'options': {}}))
        self.run_root = self.root / 'instance'

    def command(self, *arguments):
        process = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/workflow.py'), *map(str, arguments)],
                                 cwd=self.root, text=True, capture_output=True, timeout=30)
        return process.returncode, json.loads(process.stdout)

    def paused(self):
        return entry.run(self.request, self.run_root, pause=True)

    def alter_state(self, **changes):
        path = self.run_root / 'state.json'
        value = json.loads(path.read_text())
        value.update(changes)
        path.write_text(json.dumps(value))

    def test_real_cross_process_pause_resume_and_idempotent_completed_read(self):
        code, paused = self.command('run', '--request', self.request, '--run-root', self.run_root, '--pause-after-preflight')
        self.assertEqual((code, paused['status']), (0, 'READY'))
        code, done = self.command('resume', '--request', self.request, '--run-root', self.run_root)
        self.assertEqual((code, done['status']), (0, 'SUCCEEDED'))
        self.assertEqual(done['run_id'], paused['run_id'])
        self.assertEqual(done['steps'], ['preflight', 'execute'])
        before = (self.run_root / 'state.json').read_bytes()
        self.assertEqual(self.command('resume', '--request', self.request, '--run-root', self.run_root)[1], done)
        self.assertEqual((self.run_root / 'state.json').read_bytes(), before)

    def test_doctor_and_choose_are_explicit_routing_without_execution(self):
        self.assertEqual(self.command('doctor')[1]['status'], 'READY')
        result = self.command('choose', '--goal', 'challenge')[1]
        self.assertEqual(result['entry'], 'workflows/conclusion-challenge.md')
        self.assertEqual(result['kind'], 'explicit_goal_mapping')
        self.assertFalse(self.run_root.exists())

    def test_changed_request_bytes_reject_resume_even_if_json_meaning_same(self):
        self.paused()
        self.request.write_text(self.request.read_text() + '\n')
        with self.assertRaisesRegex(entry.EntryError, 'drift'):
            entry.resume(self.request, self.run_root)

    def test_changed_implementation_identity_rejects_resume(self):
        self.paused()
        self.alter_state(fingerprint='0' * 64)
        with patch.object(entry, 'execute') as action, self.assertRaisesRegex(entry.EntryError, 'drift'):
            entry.resume(self.request, self.run_root)
        action.assert_not_called()

    def test_unknown_and_running_never_replay(self):
        self.paused()
        for status in ('UNKNOWN', 'RUNNING'):
            with self.subTest(status=status):
                self.alter_state(status=status)
                with patch.object(entry, 'execute') as action:
                    result = entry.resume(self.request, self.run_root)
                self.assertEqual(result['status'], 'UNKNOWN')
                action.assert_not_called()

    def test_failed_run_is_returned_without_automatic_retry(self):
        self.paused()
        self.alter_state(status='FAILED')
        with patch.object(entry, 'execute') as action:
            self.assertEqual(entry.resume(self.request, self.run_root)['status'], 'FAILED')
        action.assert_not_called()

    def test_existing_writer_lock_is_not_stolen(self):
        self.paused()
        lock = self.run_root / 'writer.lock'
        lock.write_text('existing owner')
        with self.assertRaisesRegex(entry.EntryError, 'writer present'):
            entry.resume(self.request, self.run_root)
        self.assertEqual(lock.read_text(), 'existing owner')

    def test_existing_instance_not_overwritten(self):
        self.paused()
        before = (self.run_root / 'state.json').read_bytes()
        with self.assertRaises(FileExistsError):
            entry.run(self.request, self.run_root)
        self.assertEqual((self.run_root / 'state.json').read_bytes(), before)

    def test_runtime_inside_repository_rejected_before_creation(self):
        target = ROOT / 'runtime-should-not-exist'
        with self.assertRaises(entry.EntryError):
            entry.run(self.request, target)
        self.assertFalse(target.exists())

    def test_unavailable_spring_tools_reject_before_run_creation(self):
        self.request.write_text(json.dumps({'job': 'spring-archive', 'options': {'java_home': str(self.root / 'jdk'),
            'maven_home': str(self.root / 'maven'), 'repository': str(self.root / 'deps'), 'offline': True}}))
        self.assertEqual(entry.doctor(entry.request(self.request))['status'], 'NOT_READY')
        with self.assertRaisesRegex(entry.EntryError, 'environment'):
            entry.run(self.request, self.run_root)
        self.assertFalse(self.run_root.exists())

    def test_arbitrary_job_or_shell_options_not_accepted(self):
        for value in ({'job': 'shell', 'options': {}}, {'job': 'conclusion-challenge', 'options': {'command': 'echo unsafe'}}):
            self.request.write_text(json.dumps(value))
            with self.assertRaises(entry.EntryError):
                entry.run(self.request, self.run_root)
        self.assertFalse(self.run_root.exists())

    def test_exception_after_start_persists_unknown(self):
        self.paused()
        with patch.object(entry, 'execute', side_effect=RuntimeError('simulated interruption')):
            result = entry.resume(self.request, self.run_root)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['failure_category'], 'RuntimeError')
        self.assertEqual(entry.status(self.run_root)['status'], 'UNKNOWN')

    def test_real_cli_fault_after_side_effect_reports_unknown_exit_one(self):
        script = ROOT / 'scripts/workflow.py'
        marker = self.root / 'marker'
        program = '''import sys,runpy
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools import workflow_entry as entry
marker=Path(sys.argv[2])
def crash(value, root):
    marker.write_text('action happened')
    raise ValueError('injected after action')
entry.execute=crash
sys.argv=[sys.argv[1]+'/scripts/workflow.py','run','--request',sys.argv[3],'--run-root',sys.argv[4]]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        process = subprocess.run([sys.executable, '-B', '-c', program, str(ROOT), str(marker),
                                  str(self.request), str(self.run_root)], capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(json.loads(process.stdout)['status'], 'UNKNOWN')
        self.assertEqual(marker.read_text(), 'action happened')
        self.assertEqual(self.command('resume', '--request', self.request, '--run-root', self.run_root)[1]['status'], 'UNKNOWN')

    def test_actual_local_collection_and_module_handlers_execute(self):
        for job in ('local-evidence', 'module-plan', 'capability-benchmark'):
            self.request.write_text(json.dumps({'job': job, 'options': {}}))
            result = entry.run(self.request, self.root / job)
            self.assertEqual(result['status'], 'SUCCEEDED')
            if job == 'local-evidence':
                self.assertEqual(result['result']['page_budget']['coverage']['status'], 'PARTIAL')
            elif job == 'module-plan':
                self.assertEqual(result['result']['implementation'], 'NOT_RUN')
            else:
                self.assertEqual(result['result']['human_rework'], 'NOT_MEASURED')

    def test_actual_cli_receipt_binds_current_entry_and_preserves_child_statuses(self):
        receipt = json.loads((ROOT / 'workflows/examples/cli/result.json').read_text())
        import hashlib
        for name, digest in receipt['entry_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(set(receipt['handlers']), {'challenge', 'local', 'modules', 'benchmark', 'spring'})
        for handler in receipt['handlers'].values():
            self.assertTrue(handler['run_id_preserved'])
            self.assertTrue(handler['completed_resume_did_not_rewrite_state'])
        self.assertEqual(receipt['handlers']['local']['coverage_statuses']['page_budget'], 'PARTIAL')
        self.assertEqual(receipt['handlers']['challenge']['semantic_acceptance'], 'NOT_ASSESSED')
        self.assertEqual(receipt['handlers']['modules']['implementation'], 'NOT_RUN')
        self.assertEqual(receipt['handlers']['spring']['variants'][1]['failures'], [])


if __name__ == '__main__':
    unittest.main()
