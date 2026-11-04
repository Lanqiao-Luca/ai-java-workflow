"""Run/pause/resume the synthetic foreground goal Graph; no model or service."""
from pathlib import Path
import argparse
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.goal_graph import GoalGraphRejected
from tools.goal_graph_loops import fixture_graph, summary
from tools.goal_graph_run import GoalGraphRun


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--scenario', choices=['complete', 'partial', 'unknown-effect'], default='complete')
    parser.add_argument('--budget-seconds', type=float, default=20)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--pause-after', choices=['inspection', 'defect', 'review-inspection', 'review-defect', 'close'])
    args = parser.parse_args()
    try:
        fixture = fixture_graph(args.scenario)
        state = GoalGraphRun(fixture.definition, fixture.handlers, fixture.context, args.run_root,
                             budget_seconds=args.budget_seconds, resume=args.resume, pause_after=args.pause_after).run()
    except (GoalGraphRejected, OSError, ValueError, KeyError) as exc:
        print('Goal Graph REJECTED:', type(exc).__name__, '; inspect selected fixture/checkpoint prerequisites')
        return 2
    print(json.dumps(summary(state, args.scenario), ensure_ascii=False, indent=2))
    return 0 if state['status'] == 'SUCCEEDED' else 3 if state['status'] == 'PAUSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
