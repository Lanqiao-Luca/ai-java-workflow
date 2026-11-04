"""Graph contract counterexamples; no dispatch, sandbox or model execution."""
from copy import deepcopy
import unittest

from tools.goal_graph import GoalGraphRejected, validate_definition


def definition():
    def loop(ident, goal):
        return {'id': ident, 'kind': 'loop', 'depends_on': [], 'handler': 'demo-' + ident,
                'contract': 'task', 'writes': [ident + '/result.json'], 'goal_id': goal, 'required': True}
    return {'version': 1, 'graph_id': 'synthetic-goals', 'max_parallel': 2,
            'goals': [{'id': 'goal-a', 'required': ['accept-a']}, {'id': 'goal-b', 'required': ['accept-b']}],
            'nodes': [loop('a', 'goal-a'), loop('b', 'goal-b'),
                      {'id': 'close', 'kind': 'closure', 'depends_on': ['a', 'b'], 'handler': None,
                       'contract': 'closure', 'writes': [], 'goal_id': None, 'required': True}]}


class DefinitionTests(unittest.TestCase):
    def rejected(self, change):
        value = definition(); change(value)
        with self.assertRaises(GoalGraphRejected):
            validate_definition(value)

    def test_independent_goals_and_explicit_closure(self):
        value = definition()
        result = validate_definition(value)
        self.assertEqual(result, value)
        result['goals'].clear()
        self.assertEqual(len(value['goals']), 2)

    def test_missing_goal_or_optional_owner_rejected(self):
        self.rejected(lambda d: d['nodes'][1].update(goal_id=None))
        self.rejected(lambda d: d['nodes'][1].update(required=False))
        self.rejected(lambda d: d['nodes'][1].update(goal_id='goal-a'))

    def test_cycles_and_unknown_dependencies_rejected(self):
        self.rejected(lambda d: d['nodes'][0].update(depends_on=['missing']))
        self.rejected(lambda d: d['nodes'][0].update(depends_on=['a']))
        def cycle(d):
            d['nodes'][0]['depends_on'] = ['b']; d['nodes'][1]['depends_on'] = ['a']
        self.rejected(cycle)

    def test_missing_duplicate_or_nonterminal_closure_rejected(self):
        self.rejected(lambda d: d['nodes'].pop())
        def duplicate(d):
            node = deepcopy(d['nodes'][-1]); node['id'] = 'second-close'; d['nodes'].append(node)
        self.rejected(duplicate)
        self.rejected(lambda d: d['nodes'][0].update(depends_on=['close']))

    def test_closure_must_include_all_required_branches(self):
        self.rejected(lambda d: d['nodes'][-1].update(depends_on=['a']))

    def test_concurrent_equal_or_nested_paths_rejected(self):
        for paths in [(['shared.json'], ['shared.json']), (['shared'], ['shared/result.json'])]:
            def change(d):
                d['nodes'][0]['writes'], d['nodes'][1]['writes'] = paths
            self.rejected(change)

    def test_dependency_order_allows_same_logical_output(self):
        value = definition()
        value['nodes'][1].update(depends_on=['a'], writes=value['nodes'][0]['writes'])
        validate_definition(value)

    def test_hidden_escaped_or_duplicate_writes_rejected(self):
        for writes in [['../out'], ['.private/out'], ['/out'], ['out', 'out'], ['a//b']]:
            self.rejected(lambda d: d['nodes'][0].update(writes=writes))

    def test_gate_is_read_only_and_reviews_declared_loop_products(self):
        value = definition()
        gate = {'id': 'review', 'kind': 'gate', 'depends_on': ['a', 'b'], 'handler': 'demo-review',
                'contract': 'review', 'writes': [], 'goal_id': None, 'required': True}
        value['nodes'].insert(2, gate); value['nodes'][-1]['depends_on'] = ['review']
        validate_definition(value)
        gate['writes'] = ['report.md']
        with self.assertRaises(GoalGraphRejected):
            validate_definition(value)

    def test_definition_does_not_accept_runtime_or_arbitrary_code_fields(self):
        self.rejected(lambda d: d.update(run_id='not-a-definition'))
        self.rejected(lambda d: d['nodes'][0].update(command=['arbitrary-shell']))
        self.rejected(lambda d: d.update(max_parallel=True))
        self.rejected(lambda d: d.update(version=True))

    def test_goal_scope_is_nonempty_and_named(self):
        self.rejected(lambda d: d['goals'][0].update(required=[]))
        self.rejected(lambda d: d['goals'][0].update(required=['same', 'same']))
        self.rejected(lambda d: d['nodes'][1].update(id='a'))

    def test_malformed_json_fields_are_contract_rejections(self):
        for field in ('kind', 'contract', 'goal_id', 'handler'):
            self.rejected(lambda d: d['nodes'][0].update({field: {}}))


if __name__ == '__main__':
    unittest.main()
