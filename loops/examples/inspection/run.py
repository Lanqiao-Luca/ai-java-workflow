"""Read only explicitly synthetic local fixtures; no network, model or build."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.inspection_loop import inspect


def sha(content):
    return hashlib.sha256(content).hexdigest()


def run_examples():
    required = [{'id': 'log-window', 'source': 'logs', 'kind': 'log'},
                {'id': 'api-response', 'source': 'api', 'kind': 'api'},
                {'id': 'build-report', 'source': 'build', 'kind': 'build'}]
    bindings = {'candidate_id': sha((CASE / 'candidate.json').read_bytes()),
                'requirements_id': sha(json.dumps(required, sort_keys=True).encode()),
                'rules_id': sha((ROOT / 'tools/inspection_loop.py').read_bytes())}
    allowed_files = {'service-head.log', 'service-tail.log', 'api-response.json', 'build-report.json'}
    results = {}
    for scenario in json.loads((CASE / 'scenarios.json').read_text())['cases']:
        plan = {'scope_id': 'synthetic-observation-' + scenario['name'], 'context': bindings,
                'requirements': required, 'authorized_sources': scenario['authorized_sources'],
                'max_rounds': 2, 'budget_seconds': 20, 'deadline': 1025, 'not_before': 1000}

        def collect(requirement, step, remaining):
            entry = scenario['steps'][requirement['id']][step]
            result = {'requirement_id': requirement['id'], 'source': requirement['source'],
                'kind': requirement['kind'], 'context': bindings, 'status': 'FUTURE',
                'evidence_id': None, 'artifact_sha256': None, 'observed_at': 1001,
                'finding': None, 'next_step': None}
            if entry.get('future') is True:
                return result
            name = entry['file']
            if name not in allowed_files:
                raise ValueError('fixture outside admitted file set')
            path = CASE / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
                raise ValueError('invalid bounded fixture')
            content = path.read_bytes()
            result.update(status='OBSERVED', evidence_id='synthetic:' + name, artifact_sha256=sha(content))
            if requirement['kind'] == 'log':
                text = content.decode()
                if 'WINDOW_COMPLETE' not in text:
                    result.update(status='MISSING', next_step=entry['next_step'])
                if '[ERROR]' in text:
                    result['finding'] = 'Synthetic error in the observed log window'
            else:
                payload = json.loads(content)
                if payload.get('synthetic') is not True or payload['candidate_id'] != bindings['candidate_id']:
                    raise ValueError('fixture candidate mismatch')
                if requirement['kind'] == 'api' and payload['http_status'] >= 400:
                    result['finding'] = 'Synthetic HTTP ' + str(payload['http_status'])
                if requirement['kind'] == 'build' and payload['process_exit'] != 0:
                    result['finding'] = 'Synthetic build failure'
            return result

        result = inspect(plan, collect, clock=lambda: 1005)
        if result['status'] != scenario['expected_status'] or result['missing'] != scenario['expected_missing']:
            raise ValueError('synthetic scenario did not meet its declared expectation')
        results[scenario['name']] = result
    return results


if __name__ == '__main__':
    print(json.dumps({'synthetic': True, 'execution': 'local fixture reads only', 'results': run_examples()}, indent=2))
