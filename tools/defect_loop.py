"""Bounded whole-goal adjudication over Workflow evidence; no business writes.

The callback returns trusted, bounded Workflow receipts, not model assertions.
It owns execution, provenance and any inner timeout. This module neither submits
nor replays side effects and never treats a successful test as whole-goal success.
"""
from copy import deepcopy
import hashlib
import json
import math
import time

from tools import finding_ledger as findings


def demand(condition, message):
    if not condition:
        raise ValueError('defect: ' + message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _ledger(previous, current, bindings):
    demand(isinstance(current, dict) and set(current) == {'version', 'context', 'findings', 'evidence', 'events'}, 'finding ledger required')
    demand(type(current['version']) is int and current['version'] == 1 and current['context'] == bindings
           and isinstance(current['findings'], dict) and isinstance(current['evidence'], dict)
           and isinstance(current['events'], list), 'ledger context or structure mismatch')
    for ident, receipt in current['evidence'].items():
        demand(receipt['id'] == ident and receipt['kind'] in findings.CHECKS | {'repair'}
               and receipt['status'] in {'PASSED', 'FAILED', 'STALE'}
               and isinstance(receipt['actor'], str) and bool(receipt['actor']), 'invalid evidence identity/kind/status')
        findings.context(receipt['context']); findings.identity(receipt['artifact_sha256'])
        findings.names(receipt['depends_on']); findings.names(receipt['checked_findings'])
        demand(set(receipt['depends_on']) == findings.BINDINGS
               and set(receipt['checked_findings']) <= set(current['findings']), 'evidence inputs or finding references missing')
    if previous is not None:
        demand(set(previous['findings']) <= set(current['findings']), 'original findings disappeared')
        demand(current['events'][:len(previous['events'])] == previous['events'], 'finding history replaced')
        for ident, old in previous['findings'].items():
            new = current['findings'][ident]
            for field in ('id', 'key', 'origin_stage', 'summary', 'location', 'criterion', 'opened_context'):
                demand(new[field] == old[field], 'original finding identity changed')
            demand(new['observations'][:len(old['observations'])] == old['observations'], 'failure observations erased')
        for ident, old in previous['evidence'].items():
            demand(ident in current['evidence'], 'original evidence erased')
            for field in ('id', 'kind', 'actor', 'context', 'artifact_sha256', 'depends_on', 'checked_findings'):
                demand(current['evidence'][ident][field] == old[field], 'original evidence rewritten')
            new = current['evidence'][ident]
            if new['status'] != old['status']:
                demand(new['status'] == 'STALE' and old['status'] in {'PASSED', 'FAILED'}
                       and new.get('previous_status') == old['status'], 'original evidence outcome rewritten')
    unresolved = []
    for ident, issue in current['findings'].items():
        demand(issue['id'] == ident and issue['status'] in {'OPEN', 'REPAIRED', 'CLOSED'}, 'invalid finding status/identity')
        demand(issue['origin_stage'] in findings.CHECKS
               and all(isinstance(issue[key], str) and bool(issue[key].strip())
                       for key in ('key', 'summary', 'location', 'criterion')), 'original issue contract missing')
        findings.context(issue['opened_context'])
        demand(bool(issue['observations']) and all(key in current['evidence'] for key in issue['observations']), 'failure evidence missing')
        for key in issue['observations']:
            receipt = current['evidence'][key]
            demand(receipt['kind'] in findings.CHECKS and (receipt['status'] == 'FAILED'
                   or receipt['status'] == 'STALE' and receipt.get('previous_status') == 'FAILED'), 'original failure outcome missing')
        if issue['status'] != 'CLOSED':
            unresolved.append(ident)
            continue
        repair = current['evidence'].get(issue['repair_evidence'])
        demand(repair is not None and repair['kind'] == 'repair' and repair['status'] == 'PASSED', 'repair proof missing')
        temporary = deepcopy(current)
        temporary['findings'][ident]['status'] = 'REPAIRED'
        # Recheck the actual closure evidence, not a prefilled CLOSED string.
        findings.close(temporary, ident, issue['closure_evidence'])
    return deepcopy(current), sorted(unresolved)


def run_defect(plan, workflow, *, clock=time.time):
    """One callback is one substantive Workflow round, not one tool/query attempt.

    It receives the original goal, earliest requested phase, remaining budget and
    known operation receipts. Raw JSON from a model is not a trusted adapter.
    """
    demand(isinstance(plan, dict) and set(plan) == {'goal_id', 'requirements_id', 'rules_id', 'criteria',
        'operation_ids', 'max_rounds', 'budget_seconds', 'deadline', 'not_before'}, 'exact goal plan required')
    findings.identity(plan['requirements_id']); findings.identity(plan['rules_id'])
    demand(isinstance(plan['goal_id'], str) and bool(plan['goal_id']), 'goal identity required')
    demand(type(plan['max_rounds']) is int and 1 <= plan['max_rounds'] <= 10, 'bounded rounds required')
    demand(all(finite(plan[k]) for k in ('budget_seconds', 'deadline', 'not_before'))
           and 0 < plan['budget_seconds'] <= 3600, 'bounded finite times required')
    criteria = plan['criteria']
    demand(isinstance(criteria, list) and 0 < len(criteria) <= 64, 'bounded original acceptance required')
    for row in criteria:
        demand(isinstance(row, dict) and set(row) == {'id', 'kind'}
               and isinstance(row['id'], str) and row['id'].strip()
               and row['kind'] in {'tests', 'behavior', 'artifact', 'handoff'}, 'named acceptance criterion required')
    ids = [r['id'] for r in criteria]
    findings.names(ids); findings.names(plan['operation_ids'])
    demand({'tests', 'behavior', 'handoff'} <= {r['kind'] for r in criteria}, 'tests, behavior and handoff obligations must be explicit')
    plan = deepcopy(plan)
    kinds = {r['id']: r['kind'] for r in plan['criteria']}
    started = last_at = clock()
    demand(finite(started), 'finite clock required')
    deadline = min(started + plan['budget_seconds'], plan['deadline'])
    state = {'goal_id': plan['goal_id'], 'status': 'PARTIAL', 'goal_met': False, 'required': ids,
             'required_operations': list(plan['operation_ids']),
             'missing_criteria': list(ids), 'missing_operations': list(plan['operation_ids']),
             'unresolved_findings': [], 'checks': {}, 'operations': {}, 'finding_ledger': None,
             'context': None, 'history': [], 'rounds_used': 0, 'started_at': started, 'deadline': deadline, 'elapsed': 0,
             'reason': 'NOT_STARTED', 'next_phase': 'reproduce'}
    seen = set()

    def now():
        nonlocal last_at
        value = clock()
        demand(finite(value) and value >= last_at, 'clock moved backwards')
        last_at = value
        state['elapsed'] = value - started
        return value

    for round_number in range(1, plan['max_rounds'] + 1):
        if now() >= deadline:
            state.update(status='BUDGET_EXHAUSTED', reason='DEADLINE')
            break
        state['rounds_used'] = round_number
        request = {'goal': deepcopy(plan), 'round': round_number, 'resume_phase': state['next_phase'],
                   'missing_criteria': list(state['missing_criteria']),
                   'unresolved_findings': list(state['unresolved_findings']),
                   'operations': deepcopy(state['operations']), 'remaining_seconds': deadline - now()}
        try:
            packet = workflow(request)
            demand(isinstance(packet, dict) and set(packet) == {'context', 'finding_ledger', 'checks', 'operations', 'next_phase'}, 'exact Workflow packet required')
            findings.context(packet['context'])
            demand(all(packet['context'][key] == plan[key] for key in ('requirements_id', 'rules_id')), 'original acceptance or rules changed')
            demand(packet['next_phase'] in {'repair', 'verify', 'observe', 'handoff', 'none'}, 'unknown recovery phase')
            ledger, unresolved = _ledger(state['finding_ledger'], packet['finding_ledger'], packet['context'])
            checks, operations = deepcopy(state['checks']), deepcopy(state['operations'])
            for receipt in checks.values():
                if receipt['context'] != packet['context'] and receipt['status'] != 'STALE':
                    receipt['previous_status'] = receipt['status']
                    receipt['status'] = 'STALE'
            demand(isinstance(packet['checks'], list) and isinstance(packet['operations'], list), 'receipt lists required')
            demand(len(packet['checks']) <= len(ids) and len(packet['operations']) <= len(plan['operation_ids']), 'unbounded receipt set')
            packet_ids = []
            for receipt in packet['checks']:
                demand(isinstance(receipt, dict) and set(receipt) == {'criterion_id', 'kind', 'context', 'status', 'evidence_id', 'artifact_sha256', 'observed_at'}, 'exact acceptance receipt required')
                ident = receipt['criterion_id']
                demand(ident in kinds and receipt['kind'] == kinds[ident], 'receipt outside original acceptance')
                findings.context(receipt['context']); findings.identity(receipt['artifact_sha256'])
                demand(receipt['context'] == packet['context'] and receipt['status'] in {'PASSED', 'FAILED', 'UNKNOWN'}, 'stale or invalid receipt')
                demand(isinstance(receipt['evidence_id'], str) and bool(receipt['evidence_id'])
                       and finite(receipt['observed_at']) and plan['not_before'] <= receipt['observed_at'] <= now(), 'evidence identity/time required')
                packet_ids.append(ident)
                checks[ident] = deepcopy(receipt)
            findings.names(packet_ids)
            operation_ids = []
            for operation in packet['operations']:
                demand(isinstance(operation, dict) and set(operation) == {'operation_id', 'status', 'handle', 'artifact_sha256'}, 'exact operation observation required')
                ident = operation['operation_id']
                demand(ident in plan['operation_ids'] and operation['status'] in {'SUCCEEDED', 'FAILED_CONFIRMED', 'UNKNOWN'}, 'unadmitted operation observation')
                demand(operation['handle'] is None or isinstance(operation['handle'], str) and bool(operation['handle']), 'invalid operation handle')
                if operation['artifact_sha256'] is not None:
                    findings.identity(operation['artifact_sha256'])
                if operation['status'] == 'SUCCEEDED':
                    demand(operation['handle'] is not None and operation['artifact_sha256'] is not None, 'successful operation needs actual receipt')
                if ident in operations:
                    old = operations[ident]
                    demand(old['handle'] == operation['handle'], 'original operation handle changed')
                    demand(old['status'] != 'SUCCEEDED' or old == operation, 'accepted side effect overwritten')
                operations[ident] = deepcopy(operation)
                operation_ids.append(ident)
            findings.names(operation_ids)
        except Exception:
            state.update(status='PARTIAL', reason='INVALID_OR_UNAVAILABLE_WORKFLOW_RESULT')
            break
        state['history'].append(deepcopy(packet))
        if now() > deadline:
            state.update(status='BUDGET_EXHAUSTED', reason='LATE_WORKFLOW_RESULT')
            break
        state.update(context=deepcopy(packet['context']), finding_ledger=ledger, checks=checks,
                     operations=operations, unresolved_findings=unresolved, next_phase=packet['next_phase'])
        state['missing_criteria'] = sorted(ident for ident in ids if ident not in checks
            or checks[ident]['status'] != 'PASSED' or checks[ident]['context'] != state['context'])
        state['missing_operations'] = sorted(ident for ident in plan['operation_ids']
            if ident not in operations or operations[ident]['status'] != 'SUCCEEDED')
        if any(o['status'] == 'UNKNOWN' for o in operations.values()):
            state.update(status='HOLD', reason='UNKNOWN_SIDE_EFFECT')
            break
        if not state['missing_criteria'] and not unresolved and not state['missing_operations']:
            state.update(status='COMPLETE', goal_met=True, reason='ALL_ORIGINAL_OBLIGATIONS_MET')
            break
        material = {'context': state['context'], 'checks': {key: {k: r[k] for k in
            ('status', 'context', 'artifact_sha256')} for key, r in checks.items()},
            'findings': {key: row['status'] for key, row in ledger['findings'].items()}, 'operations': operations}
        fingerprint = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        if fingerprint in seen:
            state.update(status='NO_PROGRESS', reason='NO_NEW_GOAL_EVIDENCE')
            break
        seen.add(fingerprint)
        if packet['next_phase'] == 'none':
            state.update(status='PARTIAL', reason='NO_EFFECTIVE_NEXT_PHASE')
            break
    else:
        state.update(status='BUDGET_EXHAUSTED', reason='ROUND_LIMIT')
    now()
    return state
