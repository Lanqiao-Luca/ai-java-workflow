"""Finite read-only evidence collection. The callback owns bounded source access.

CONVERGED means required evidence is covered, never that the service is healthy.
This controller does not sleep, schedule, write to sources or retry UNKNOWN calls.
"""
from copy import deepcopy
import math
import time

from tools.finding_ledger import context, identity, names


def demand(condition, message):
    if not condition:
        raise ValueError('inspection: ' + message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def inspect(plan, collect, *, clock=time.time):
    """Call collect(requirement, step, remaining_seconds) only for admitted reads.

    Callback timeouts must be enforced by the source adapter; this is not a sandbox.
    Only a MISSING response proposing a distinct next step can request another read.
    """
    demand(isinstance(plan, dict) and set(plan) == {
        'scope_id', 'context', 'requirements', 'authorized_sources', 'max_rounds',
        'budget_seconds', 'deadline', 'not_before'}, 'exact plan required')
    context(plan['context'])
    demand(isinstance(plan['scope_id'], str) and bool(plan['scope_id']), 'scope identity required')
    demand(type(plan['max_rounds']) is int and 1 <= plan['max_rounds'] <= 10, 'bounded rounds required')
    demand(all(number(plan[k]) for k in ('budget_seconds', 'deadline', 'not_before'))
           and 0 < plan['budget_seconds'] <= 3600, 'bounded finite times required')
    names(plan['authorized_sources'])
    requirements = plan['requirements']
    demand(isinstance(requirements, list) and 0 < len(requirements) <= 64, 'bounded required scope required')
    for requirement in requirements:
        demand(isinstance(requirement, dict) and set(requirement) == {'id', 'source', 'kind'}, 'exact requirement required')
        demand(all(isinstance(v, str) and bool(v.strip()) for v in requirement.values()), 'named requirement fields required')
    ids = [r['id'] for r in requirements]
    names(ids)
    demand(set(plan['authorized_sources']) <= {r['source'] for r in requirements}, 'unrelated authorized source')
    # Freeze the caller's input so a callback cannot silently narrow the scope.
    plan = deepcopy(plan)
    requirements = plan['requirements']
    started = previous_time = clock()
    demand(number(started), 'finite clock required')
    deadline = min(plan['deadline'], started + plan['budget_seconds'])
    state = {'status': 'PARTIAL', 'scope_complete': False, 'scope_id': plan['scope_id'],
             'context': plan['context'], 'required': ids, 'covered': [], 'missing': list(ids),
             'observations': [], 'findings': [], 'reasons': {}, 'rounds_used': 0,
             'started_at': started, 'deadline': deadline, 'elapsed': 0}
    queue = {ident: 'initial' for ident in ids}
    steps = {ident: set() for ident in ids}
    hashes = {ident: set() for ident in ids}

    def now():
        nonlocal previous_time
        value = clock()
        demand(number(value) and value >= previous_time, 'clock moved backwards')
        previous_time = value
        state['elapsed'] = value - started
        return value

    for round_number in range(1, plan['max_rounds'] + 1):
        if not queue or now() >= deadline:
            break
        state['rounds_used'] = round_number
        following = {}
        for requirement in requirements:
            ident = requirement['id']
            if ident not in queue:
                continue
            if now() >= deadline:
                state['reasons'][ident] = 'BUDGET_EXHAUSTED'
                continue
            if requirement['source'] not in plan['authorized_sources']:
                state['reasons'][ident] = 'DENIED_SOURCE'
                continue
            step = queue[ident]
            steps[ident].add(step)
            try:
                report = collect(dict(requirement), step, deadline - now())
                demand(isinstance(report, dict) and set(report) == {
                    'requirement_id', 'source', 'kind', 'context', 'status', 'evidence_id',
                    'artifact_sha256', 'observed_at', 'finding', 'next_step'}, 'exact observation required')
                demand(report['requirement_id'] == ident and report['source'] == requirement['source']
                       and report['kind'] == requirement['kind'], 'observation source/scope mismatch')
                context(report['context'])
                demand(report['context'] == plan['context'], 'stale context')
                demand(report['status'] in {'OBSERVED', 'MISSING', 'DENIED', 'UNKNOWN', 'FUTURE', 'CHANGE_REQUIRED'}, 'invalid observation status')
                demand(number(report['observed_at']) and plan['not_before'] <= report['observed_at'] <= now(), 'stale or future-dated evidence')
                demand(report['finding'] is None or isinstance(report['finding'], str), 'invalid finding')
                demand(report['next_step'] is None or isinstance(report['next_step'], str) and bool(report['next_step'].strip()), 'invalid next step')
                demand(report['evidence_id'] is None or isinstance(report['evidence_id'], str) and bool(report['evidence_id']), 'invalid evidence identity')
                if report['artifact_sha256'] is not None:
                    identity(report['artifact_sha256'])
                if report['status'] in {'OBSERVED', 'MISSING'}:
                    demand(isinstance(report['evidence_id'], str) and bool(report['evidence_id']), 'source evidence identity required')
                    identity(report['artifact_sha256'])
                report = deepcopy(report)
            except Exception:
                state['observations'].append({'requirement_id': ident, 'step': step, 'status': 'UNKNOWN'})
                state['reasons'][ident] = 'UNKNOWN_OR_INVALID_REPORT'
                continue
            state['observations'].append({'step': step, **report})
            if now() > deadline:
                state['reasons'][ident] = 'LATE_EVIDENCE'
                continue
            if report['artifact_sha256'] and report['artifact_sha256'] in hashes[ident]:
                state['reasons'][ident] = 'NO_INFORMATION_GAIN'
                continue
            if report['artifact_sha256']:
                hashes[ident].add(report['artifact_sha256'])
            if report['status'] == 'OBSERVED':
                state['covered'].append(ident)
                state['reasons'].pop(ident, None)
                if report['finding']:
                    state['findings'].append({'requirement_id': ident, 'evidence_id': report['evidence_id'], 'finding': report['finding']})
            elif report['status'] == 'MISSING':
                next_step = report['next_step']
                if next_step is not None and next_step not in steps[ident]:
                    following[ident] = next_step
                    state['reasons'][ident] = 'NEEDS_EVIDENCE'
                else:
                    state['reasons'][ident] = 'NO_EFFECTIVE_NEXT_STEP'
            else:
                state['reasons'][ident] = report['status']
        queue = following
    state['covered'] = sorted(state['covered'])
    state['missing'] = sorted(set(ids) - set(state['covered']))
    state['scope_complete'] = not state['missing']
    state['status'] = 'CONVERGED' if state['scope_complete'] else 'PARTIAL'
    for ident in state['missing']:
        if ident in queue or ident not in state['reasons']:
            state['reasons'][ident] = 'BUDGET_EXHAUSTED' if now() >= deadline else 'ROUND_LIMIT'
    now()
    return state
