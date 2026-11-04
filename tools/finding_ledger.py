"""Candidate-bound finding lifecycle. Pure data operations; no execution or storage.

Callers supply real receipt identities and persist the returned value. A repaired
claim is never closure; verification and both independent reviews must name it.
"""
from copy import deepcopy
import hashlib
import json
import re

BINDINGS = {'candidate_id', 'requirements_id', 'rules_id'}
CHECKS = {'verification', 'code_review', 'principle_review'}


def demand(condition, message):
    if not condition:
        raise ValueError('finding ledger: ' + message)


def identity(value):
    demand(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'SHA256 required')


def context(value):
    demand(isinstance(value, dict) and set(value) == BINDINGS, 'complete context required')
    for item in value.values():
        identity(item)


def names(values):
    demand(isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values)
           and len(values) == len(set(values)), 'unique named references required')


def create(bindings):
    context(bindings)
    return {'version': 1, 'context': dict(bindings), 'findings': {}, 'evidence': {}, 'events': []}


def current(ledger, receipt):
    return (receipt['status'] != 'STALE'
            and all(receipt['context'][key] == ledger['context'][key] for key in receipt['depends_on']))


def add_evidence(ledger, receipt):
    required = {'id', 'kind', 'actor', 'context', 'artifact_sha256', 'status', 'depends_on', 'checked_findings'}
    demand(isinstance(receipt, dict) and set(receipt) == required, 'exact evidence contract required')
    context(receipt['context'])
    identity(receipt['artifact_sha256'])
    names(receipt['depends_on']); names(receipt['checked_findings'])
    demand(set(receipt['depends_on']) == BINDINGS, 'all correctness inputs must be bound')
    demand(receipt['kind'] in CHECKS | {'repair'} and receipt['status'] in {'PASSED', 'FAILED'}, 'invalid evidence kind/status')
    demand(all(isinstance(receipt[key], str) and receipt[key].strip() for key in ('id', 'actor')), 'evidence identity/actor required')
    demand(receipt['id'] not in ledger['evidence'], 'evidence identity reused')
    demand(set(receipt['checked_findings']) <= set(ledger['findings']), 'unknown checked finding')
    demand(receipt['context'] == ledger['context'], 'evidence uses stale context')
    result = deepcopy(ledger)
    result['evidence'][receipt['id']] = deepcopy(receipt)
    result['events'].append({'action': 'EVIDENCE', 'evidence_id': receipt['id']})
    return result


def observe(ledger, evidence_id, findings):
    demand(evidence_id in ledger['evidence'], 'missing failure evidence')
    evidence = ledger['evidence'][evidence_id]
    demand(evidence['kind'] in CHECKS and evidence['status'] == 'FAILED' and current(ledger, evidence), 'current failed check required')
    demand(isinstance(findings, list) and bool(findings), 'concrete findings required')
    result = deepcopy(ledger)
    observed = set()
    for item in findings:
        demand(isinstance(item, dict) and set(item) == {'finding_id', 'key', 'summary', 'location', 'criterion'}, 'exact finding contract required')
        demand(all(isinstance(item[k], str) and item[k].strip() and len(item[k]) <= 2000
                   for k in ('key', 'summary', 'location', 'criterion')), 'bounded concrete finding fields required')
        key = json.dumps([evidence['kind'], item['key']], separators=(',', ':'))
        ident = 'F-' + hashlib.sha256(key.encode()).hexdigest()[:16]
        if item['finding_id'] is not None:
            demand(isinstance(item['finding_id'], str) and item['finding_id'] in result['findings'], 'unknown finding identity')
            ident = item['finding_id']
            demand(result['findings'][ident]['key'] == item['key'], 'finding semantic key changed')
        demand(ident not in observed, 'duplicate finding in report')
        observed.add(ident)
        if ident not in result['findings']:
            result['findings'][ident] = {'id': ident, 'key': item['key'], 'origin_stage': evidence['kind'],
                'summary': item['summary'], 'location': item['location'], 'criterion': item['criterion'],
                'opened_context': deepcopy(evidence['context']), 'observations': [],
                'status': 'OPEN', 'repair_evidence': None, 'closure_evidence': []}
        finding = result['findings'][ident]
        demand(finding['location'] == item['location'] and finding['criterion'] == item['criterion'], 'finding key reused for different issue')
        finding.update(status='OPEN', repair_evidence=None, closure_evidence=[])
        finding['observations'].append(evidence_id)
        result['events'].append({'action': 'OPEN', 'finding_id': ident, 'evidence_id': evidence_id})
    return result


