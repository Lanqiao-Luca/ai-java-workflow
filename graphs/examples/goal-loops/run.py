"""Exercise all three expected outcomes using real Graph/Loop programs and fixtures."""
from pathlib import Path
import json
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.goal_graph_loops import fixture_graph, summary
from tools.goal_graph_run import GoalGraphRun


def run_examples():
    results = {}
    with tempfile.TemporaryDirectory(prefix='public-goal-graph-') as temporary:
        for scenario in ['complete', 'partial', 'unknown-effect']:
            fixture = fixture_graph(scenario)
            state = GoalGraphRun(fixture.definition, fixture.handlers, fixture.context,
                                 Path(temporary) / scenario, budget_seconds=20).run()
            if state['status'] != fixture.expected_status:
                raise ValueError('unexpected synthetic Graph outcome')
            results[scenario] = summary(state, scenario)
    return results


if __name__ == '__main__':
    print(json.dumps({'synthetic': True, 'expectations_met': True, 'results': run_examples()}, indent=2))
