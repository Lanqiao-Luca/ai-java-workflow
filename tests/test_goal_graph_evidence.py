"""Real deterministic Gate invocations and typed-Loop receipt counterexamples."""
from copy import deepcopy
from pathlib import Path
import json
import runpy
import unittest

from test_goal_graph_runtime import CONTEXT, GraphFixture
from tools.goal_graph import GoalGraphRejected
from tools.goal_graph_evidence import review_inputs, validate_loop
from tools.goal_graph_run import Handler


class GateTests(GraphFixture, unittest.TestCase):
    def setUp(self):
        GraphFixture.setUp(self)
        self.graph['nodes'].insert(2, {'id': 'review', 'kind': 'gate', 'depends_on': ['a', 'b'],
            'handler': 'demo-review', 'contract': 'review', 'writes': [], 'goal_id': None, 'required': True})
        self.graph['nodes'][-1]['depends_on'] = ['review']

    def registry(self, gate=review_inputs, callback=None):
        return {n['handler']: Handler(gate if n['kind'] == 'gate' else callback or self.callback,
                    'e' * 64 if n['kind'] == 'gate' else 'd' * 64)
                for n in self.graph['nodes'] if n['handler']}

    def test_registered_reviewer_and_explicit_closure_bind_actual_products(self):
        result = self.run_graph(handlers=self.registry())
        self.assertEqual(result['status'], 'SUCCEEDED')
        proof = result['nodes']['review']['result']
        self.assertEqual(proof['reviewer']['identity'], 'e' * 64)
        self.assertEqual(proof['run_id'], result['run_id'])
        self.assertEqual(proof['gate_execution_id'], result['nodes']['review']['execution_id'])
        self.assertEqual(set(proof['targets']), {'a', 'b'})
        self.assertEqual(set(result['nodes']['close']['result']['targets']), {'a', 'b', 'review'})

    def test_empty_pass_is_not_review(self):
        def empty(request):
            return {'status': 'SUCCEEDED', 'context': CONTEXT, 'payload_path': None, 'result': {'verdict': 'PASS'}}
        result = self.run_graph(handlers=self.registry(empty))
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['goals']['goal-a']['owner_status'], 'SUCCEEDED')
        self.assertEqual(result['goals']['goal-a']['status'], 'FAILED')

    def test_stale_snapshot_or_forged_reviewer_or_missing_branch_rejected(self):
        for change in ['snapshot', 'reviewer', 'branch', 'execution']:
            with self.subTest(change=change):
                self.root = self.root / change; self.root.mkdir()
                def gate(request):
                    proof = review_inputs(request)
                    if change == 'snapshot': proof['result']['snapshot_id'] = '0' * 64
                    elif change == 'reviewer': proof['result']['reviewer']['identity'] = 'f' * 64
                    elif change == 'branch': proof['result']['targets'].pop('b')
                    else: proof['result']['gate_execution_id'] = 'another-gate'
                    return proof
                self.assertEqual(self.run_graph(handlers=self.registry(gate))['status'], 'FAILED')

    def test_review_receipt_from_another_run_cannot_be_replayed(self):
        cached = []
        def gate(request):
            if not cached:
                cached.append(review_inputs(request))
            return deepcopy(cached[0])
        first = self.run_graph(handlers=self.registry(gate))
        self.assertEqual(first['status'], 'SUCCEEDED')
        self.root = self.root / 'second'; self.root.mkdir()
        second = self.run_graph(handlers=self.registry(gate))
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertEqual(second['status'], 'FAILED')

    def test_dependency_tamper_after_review_cannot_reach_closure(self):
        def gate(request):
            proof = review_inputs(request)
            item = request['inputs']['a']
            (Path(item['workspace']) / item['record']['payload_path']).write_text('{}')
            return proof
        result = self.run_graph(handlers=self.registry(gate))
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotEqual(result['nodes']['close']['status'], 'SUCCEEDED')
        self.assertEqual(len(result['definition']['goals']), 2)

    def test_byte_consistent_false_completion_and_reduced_scope_rejected(self):
        for mode in ['false', 'reduced']:
            self.root = self.root / mode; self.root.mkdir()
            def callback(request):
                outcome = self.callback(request)
                if request['node']['id'] == 'a':
                    if mode == 'false': outcome['result']['complete'] = False
                    else: outcome['result'].update(required=[], completed=[])
                    (Path(request['workspace']) / outcome['payload_path']).write_text(json.dumps(outcome['result']))
                return outcome
            result = self.run_graph(handlers=self.registry(callback=callback))
            self.assertEqual(result['status'], 'FAILED')

    def test_optional_skip_does_not_substitute_for_required_goals(self):
        self.graph['nodes'].insert(0, {'id': 'diagnostic', 'kind': 'loop', 'depends_on': [],
            'handler': 'demo-diagnostic', 'contract': 'task', 'writes': ['diagnostic.json'], 'goal_id': None, 'required': False})
        def callback(request):
            if request['node']['id'] == 'diagnostic':
                return {'status': 'SKIPPED', 'context': CONTEXT, 'payload_path': None, 'result': {'reason': 'optional diagnostic not needed'}}
            return self.callback(request)
        result = self.run_graph(handlers=self.registry(callback=callback))
        self.assertEqual(result['status'], 'SUCCEEDED')
        self.assertEqual(result['nodes']['diagnostic']['status'], 'SKIPPED')


