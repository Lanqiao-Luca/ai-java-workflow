"""Mutate copies of the published receipt; no models, Maven or network are invoked."""
from pathlib import Path
import hashlib
import json
import runpy
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(ROOT / 'scripts/check_native_cases.py'))['check_native_case']
CASE = ROOT / 'examples/native-spring-workflow'


class PublishedNativeCaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.case = Path(self.temporary.name) / CASE.name
        shutil.copytree(CASE, self.case)
        self.runtime_path = self.case / 'evidence/runtime.json'
        self.runtime = json.loads(self.runtime_path.read_text())

    def seal(self):
        self.runtime_path.write_text(json.dumps(self.runtime, indent=2) + '\n')
        rows = [{'path': p.relative_to(self.case).as_posix(),
                 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted(self.case.rglob('*')) if p.is_file() and p.name != 'artifact-manifest.json']
        (self.case / 'artifact-manifest.json').write_text(json.dumps({'files': rows}, indent=2) + '\n')

    def rejected(self):
        self.seal()
        with self.assertRaises(ValueError):
            CHECK(self.case)

    def test_published_control_accepted(self):
        CHECK(self.case)

    def test_substitute_role_rejected(self):
        self.runtime['stages']['implementation']['native']['role'] = 'default'
        self.rejected()

    def test_missing_actual_completion_rejected(self):
        self.runtime['stages']['verification']['native']['native_completed'] = False
        self.rejected()

    def test_stale_review_document_rejected_even_when_its_recorded_hash_matches(self):
        path = self.case / 'final/code-review.md'
        data = path.read_bytes().split(b'\n', 1)
        path.write_bytes(b'candidate_id: ' + b'0' * 64 + b'\n' + data[1])
        original = path.read_bytes().replace(b'../../../', b'catalog/')
        changed_native = hashlib.sha256(original).hexdigest()
        self.runtime['stages']['code_review']['outputs_sha256']['code-review.md'] = changed_native
        declaration = json.loads((self.case / 'case.json').read_text())
        declaration['public_document_abstracts']['code-review.md'].update(
            native_sha256=changed_native, public_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        (self.case / 'case.json').write_text(json.dumps(declaration, indent=2) + '\n')
        self.rejected()

    def test_stale_host_validation_rejected(self):
        validation = self.runtime['validation']
        validation['candidate_id'] = '0' * 64
        (self.case / 'final/validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        self.rejected()

    def test_skipped_test_cannot_be_claimed_passed(self):
        validation = self.runtime['validation']
        validation['skipped'] = [validation['test_names'][0]]
        (self.case / 'final/validation.json').write_text(json.dumps(validation, indent=2) + '\n')
        self.rejected()

    def test_source_changed_after_verification_rejected(self):
        path = self.case / 'final/app/src/main/java/example/nativeflow/LabelService.java'
        path.write_bytes(path.read_bytes() + b'\n// synthetic post-verification drift\n')
        self.rejected()

    def test_sequential_reviews_cannot_claim_overlap(self):
        a = self.runtime['stages']['code_review']
        b = self.runtime['stages']['principle_review']
        b['started'], b['ended'] = a['ended'] + 1, a['ended'] + 20
        delivery = self.runtime['stages']['delivery']
        delivery['started'], delivery['ended'] = b['ended'] + 1, b['ended'] + 20
        self.rejected()

    def test_additional_session_carrier_rejected_even_in_manifest(self):
        (self.case / 'raw.log').write_text('independent synthetic session carrier')
        self.rejected()

    def test_model_source_map_cannot_omit_consumed_method(self):
        name = next(n for n in self.runtime['source_sha256'] if n.startswith('standards/'))
        del self.runtime['source_sha256'][name]
        self.rejected()

    def test_historical_method_identity_cannot_be_replaced(self):
        self.runtime['source_sha256']['standards/layering.md'] = '0' * 64
        self.rejected()

    def test_new_coordinator_cannot_be_claimed_in_historical_run(self):
        name = 'agents/task-coordinator.md'
        self.runtime['source_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        self.rejected()

    def test_public_abstract_cannot_exempt_java_source(self):
        path = self.case / 'case.json'
        declaration = json.loads(path.read_text())
        declaration['public_document_abstracts']['app/src/main/java/example/nativeflow/LabelService.java'] = {
            'kind': 'independent_public_summary', 'native_sha256': '0' * 64, 'public_sha256': '0' * 64}
        path.write_text(json.dumps(declaration, indent=2) + '\n')
        self.rejected()

    def test_abstract_must_bind_actual_native_output_identity(self):
        path = self.case / 'case.json'
        declaration = json.loads(path.read_text())
        declaration['public_document_abstracts']['code-review.md']['native_sha256'] = '0' * 64
        path.write_text(json.dumps(declaration, indent=2) + '\n')
        self.rejected()

    def test_seed_cannot_contain_prebuilt_java_solution(self):
        path = self.case / 'seed/app/src/main/java/example/nativeflow/Hidden.java'
        path.parent.mkdir(parents=True)
        path.write_text('class Hidden {}')
        self.rejected()

    def test_unknown_case_kind_rejected(self):
        path = self.case / 'case.json'
        declaration = json.loads(path.read_text())
        declaration['kind'] = 'unknown_native_case'
        path.write_text(json.dumps(declaration, indent=2) + '\n')
        self.rejected()


if __name__ == '__main__':
    unittest.main()
