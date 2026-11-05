"""Check the new case receipt identities; never substitutes for a Java rerun."""
from pathlib import Path
import hashlib
import json
import runpy


def check_design_spring_case(folder):
    folder = Path(folder).resolve()
    declaration = json.loads((folder / 'case.json').read_text())
    if declaration != {'kind': 'design_spring_case', 'case_id': folder.name, 'synthetic': True}:
        raise ValueError('case declaration')
    paths = list(folder.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('case symlink')
    actual = {p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    manifest = json.loads((folder / 'artifact-manifest.json').read_text())['files']
    if len(manifest) != len({r['path'] for r in manifest}) or {r['path'] for r in manifest} != actual - {'artifact-manifest.json'}:
        raise ValueError('case file set drift')
    for row in manifest:
        path = (folder / row['path']).resolve()
        if not path.is_relative_to(folder) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('case artifact drift')
    runner = runpy.run_path(str(folder / 'run.py'))
    hashes = runner['source_hashes']()
    for name in ('result.json', 'independent-result.json'):
        result = json.loads((folder / name).read_text())
        if (result['source_sha256'] != hashes or result['candidate_id'] != runner['candidate_id'](hashes)
                or result['runner_sha256'] != hashlib.sha256((folder / 'run.py').read_bytes()).hexdigest()
                or result['status'] != 'PASSED' or [v['variant'] for v in result['variants']] != ['red', 'green']):
            raise ValueError('runtime receipt drift')
        for variant in result['variants']:
            expected_failures = runner['RED_FAILURES'] if variant['variant'] == 'red' else set()
            if (variant['tests'] != len(runner['TESTS']) or set(variant['test_names']) != runner['TESTS']
                    or len(variant['test_names']) != len(runner['TESTS'])
                    or set(variant['failures']) != expected_failures or variant['errors'] or variant['skipped']
                    or not variant['accepted'] or variant['process_exit'] != (1 if expected_failures else 0)):
                raise ValueError('runtime test declaration')
            for source, digest in variant['compiled_source_sha256'].items():
                path = folder / ('fixtures/ReadingListService-red.java.txt' if variant['variant'] == 'red'
                                 and source == runner['SERVICE'] else 'app/' + source)
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError('compiled variant drift')
    review = json.loads((folder / 'implementation-review.json').read_text())
    if (review['candidate_id'] != runner['candidate_id'](hashes) or review['source_sha256'] != hashes
            or review['verdict'] != 'IMPLEMENTATION_ACCEPTED_WITHIN_SCOPE' or review['findings']):
        raise ValueError('independent review drift')
