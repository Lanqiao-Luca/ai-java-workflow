"""Real callbacks, threads and private files; no model, shell, sandbox or service."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import fcntl
import json
import tempfile
import threading
import time
import unittest

from test_goal_graph_definition import definition
from tools.goal_graph import GoalGraphRejected
from tools.goal_graph_run import GoalGraphRun, Handler


CONTEXT = {'candidate_id': 'a' * 64, 'requirements_id': 'b' * 64, 'rules_id': 'c' * 64}


class GraphFixture:
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.graph = definition()
        self.calls = []
        self.modes = {}
        self.barrier = None

    def callback(self, request):
        node = request['node']; ident = node['id']
        self.calls.append(ident)
        state = json.loads((Path(request['workspace']).parents[1] / 'state.json').read_text())
        self.assertEqual(state['nodes'][ident]['status'], 'RUNNING')
        self.assertEqual(state['nodes'][ident]['execution_id'], request['execution_id'])
        if self.barrier and ident in {'a', 'b'}:
            self.barrier.wait(timeout=3)
        mode = self.modes.get(ident, 'SUCCEEDED')
        if mode == 'raise':
            raise OSError('controlled callback state unknown')
        if mode == 'UNKNOWN':
            return {'status': mode, 'context': CONTEXT, 'payload_path': None, 'result': {}}
        path = Path(request['workspace']) / node['writes'][0]
        path.parent.mkdir(parents=True, exist_ok=True)
        result = {'complete': True, 'goal_id': node['goal_id'], 'required': next((g['required'] for g in self.graph['goals'] if g['id'] == node['goal_id']), []),
                  'completed': next((g['required'] for g in self.graph['goals'] if g['id'] == node['goal_id']), [])}
        path.write_text(json.dumps(result))
        return {'status': mode, 'context': CONTEXT, 'payload_path': node['writes'][0], 'result': result}

    def run_graph(self, *, resume=False, pause_after=None, handlers=None, **changes):
        registry = handlers or {n['handler']: Handler(self.callback, 'd' * 64) for n in self.graph['nodes'] if n['handler']}
        return GoalGraphRun(self.graph, registry, CONTEXT, self.root / 'run', budget_seconds=20,
                            resume=resume, pause_after=pause_after, **changes).run()

class RuntimeTests(GraphFixture, unittest.TestCase):
    def test_concurrent_callbacks_and_explicit_closure(self):
        self.barrier = threading.Barrier(2)
        result = self.run_graph()
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(result['nodes']['close']['status'], 'SUCCEEDED')
        self.assertEqual(set(self.calls), {'a', 'b'})
        self.assertEqual(result['attempts'], 3)

    def test_confirmed_failure_blocks_descendants_not_independent_goal(self):
        child = deepcopy(self.graph['nodes'][0])
        child.update(id='child', handler='demo-child', goal_id=None, writes=['child/result.json'], depends_on=['a'])
        self.graph['nodes'].insert(2, child)
        self.graph['nodes'][-1]['depends_on'].append('child')
        self.modes['a'] = 'FAILED'
        result = self.run_graph()
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['nodes']['b']['status'], 'SUCCEEDED')
        self.assertEqual(result['nodes']['child']['status'], 'BLOCKED')
        self.assertNotIn('child', self.calls)
        self.assertEqual(len(result['goals']), 2)

    def test_partial_is_not_success_or_a_join_input(self):
        self.modes['a'] = 'PARTIAL'
        result = self.run_graph()
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['nodes']['close']['status'], 'BLOCKED')

    def test_required_skip_is_not_success(self):
        self.modes['a'] = 'SKIPPED'
        result = self.run_graph()
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['nodes']['a']['status'], 'FAILED')

    def test_unknown_or_exception_is_never_resumed(self):
        for mode in ['UNKNOWN', 'raise']:
            with self.subTest(mode=mode):
                self.root = self.root / mode; self.root.mkdir()
                self.modes['a'] = mode
                result = self.run_graph()
                self.assertEqual(result['status'], 'UNKNOWN')
                with self.assertRaises(GoalGraphRejected):
                    self.run_graph(resume=True)

    def test_safe_resume_skips_accepted_prefix_and_preserves_deadline(self):
        self.graph['max_parallel'] = 1
        first = self.run_graph(pause_after='a')
        self.assertEqual(first['status'], 'PAUSED')
        second = self.run_graph(resume=True)
        self.assertEqual(second['status'], 'SUCCEEDED')
        self.assertEqual(second['deadline'], first['deadline'])
        self.assertEqual(second['attempts'], 3)
        self.assertEqual(self.calls.count('a'), 1)

    def test_changed_product_blocks_resume_before_more_callbacks(self):
        self.graph['max_parallel'] = 1
        first = self.run_graph(pause_after='a')
        path = self.root / 'run' / first['nodes']['a']['workspace'] / 'a/result.json'
        path.write_text('changed')
        count = len(self.calls)
        with self.assertRaises(GoalGraphRejected):
            self.run_graph(resume=True)
        self.assertEqual(len(self.calls), count)

    def test_changed_registry_or_definition_cannot_resume(self):
        self.run_graph(pause_after='a')
        registry = {n['handler']: Handler(self.callback, 'e' * 64) for n in self.graph['nodes'] if n['handler']}
        with self.assertRaises(GoalGraphRejected):
            self.run_graph(resume=True, handlers=registry)
        self.graph['goals'][0]['required'].append('new-criterion')
        with self.assertRaises(GoalGraphRejected):
            self.run_graph(resume=True)

    def test_active_checkpoint_and_controller_lock_reject_replay(self):
        self.run_graph(pause_after='a')
        with (self.root / 'run/controller.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(GoalGraphRejected):
                self.run_graph(resume=True)
        path = self.root / 'run/state.json'; saved = json.loads(path.read_text())
        saved['status'] = 'RUNNING'; path.write_text(json.dumps(saved))
        with self.assertRaises(GoalGraphRejected):
            self.run_graph(resume=True)

    def test_no_dispatch_when_reservation_cannot_persist(self):
        original = GoalGraphRun._save
        failed = []
        def save(run):
            if run.state['status'] == 'RUNNING' and not failed:
                failed.append(True)
                raise OSError('synthetic write failure')
            original(run)
        with patch.object(GoalGraphRun, '_save', save):
            result = self.run_graph()
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(self.calls, [])

    def test_expired_checkpoint_dispatches_nothing(self):
        first = self.run_graph(pause_after='a', clock=lambda: 100)
        count = len(self.calls)
        result = self.run_graph(resume=True, clock=lambda: first['deadline'] + 1)
        self.assertEqual(result['status'], 'BUDGET_EXHAUSTED')
        self.assertEqual(len(self.calls), count)

    def test_callback_timeout_preserves_unknown_without_claiming_it_stopped(self):
        done = threading.Event()
        def slow(request):
            time.sleep(.12)
            done.set()
            return {'status': 'UNKNOWN', 'context': CONTEXT, 'payload_path': None, 'result': {}}
        handlers = {n['handler']: Handler(slow, 'd' * 64) for n in self.graph['nodes'] if n['handler']}
        result = GoalGraphRun(self.graph, handlers, CONTEXT, self.root / 'run', budget_seconds=.03).run()
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertTrue(done.wait(1))
        with self.assertRaises(GoalGraphRejected):
            GoalGraphRun(self.graph, handlers, CONTEXT, self.root / 'run', budget_seconds=.03, resume=True).run()

    def test_unrelated_resume_directory_is_not_modified(self):
        unrelated = self.root / 'unrelated'; unrelated.mkdir()
        with self.assertRaises(GoalGraphRejected):
            GoalGraphRun(self.graph, {n['handler']: Handler(self.callback, 'd' * 64) for n in self.graph['nodes'] if n['handler']},
                         CONTEXT, unrelated, budget_seconds=20, resume=True)
        self.assertEqual(list(unrelated.iterdir()), [])

    def test_late_closure_cannot_report_success(self):
        ticks = [100]
        original = GoalGraphRun._invoke
        def invoke(run, node, record):
            result = original(run, node, record)
            if node['kind'] == 'closure':
                ticks[0] = 121
                result['ended_at'] = 121
            return result
        with patch.object(GoalGraphRun, '_invoke', invoke):
            result = self.run_graph(clock=lambda: ticks[0])
        self.assertNotEqual(result['status'], 'SUCCEEDED')
        self.assertNotEqual(result['nodes']['close']['status'], 'SUCCEEDED')

    def test_undeclared_product_or_forged_payload_rejected(self):
        original = self.callback
        def forged(request):
            result = original(request)
            if request['node']['id'] == 'a':
                result['result']['complete'] = False
            return result
        registry = {n['handler']: Handler(forged, 'd' * 64) for n in self.graph['nodes'] if n['handler']}
        result = self.run_graph(handlers=registry)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['nodes']['b']['status'], 'SUCCEEDED')


if __name__ == '__main__':
    unittest.main()
