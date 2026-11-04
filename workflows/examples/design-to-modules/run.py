"""Run deterministic synthetic design bindings and module-plan control cases only."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.module_plan import PlanError, load_json, validate_plan

CASE = Path(__file__).resolve().parent


def run_examples():
    contract, plan, review = [load_json(CASE / name) for name in ('contract.json', 'plan.json', 'review.json')]
    sha = lambda name: hashlib.sha256((CASE / name).read_bytes()).hexdigest()
    if (contract['sha256'] != sha('design-v2.md') or review['reviewed_sha256'] != sha('design-v1.md')
            or review['revision_sha256'] != contract['sha256'] or review['independent_context'] is not False
            or review['independent_acceptance'] != 'NOT_RUN'):
        raise ValueError('synthetic design or review binding drift')
    result = validate_plan(plan, contract)
    negative = {}
    missing = deepcopy(plan)
    missing['modules'][-1]['requirements'] = []
    overlap = deepcopy(plan)
    overlap['modules'][2]['writes'] = overlap['modules'][1]['writes'][:]
    cycle = deepcopy(plan)
    cycle['modules'][0]['depends_on'] = ['integration']
    stale = deepcopy(plan)
    stale['design_sha256'] = '0' * 64
    for name, candidate in [('missing_requirement', missing), ('overlapping_writes', overlap),
                            ('dependency_cycle', cycle), ('stale_design', stale)]:
        try:
            validate_plan(candidate, contract)
        except PlanError:
            negative[name] = 'REJECTED'
        else:
            raise ValueError('negative plan was not rejected')
    return {'synthetic': True, 'positive': result, 'negative': negative,
            'professional_review': 'author_walkthrough_only', 'implementation': 'NOT_RUN'}


if __name__ == '__main__':
    print(json.dumps(run_examples(), ensure_ascii=False, indent=2))
