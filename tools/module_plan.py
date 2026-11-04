"""Validate declared module ownership and dependencies; never authorizes implementation."""
from pathlib import Path, PurePosixPath
import argparse
import json
import re


class PlanError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise PlanError(message)


def shape(value, keys, label):
    need(isinstance(value, dict) and set(value) == set(keys.split()), label + ': invalid fields')


def ident(value):
    need(isinstance(value, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', value), 'invalid identity')
    return value


def names(value):
    need(isinstance(value, list), 'expected identity list')
    for item in value:
        ident(item)
    need(len(value) == len(set(value)), 'duplicate identity')
    return value


def digest(value):
    need(isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value), 'invalid SHA256')
    return value


def text(value):
    need(isinstance(value, str) and bool(value.strip()), 'empty statement')


def file_path(value):
    need(isinstance(value, str) and value and not any(c in value for c in '\\:*?[]\x00\n\r'), 'invalid file path')
    path = PurePosixPath(value)
    need(not path.is_absolute() and path.as_posix() == value
         and all(part not in {'.', '..'} for part in value.split('/')), 'unsafe file path')
    return value


def validate_plan(plan, contract):
    """Contract is an independently supplied design boundary, not inferred from plan."""
    shape(contract, 'design_id revision sha256 active_requirements repositories cohesion_groups', 'contract')
    shape(plan, 'design_id design_revision design_sha256 modules shared_files', 'plan')
    ident(contract['design_id'])
    need(type(contract['revision']) is int and contract['revision'] > 0, 'invalid design revision')
    digest(contract['sha256'])
    required = set(names(contract['active_requirements']))
    need(required, 'empty active requirement set')
    need(plan['design_id'] == contract['design_id'] and type(plan['design_revision']) is int
         and plan['design_revision'] == contract['revision']
         and plan['design_sha256'] == contract['sha256'], 'stale design binding')
    need(isinstance(contract['repositories'], list) and contract['repositories'], 'missing repositories')
    repos = {}
    for repo in contract['repositories']:
        shape(repo, 'id baseline_sha256', 'repository')
        key = ident(repo['id'])
        need(key not in repos, 'duplicate repository')
        repos[key] = digest(repo['baseline_sha256'])
    need(isinstance(plan['modules'], list) and plan['modules'], 'missing modules')
    modules, owners, writers = {}, {}, []
    for module in plan['modules']:
        shape(module, 'id repo baseline_sha256 purpose requirements writes depends_on acceptance', 'module')
        key = ident(module['id'])
        need(key not in modules, 'duplicate module')
        ident(module['repo'])
        need(module['repo'] in repos and module['baseline_sha256'] == repos[module['repo']], 'repository or baseline mismatch')
        text(module['purpose'])
        names(module['requirements'])
        names(module['depends_on'])
        need(isinstance(module['acceptance'], list) and module['acceptance'], 'missing module acceptance')
        for item in module['acceptance']:
            text(item)
        need(isinstance(module['writes'], list) and module['writes'], 'missing exact write set')
        for name in module['writes']:
            file_path(name)
            for repo, path, _ in writers:
                if repo == module['repo']:
                    need(not (name == path or name.startswith(path + '/') or path.startswith(name + '/')), 'overlapping writes')
            writers.append((module['repo'], name, key))
        for requirement in module['requirements']:
            need(requirement in required and requirement not in owners, 'unknown or multiply owned requirement')
            owners[requirement] = key
        modules[key] = module
    need(set(owners) == required, 'unowned active requirement')
    for key, module in modules.items():
        need(key not in module['depends_on'] and set(module['depends_on']) <= set(modules), 'invalid dependency')
    closures, visiting = {}, set()

    def ancestors(key):
        if key in closures:
            return closures[key]
        need(key not in visiting, 'dependency cycle')
        visiting.add(key)
        result = set()
        for parent in modules[key]['depends_on']:
            result.add(parent)
            result.update(ancestors(parent))
        visiting.remove(key)
        closures[key] = result
        return result

    for key in modules:
        ancestors(key)
    need(isinstance(contract['cohesion_groups'], list), 'invalid cohesion groups')
    group_ids = set()
    for group in contract['cohesion_groups']:
        shape(group, 'id requirements', 'cohesion group')
        ident(group['id'])
        need(group['id'] not in group_ids, 'duplicate cohesion group')
        group_ids.add(group['id'])
        ids = set(names(group['requirements']))
        need(ids and ids <= required, 'invalid cohesion requirement')
        need(len({owners[item] for item in ids}) == 1, 'indivisible design boundary split across modules')
    need(isinstance(plan['shared_files'], list), 'invalid shared files')
    shared_seen = set()
    for shared in plan['shared_files']:
        shape(shared, 'repo path owner consumers', 'shared file')
        file_path(shared['path'])
        ident(shared['repo'])
        ident(shared['owner'])
        key = (shared['repo'], shared['path'])
        need(key not in shared_seen and shared['repo'] in repos, 'duplicate or unknown shared file')
        shared_seen.add(key)
        need(shared['owner'] in modules, 'unknown shared owner')
        owner = modules[shared['owner']]
        need(owner['repo'] == shared['repo'] and shared['path'] in owner['writes'], 'shared owner does not own file')
        consumers = names(shared['consumers'])
        need(consumers and set(consumers) <= set(modules) and shared['owner'] not in consumers, 'invalid shared consumers')
        need(all(shared['owner'] in closures[item] for item in consumers), 'consumer lacks owner dependency')
    return {'status': 'STRUCTURE_VALID', 'design_id': contract['design_id'],
            'module_count': len(modules), 'requirement_count': len(required), 'execution': 'not_started'}


def load_json(path):
    def unique(pairs):
        data = {}
        for key, value in pairs:
            need(key not in data, 'duplicate JSON key')
            data[key] = value
        return data
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate_plan(load_json(args.plan), load_json(args.contract))
    except (PlanError, ValueError, OSError, TypeError, KeyError):
        print(json.dumps({'status': 'REJECTED', 'execution': 'not_started'}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
