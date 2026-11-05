"""Execute local counterexample and check a human-authored report; no writes."""
from pathlib import Path
import hashlib
import json
import runpy
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.conclusion_challenge import check
CASE = Path(__file__).resolve().parent


def candidate_sha256():
    # Fixed order and explicit names bind both behavior contract and source.
    digest = hashlib.sha256()
    for name in ('requirements.md', 'cache_demo.py'):
        digest.update(name.encode() + b'\0' + (CASE / name).read_bytes() + b'\0')
    return digest.hexdigest()


def run_case():
    observed = runpy.run_path(str(CASE / 'cache_demo.py'))['observe']()
    expected = {'before': 'version-one', 'stored_after_write': 'version-two',
                'cached_after_write': 'version-one', 'after_clear': 'version-two'}
    if observed != expected:
        raise ValueError('local counterexample changed; review report again')
    report = json.loads((CASE / 'review.json').read_text())
    runtime = next(e for e in report['evidence'] if e['id'] == 'E-runtime')
    if runtime['observation'] != json.dumps(observed, sort_keys=True):
        raise ValueError('reported runtime evidence differs from actual observation')
    result = check(report, candidate_sha256())
    return {'observed': observed, 'report_check': result, 'source_requests': 0,
            'independent_review': 'NOT_RUN', 'production_diagnosis': 'NOT_RUN'}


if __name__ == '__main__':
    print(json.dumps(run_case(), ensure_ascii=False, indent=2))
