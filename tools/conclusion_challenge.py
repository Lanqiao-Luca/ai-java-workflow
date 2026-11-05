"""Validate a supplied challenge report, never its truth or permission to act."""
import re


class ChallengeError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ChallengeError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def fields(value, names, label):
    need(isinstance(value, dict) and set(value) == set(names.split()), label)


def rows(value, label):
    need(isinstance(value, list) and bool(value), label)


def identifiers(items, names, label):
    rows(items, label)
    seen = set()
    for item in items:
        fields(item, names, label + ' fields')
        need(text(item['id']) and item['id'] not in seen, label + ' identity')
        seen.add(item['id'])
    return seen


def references(value, known, label, required=True):
    need(isinstance(value, list), label)
    need(all(text(v) and v in known for v in value), label)
    need(len(value) == len(set(value)) and (bool(value) or not required), label)


def check(report, candidate_sha256):
    """Caller supplies independently computed current candidate digest.

    Group labels and all reasoning remain declarations. Missing probes can be
    recorded validly, but can never become evidence merely by passing this check.
    """
    fields(report, 'candidate_sha256 scope claim preferred hypotheses evidence matrix probes sensitivity conclusion', 'report fields')
    need(isinstance(candidate_sha256, str) and re.fullmatch(r'[0-9a-f]{64}', candidate_sha256) is not None,
         'current candidate digest')
    need(report['candidate_sha256'] == candidate_sha256, 'candidate drift')
    need(all(text(report[k]) for k in ('scope', 'claim', 'preferred', 'conclusion')), 'report context')
    hypotheses = identifiers(report['hypotheses'], 'id explanation', 'hypotheses')
    need(len(hypotheses) >= 2 and report['preferred'] in hypotheses, 'competing explanations')
    explanations = [h['explanation'] for h in report['hypotheses']]
    need(all(text(v) for v in explanations), 'hypothesis explanation')
    need(len({v.strip().casefold() for v in explanations}) == len(explanations), 'duplicate explanation')

    evidence = identifiers(report['evidence'], 'id source_group locator observation limits critical', 'evidence')
    critical, groups = set(), set()
    for item in report['evidence']:
        need(all(text(item[k]) for k in ('source_group', 'locator', 'observation', 'limits')), 'evidence provenance')
        need(type(item['critical']) is bool, 'critical flag')
        groups.add(item['source_group'])
        if item['critical']:
            critical.add(item['id'])

    rows(report['matrix'], 'matrix')
    cells = set()
    for cell in report['matrix']:
        fields(cell, 'evidence hypothesis effect rationale', 'matrix fields')
        need(text(cell['evidence']) and cell['evidence'] in evidence
             and text(cell['hypothesis']) and cell['hypothesis'] in hypotheses, 'matrix reference')
        pair = (cell['evidence'], cell['hypothesis'])
        need(pair not in cells, 'duplicate matrix cell')
        cells.add(pair)
        need(isinstance(cell['effect'], str) and cell['effect'] in {'support', 'oppose', 'neutral', 'strong_oppose'}
             and text(cell['rationale']), 'matrix assessment')
    need(cells == {(e, h) for e in evidence for h in hypotheses}, 'incomplete matrix')

    identifiers(report['probes'], 'id hypothesis counterexample state evidence result', 'probes')
    pending = []
    for probe in report['probes']:
        need(text(probe['hypothesis']) and probe['hypothesis'] in hypotheses
             and text(probe['counterexample']) and text(probe['result']), 'probe context')
        need(isinstance(probe['state'], str) and probe['state'] in {'DONE', 'NOT_RUN', 'UNAVAILABLE'}, 'probe state')
        references(probe['evidence'], evidence, 'probe evidence', required=probe['state'] == 'DONE')
        if probe['state'] != 'DONE':
            need(not probe['evidence'], 'unexecuted probe cannot claim evidence')
            pending.append(probe['id'])
    need(any(p['hypothesis'] == report['preferred'] for p in report['probes']), 'preferred hypothesis unchallenged')

    need(isinstance(report['sensitivity'], list), 'sensitivity')
    exclusions = set()
    for item in report['sensitivity']:
        fields(item, 'without effect rationale', 'sensitivity fields')
        need(text(item['without']) and item['without'] in critical and item['without'] not in exclusions,
             'sensitivity critical reference')
        exclusions.add(item['without'])
        need(isinstance(item['effect'], str) and item['effect'] in {'changed', 'unchanged', 'unknown'}
             and text(item['rationale']), 'sensitivity assessment')
    need(exclusions == critical, 'missing critical evidence sensitivity')

    return {'status': 'STRUCTURE_VALID', 'candidate_sha256': candidate_sha256,
            'hypotheses': len(hypotheses), 'evidence_items': len(evidence),
            'declared_source_groups': len(groups), 'pending_checks': pending,
            'semantic_acceptance': 'NOT_ASSESSED', 'action_authorization': 'NOT_ASSESSED'}