def invalidate(ledger, bindings):
    context(bindings)
    result = deepcopy(ledger)
    changed = sorted(k for k in BINDINGS if result['context'][k] != bindings[k])
    result['context'] = dict(bindings)
    if not changed:
        return result
    stale = []
    for ident, receipt in result['evidence'].items():
        if not current(result, receipt) and receipt['status'] != 'STALE':
            receipt['previous_status'] = receipt['status']
            receipt['status'] = 'STALE'
            receipt['invalidated_by'] = changed
            stale.append(ident)
    for finding in result['findings'].values():
        proofs = finding['closure_evidence'] + ([finding['repair_evidence']] if finding['repair_evidence'] else [])
        if set(proofs) & set(stale):
            finding.update(status='OPEN', repair_evidence=None, closure_evidence=[])
            result['events'].append({'action': 'REOPEN', 'finding_id': finding['id'], 'changed': changed})
    result['events'].append({'action': 'INVALIDATE', 'changed': changed, 'evidence_ids': sorted(stale)})
    return result


def mark_repaired(ledger, finding_ids, evidence_id):
    names(finding_ids)
    demand(bool(finding_ids) and set(finding_ids) <= set(ledger['findings']), 'known repair targets required')
    evidence = ledger['evidence'].get(evidence_id)
    demand(evidence is not None and evidence['kind'] == 'repair' and evidence['status'] == 'PASSED'
           and current(ledger, evidence), 'current repair receipt required')
    demand(set(finding_ids) == set(evidence['checked_findings']), 'repair targets do not match receipt')
    result = deepcopy(ledger)
    for ident in finding_ids:
        demand(result['findings'][ident]['status'] != 'CLOSED', 'closed issue needs new observation before repair')
        result['findings'][ident].update(status='REPAIRED', repair_evidence=evidence_id, closure_evidence=[])
        result['events'].append({'action': 'REPAIRED', 'finding_id': ident, 'evidence_id': evidence_id})
    return result


def close(ledger, finding_id, evidence_ids):
    names(evidence_ids)
    demand(finding_id in ledger['findings'], 'unknown finding')
    finding = ledger['findings'][finding_id]
    demand(finding['status'] == 'REPAIRED', 'author repair claim required before closure')
    repair = ledger['evidence'][finding['repair_evidence']]
    demand(current(ledger, repair), 'stale repair')
    receipts = [ledger['evidence'].get(ident) for ident in evidence_ids]
    demand(len(receipts) == len(CHECKS) and all(r is not None for r in receipts), 'three independent checks required')
    demand({r['kind'] for r in receipts} == CHECKS, 'verification and both reviews required')
    demand(len({r['actor'] for r in receipts} | {repair['actor']}) == 4, 'independent execution contexts required')
    order = list(ledger['evidence'])
    demand(all(order.index(r['id']) > order.index(repair['id']) for r in receipts), 'checks must follow the repair receipt')
    demand(all(r['status'] == 'PASSED' and current(ledger, r) and finding_id in r['checked_findings']
               for r in receipts), 'each current check must explicitly recheck this finding')
    result = deepcopy(ledger)
    result['findings'][finding_id].update(status='CLOSED', closure_evidence=list(evidence_ids))
    result['events'].append({'action': 'CLOSED', 'finding_id': finding_id, 'evidence_ids': list(evidence_ids)})
    return result


def unresolved(ledger):
    return sorted(ident for ident, finding in ledger['findings'].items() if finding['status'] != 'CLOSED')
