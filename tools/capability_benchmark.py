"""Small, declared structural-check comparison; no model or engineering ROI claim."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import platform
import runpy
import time
from tools.conclusion_challenge import check, ChallengeError

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'workflows/examples/capability-benchmark'
BASE = ROOT / 'workflows/examples/conclusion-challenge'
EDITS = {'none', 'missing_cell', 'candidate_drift', 'blank_probe_result',
         'done_without_evidence', 'missing_sensitivity', 'correlated', 'pending'}


def variant(base, edit):
    report = deepcopy(base)
    if edit == 'missing_cell':
        report['matrix'].pop()
    elif edit == 'candidate_drift':
        report['candidate_sha256'] = '0' * 64
    elif edit == 'blank_probe_result':
        report['probes'][0]['result'] = ''
    elif edit == 'done_without_evidence':
        report['probes'][0]['evidence'] = []
    elif edit == 'missing_sensitivity':
        report['sensitivity'].pop()
    elif edit == 'correlated':
        for item in report['evidence']:
            item['source_group'] = 'same-observation-group'
    elif edit == 'pending':
        report['probes'][0].update(state='NOT_RUN', evidence=[], result='Not executed; preserve missing evidence.')
    elif edit != 'none':
        raise ValueError('unsupported benchmark edit')
    return report


def minimal_fields(report, candidate):
    # Deliberately weak and transparent baseline; not a pre-existing AI method.
    return isinstance(report, dict) and all(k in report for k in ('candidate_sha256', 'hypotheses', 'evidence', 'matrix'))


def contract_check(report, candidate):
    try:
        check(report, candidate)
    except ChallengeError:
        return False
    return True


def summarize(rows):
    if not isinstance(rows, list):
        raise ValueError('observation list')
    total, evaluated, correct, misses, false_alarms, detected, repairs = len(rows), 0, 0, 0, 0, 0, 0
    restore_failures, restore_unknowns = 0, 0
    for row in rows:
        if (row['state'] not in {'DONE', 'UNKNOWN'} or type(row['expected_valid']) is not bool
                or type(row['nanoseconds']) is not int or row['nanoseconds'] < 0
                or type(row['repair']['attempts']) is not int or row['repair']['attempts'] not in {0, 1}
                or (row['state'] == 'DONE' and row['decision'] not in {'VALID', 'INVALID'})
                or (row['state'] == 'UNKNOWN' and row['decision'] is not None)):
            raise ValueError('invalid observation or measurement')
        if row['state'] == 'DONE':
            evaluated += 1
            valid = row['decision'] == 'VALID'
            gold = row['expected_valid']
            correct += valid == gold
            misses += not gold and valid
            false_alarms += gold and not valid
            detected += not gold and not valid
        repairs += row['repair']['attempts']
        if row['repair']['attempts']:
            restore_failures += row['repair']['state'] == 'DONE' and row['repair']['decision'] == 'INVALID'
            restore_unknowns += row['repair']['state'] == 'UNKNOWN'
    return {'tasks': total, 'evaluated': evaluated, 'unknown': total - evaluated,
            'correct': correct, 'misses': misses, 'false_alarms': false_alarms, 'detected_defects': detected,
            'accuracy': correct / total if total and total == evaluated else None,
            'precision': detected / (detected + false_alarms) if detected + false_alarms else None,
            'recall': detected / (detected + misses) if detected + misses else None,
            'scripted_restores': repairs,
            'restore_failures': restore_failures, 'restore_unknowns': restore_unknowns,
            'initial_nanoseconds': sum(r['nanoseconds'] for r in rows)}


def measured(strategy, report, candidate):
    start = time.perf_counter_ns()
    try:
        valid = strategy(report, candidate)
        if type(valid) is not bool:
            raise ValueError('strategy must return a boolean')
    except Exception as error:
        return {'state': 'UNKNOWN', 'decision': None, 'category': type(error).__name__,
                'nanoseconds': time.perf_counter_ns() - start}
    return {'state': 'DONE', 'decision': 'VALID' if valid else 'INVALID',
            'nanoseconds': time.perf_counter_ns() - start}


def evaluate(cases, base, candidate, strategies=None):
    if not isinstance(cases, list) or not cases:
        raise ValueError('fixed labeled tasks required')
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {'id', 'edit', 'expected_valid', 'basis'}:
            raise ValueError('task fields')
        if (not isinstance(case['id'], str) or not case['id'] or case['id'] in seen
                or not isinstance(case['edit'], str) or case['edit'] not in EDITS
                or type(case['expected_valid']) is not bool
                or not isinstance(case['basis'], str) or not case['basis'].strip()):
            raise ValueError('task identity, label or basis')
        seen.add(case['id'])
    results = {}
    for name, strategy in (strategies or {'minimal_fields': minimal_fields, 'contract_checker': contract_check}).items():
        observations = []
        for case in cases:
            # Neither strategy receives the label, basis, or repair definition.
            row = measured(strategy, variant(base, case['edit']), candidate)
            row.update(task=case['id'], expected_valid=case['expected_valid'])
            row['repair'] = {'attempts': 0, 'state': 'NOT_RUN' if row['state'] == 'UNKNOWN' else 'NOT_NEEDED'}
            if not case['expected_valid'] and row['state'] == 'DONE':
                # Apply identical externally prescribed pristine restoration once.
                repair = measured(strategy, deepcopy(base), candidate)
                row['repair'] = dict(repair, attempts=1)
            observations.append(row)
        results[name] = {'observations': observations, 'metrics': summarize(observations)}
    return results


def source_hashes():
    files = [Path(__file__), CASE / 'cases.json', CASE / 'run.py', BASE / 'review.json',
             BASE / 'run.py', BASE / 'requirements.md', BASE / 'cache_demo.py', ROOT / 'tools/conclusion_challenge.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def run_benchmark():
    before = source_hashes()
    definition = json.loads((CASE / 'cases.json').read_text())
    if set(definition) != {'oracle_version', 'oracle_origin', 'cases'} or definition['oracle_version'] != 1:
        raise ValueError('oracle definition version')
    base = json.loads((BASE / 'review.json').read_text())
    candidate = runpy.run_path(str(BASE / 'run.py'))['candidate_sha256']()
    results = evaluate(definition['cases'], base, candidate)
    if source_hashes() != before:
        raise ValueError('benchmark inputs or strategies changed during run')
    complete = all(row['state'] == 'DONE' and
                   (row['repair']['attempts'] == 0 or (row['repair']['state'] == 'DONE' and row['repair']['decision'] == 'VALID'))
                   for group in results.values() for row in group['observations'])
    return {'status': 'COMPLETED' if complete else 'PARTIAL', 'oracle_version': 1,
            'oracle_origin': definition['oracle_origin'], 'source_sha256': before,
            'environment': {'python': platform.python_version(), 'system': platform.system(), 'architecture': platform.machine()},
            'timing': 'One sequential call per initial judgment, imports/fixture preparation excluded; perf_counter_ns',
            'results': results, 'human_rework': 'NOT_MEASURED', 'model_cost': 'NOT_MEASURED',
            'engineering_effect': 'NOT_MEASURED', 'source_requests': 0}
