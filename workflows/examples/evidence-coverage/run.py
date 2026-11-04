"""Run synthetic page observation controls without querying any source."""
from pathlib import Path
import json
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.evidence_coverage import assess


def run_examples():
    fixture = json.loads((Path(__file__).parent / 'scenarios.json').read_text())
    results = {}
    for case in fixture['cases']:
        result = assess(case['scope'], case['pages'])
        if result['status'] != case['expected']:
            raise ValueError('unexpected coverage outcome')
        results[case['name']] = result
    return {'synthetic': True, 'source_requests': 0, 'results': results}


if __name__ == '__main__':
    print(json.dumps(run_examples(), ensure_ascii=False, indent=2))
