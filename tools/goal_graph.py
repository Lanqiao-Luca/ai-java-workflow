"""Portable goal-Graph contracts. Existing sandbox/native engines stay separate."""
from copy import deepcopy
import re

from tools.native_flow import FlowRejected, relative


class GoalGraphRejected(RuntimeError):
    pass


def demand(condition, message):
    if not condition:
        raise GoalGraphRejected(message)


def token(value):
    demand(isinstance(value, str) and re.fullmatch('[a-z][a-z0-9_-]{0,63}', value) is not None, 'invalid Graph identifier')


def strings(values):
    demand(isinstance(values, list) and all(isinstance(v, str) and v for v in values)
           and len(values) == len(set(values)), 'unique named references required')


def ancestors(nodes, ident):
    found = set()
    remaining = list(nodes[ident]['depends_on'])
    while remaining:
        parent = remaining.pop()
        if parent not in found:
            found.add(parent)
            remaining.extend(nodes[parent]['depends_on'])
    return found


def validate_definition(definition):
    demand(isinstance(definition, dict) and set(definition) == {'version', 'graph_id', 'goals', 'max_parallel', 'nodes'}, 'exact goal Graph definition required')
    demand(type(definition['version']) is int and definition['version'] == 1, 'unsupported goal Graph version')
    token(definition['graph_id'])
    demand(type(definition['max_parallel']) is int and 1 <= definition['max_parallel'] <= 4, 'bounded concurrency required')
    demand(isinstance(definition['goals'], list) and 1 <= len(definition['goals']) <= 32, 'bounded original goals required')
    goals = {}
    for goal in definition['goals']:
        demand(isinstance(goal, dict) and set(goal) == {'id', 'required'}, 'exact goal contract required')
        token(goal['id']); strings(goal['required'])
        demand(bool(goal['required']) and len(goal['required']) <= 64 and goal['id'] not in goals, 'unique complete goal scope required')
        goals[goal['id']] = goal
    demand(isinstance(definition['nodes'], list) and 1 <= len(definition['nodes']) <= 64, 'bounded node set required')
    nodes, owners, closures = {}, {}, []
    fields = {'id', 'kind', 'depends_on', 'handler', 'contract', 'writes', 'goal_id', 'required'}
    for node in definition['nodes']:
        demand(isinstance(node, dict) and set(node) == fields, 'exact node contract required')
        token(node['id'])
        demand(node['id'] not in nodes and isinstance(node['kind'], str)
               and node['kind'] in {'loop', 'gate', 'closure'}, 'duplicate or unsupported node')
        strings(node['depends_on']); strings(node['writes'])
        demand(type(node['required']) is bool and len(node['writes']) <= 64, 'explicit requirement/write bound required')
        for name in node['writes']:
            try:
                relative(name)
            except FlowRejected as exc:
                raise GoalGraphRejected('unsafe declared output path') from exc
        if node['kind'] == 'loop':
            token(node['handler'])
            demand(isinstance(node['contract'], str) and node['contract'] in {'task', 'inspection', 'defect'}
                   and bool(node['writes']), 'declared Loop result contract/products required')
            if node['goal_id'] is not None:
                demand(isinstance(node['goal_id'], str) and node['goal_id'] in goals
                       and node['goal_id'] not in owners and node['required'], 'goal must have one required Loop owner')
                owners[node['goal_id']] = node['id']
        elif node['kind'] == 'gate':
            token(node['handler'])
            demand(node['contract'] == 'review' and node['required'] and node['goal_id'] is None
                   and not node['writes'] and bool(node['depends_on']), 'read-only required gate contract required')
        else:
            demand(node['handler'] is None and node['contract'] == 'closure' and node['required']
                   and node['goal_id'] is None and not node['writes'] and bool(node['depends_on']), 'explicit required closure contract required')
            closures.append(node['id'])
        nodes[node['id']] = node
    demand(set(owners) == set(goals) and len(closures) == 1, 'every original goal and exactly one closure required')
    for node in nodes.values():
        demand(set(node['depends_on']) <= set(nodes), 'unknown dependency')
    done = set()
    while len(done) < len(nodes):
        ready = {ident for ident, node in nodes.items() if ident not in done and set(node['depends_on']) <= done}
        demand(bool(ready), 'cyclic goal Graph is not an authorized Loop')
        done |= ready
    closure = closures[0]
    demand(not any(closure in n['depends_on'] for n in nodes.values()), 'closure must be terminal')
    predecessors = ancestors(nodes, closure)
    demand({ident for ident, node in nodes.items() if node['required'] and ident != closure} <= predecessors,
           'closure omits a required branch')
    for node in nodes.values():
        if node['kind'] == 'gate':
            demand(all(nodes[dep]['kind'] == 'loop' for dep in node['depends_on']), 'gates review Loop products only')
    # Dependency order permits reuse of a logical output; incomparable branches may
    # not overlap paths or parent/child paths. This is admission, not an OS sandbox.
    all_nodes = list(nodes.values())
    for index, left in enumerate(all_nodes):
        for right in all_nodes[index + 1:]:
            if left['id'] in ancestors(nodes, right['id']) or right['id'] in ancestors(nodes, left['id']):
                continue
            demand(not any(a == b or a.startswith(b + '/') or b.startswith(a + '/')
                           for a in left['writes'] for b in right['writes']), 'concurrent output conflict')
    return deepcopy(definition)
