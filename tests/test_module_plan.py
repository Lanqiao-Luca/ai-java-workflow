"""Exercise module ownership, independent design binding and no-execution boundaries."""
from copy import deepcopy
from pathlib import Path
import json
import runpy
import subprocess
import sys
import tempfile
import unittest

from tools.module_plan import PlanError, load_json, validate_plan

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'workflows/examples/design-to-modules'


class ModulePlanTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_json(CASE / 'contract.json')
        self.plan = load_json(CASE / 'plan.json')

    def rejected(self):
        with self.assertRaises(PlanError):
            validate_plan(self.plan, self.contract)

    def test_complete_plan_is_structure_only_and_does_not_execute(self):
        result = validate_plan(self.plan, self.contract)
        self.assertEqual(result['status'], 'STRUCTURE_VALID')
        self.assertEqual(result['execution'], 'not_started')
        self.assertEqual(result['requirement_count'], 5)

    def test_missing_requirement_rejected(self):
        self.plan['modules'][-1]['requirements'] = []
        self.rejected()

    def test_duplicate_or_unknown_requirement_rejected(self):
        for requirement in ['R1', 'R99']:
            with self.subTest(requirement=requirement):
                self.setUp()
                self.plan['modules'][-1]['requirements'].append(requirement)
                self.rejected()

    def test_design_sha_or_revision_drift_rejected(self):
        for field, value in [('design_sha256', '0' * 64), ('design_revision', 1), ('design_revision', True)]:
            with self.subTest(field=field, value=value):
                self.setUp()
                self.plan[field] = value
                self.rejected()

    def test_baseline_drift_rejected(self):
        self.plan['modules'][1]['baseline_sha256'] = '0' * 64
        self.rejected()

    def test_file_or_parent_child_write_conflict_rejected(self):
        for path in ['src/demo/BookmarkValue.java', 'src/demo']:
            with self.subTest(path=path):
                self.setUp()
                self.plan['modules'][1]['writes'] = [path]
                self.rejected()

    def test_indivisible_requirement_group_cannot_be_split(self):
        self.plan['modules'][2]['requirements'].remove('R4')
        self.plan['modules'][1]['requirements'].append('R4')
        self.rejected()

    def test_shared_file_owner_and_dependency_are_required(self):
        for mutation in ['wrong_owner', 'missing_dependency']:
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == 'wrong_owner':
                    self.plan['shared_files'][0]['owner'] = 'rename'
                else:
                    self.plan['modules'][1]['depends_on'] = []
                self.rejected()

    def test_transitive_shared_owner_dependency_is_supported(self):
        self.plan['shared_files'][0]['consumers'].append('integration')
        self.assertEqual(validate_plan(self.plan, self.contract)['status'], 'STRUCTURE_VALID')

    def test_cycles_and_missing_dependencies_rejected(self):
        for parent in ['integration', 'unknown']:
            with self.subTest(parent=parent):
                self.setUp()
                self.plan['modules'][0]['depends_on'] = [parent]
                self.rejected()

    def test_unsafe_and_pattern_write_sets_are_rejected(self):
        for path in ['../outside.java', '/outside.java', 'src/*.java', 'src/./A.java', 'src//A.java', 'C:\\A.java']:
            with self.subTest(path=path):
                self.setUp()
                self.plan['modules'][1]['writes'] = [path]
                self.rejected()

    def test_unreviewed_extra_fields_cannot_claim_authorization(self):
        self.plan['implementation_authorized'] = True
        self.rejected()

    def test_input_contract_is_independent_of_module_plan(self):
        # Changing the plan cannot silently remove the original coverage obligation.
        self.plan['modules'][-1]['requirements'] = []
        self.assertIn('R5', self.contract['active_requirements'])
        self.rejected()

    def test_case_program_checks_bindings_and_preserves_negative_outcomes(self):
        result = runpy.run_path(str(CASE / 'run.py'))['run_examples']()
        self.assertEqual(set(result['negative'].values()), {'REJECTED'})
        self.assertEqual(result['implementation'], 'NOT_RUN')
        self.assertEqual(result['professional_review'], 'author_walkthrough_only')

    def test_duplicate_json_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'duplicate.json'
            path.write_text('{"design_id":"a","design_id":"b"}')
            with self.assertRaises(PlanError):
                load_json(path)

    def test_cli_exit_status_distinguishes_valid_and_rejected_plan(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/module_plan.py'), '--contract', str(CASE / 'contract.json')]
        good = subprocess.run(cli + ['--plan', str(CASE / 'plan.json')], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)['execution'], 'not_started')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.json'
            path.write_text('{}')
            bad = subprocess.run(cli + ['--plan', str(path)], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertEqual(json.loads(bad.stdout)['status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main()
