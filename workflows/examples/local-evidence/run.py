"""Collect only this independently fictional two-file allowlist; do not write."""
from copy import deepcopy
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.local_evidence import collect
CASE = Path(__file__).resolve().parent


def run_examples():
    scope = json.loads((CASE / 'scope.json').read_text())
    variants = {}
    for name in ('complete', 'sample', 'bounded_empty', 'page_budget'):
        spec = deepcopy(scope)
        if name == 'sample':
            spec['mode'] = 'sample'
        elif name == 'bounded_empty':
            spec['needle'] = 'ABSENT'
        elif name == 'page_budget':
            spec['max_pages'] = 1
        variants[name] = collect((CASE / 'fixtures').resolve(), spec)
    expected = {'complete': 'COMPLETE_MATCH', 'sample': 'SAMPLE_FOUND',
                'bounded_empty': 'COMPLETE_EMPTY', 'page_budget': 'PARTIAL'}
    if {n: v['coverage']['status'] for n, v in variants.items()} != expected:
        raise ValueError('unexpected local coverage result')
    return variants


if __name__ == '__main__':
    print(json.dumps(run_examples(), ensure_ascii=False, indent=2))