class TypedLoopTests(unittest.TestCase):
    def sample(self, family):
        root = Path(__file__).resolve().parents[1]
        examples = runpy.run_path(str(root / ('loops/examples/' + family + '/run.py')))['run_examples']()
        result = examples['supplement' if family == 'inspection' else 'complete']
        goal_id = result['scope_id' if family == 'inspection' else 'goal_id']
        node = {'goal_id': goal_id, 'contract': family}
        goal = {'id': goal_id, 'required': list(result['required']), 'operations': list(result.get('required_operations', []))}
        return node, {'result': result, 'ended_at': 1005}, goal

    def test_complete_inspection_with_anomalies_is_valid_evidence(self):
        node, record, goal = self.sample('inspection')
        self.assertTrue(record['result']['findings'])
        validate_loop(node, record, goal, record['result']['context'], 1025)

    def test_inspection_requires_actual_current_observations(self):
        node, record, goal = self.sample('inspection')
        for change in ['missing', 'no-observations', 'stale']:
            altered = deepcopy(record)
            if change == 'missing': altered['result']['missing'] = [goal['required'][0]]
            elif change == 'no-observations': altered['result']['observations'] = []
            else:
                for row in altered['result']['observations']:
                    if row['status'] == 'OBSERVED': row['context']['candidate_id'] = '0' * 64
            with self.assertRaises(GoalGraphRejected):
                validate_loop(node, altered, goal, record['result']['context'], 1025)

    def test_complete_defect_uses_existing_independent_closure_contract(self):
        node, record, goal = self.sample('defect')
        validate_loop(node, record, goal, record['result']['context'], 1025)

    def test_defect_cannot_drop_behavior_operation_or_closure_proof(self):
        node, record, goal = self.sample('defect')
        for change in ['behavior', 'operation', 'closure']:
            altered = deepcopy(record)
            if change == 'behavior': altered['result']['checks'].pop('behavior')
            elif change == 'operation': altered['result']['required_operations'] = ['missing-operation']
            else:
                issue = next(iter(altered['result']['finding_ledger']['findings'].values()))
                issue['closure_evidence'] = []
            with self.assertRaises(GoalGraphRejected):
                validate_loop(node, altered, goal, record['result']['context'], 1025)

    def test_inner_loop_cannot_claim_completion_with_exhausted_time_or_no_round(self):
        node, record, goal = self.sample('inspection')
        for change in [{'elapsed': 100}, {'rounds_used': 0}, {'deadline': 2000}]:
            altered = deepcopy(record)
            altered['result'].update(change)
            with self.assertRaises(GoalGraphRejected):
                validate_loop(node, altered, goal, record['result']['context'], 1025)


if __name__ == '__main__':
    unittest.main()
