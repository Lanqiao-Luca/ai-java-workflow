"""Independent lifecycle/counterexample inputs; no model or business actions."""
from copy import deepcopy
import unittest

from tools.finding_ledger import add_evidence, close, create, invalidate, mark_repaired, observe, unresolved


class FindingTests(unittest.TestCase):
    def setUp(self):
        self.context = {'candidate_id': 'a' * 64, 'requirements_id': 'b' * 64, 'rules_id': 'c' * 64}
        self.ledger = create(self.context)

    def receipt(self, ident, kind, *, status='PASSED', checked=None, actor=None):
        return {'id': ident, 'kind': kind, 'actor': actor or ident, 'status': status,
                'context': dict(self.ledger['context']), 'artifact_sha256': 'd' * 64,
                'depends_on': sorted(self.context), 'checked_findings': checked or []}

    def open_issue(self):
        self.ledger = add_evidence(self.ledger, self.receipt('failed', 'code_review', status='FAILED'))
        self.item = {'finding_id': None, 'key': 'reject-blank', 'summary': 'Blank labels accepted',
                     'location': 'LabelService.normalize', 'criterion': 'Reject blank input'}
        self.ledger = observe(self.ledger, 'failed', [self.item])
        return next(iter(self.ledger['findings']))

    def repaired(self):
        ident = self.open_issue()
        changed = {**self.context, 'candidate_id': 'e' * 64}
        self.ledger = invalidate(self.ledger, changed)
        self.ledger = add_evidence(self.ledger, self.receipt('repair', 'repair', checked=[ident]))
        self.ledger = mark_repaired(self.ledger, [ident], 'repair')
        return ident

    def checks(self, ident):
        for stage in ['verification', 'code_review', 'principle_review']:
            self.ledger = add_evidence(self.ledger, self.receipt(stage, stage, checked=[ident]))
        return ['verification', 'code_review', 'principle_review']

    def test_complete_trace_and_original_failure_retained(self):
        ident = self.repaired()
        checks = self.checks(ident)
        self.ledger = close(self.ledger, ident, checks)
        self.assertEqual(unresolved(self.ledger), [])
        self.assertEqual(self.ledger['findings'][ident]['observations'], ['failed'])
        self.assertEqual(self.ledger['evidence']['failed']['previous_status'], 'FAILED')
        self.assertEqual([e['action'] for e in self.ledger['events'] if 'finding_id' in e], ['OPEN', 'REPAIRED', 'CLOSED'])

    def test_repair_is_not_closure(self):
        ident = self.repaired()
        self.assertEqual(unresolved(self.ledger), [ident])
        with self.assertRaises(ValueError):
            close(self.ledger, ident, [])

    def test_missing_or_same_author_review_cannot_close(self):
        ident = self.repaired()
        checks = self.checks(ident)
        with self.assertRaises(ValueError):
            close(self.ledger, ident, checks[:-1])
        for stage in checks:
            ledger = deepcopy(self.ledger)
            ledger['evidence'][stage]['actor'] = 'repair'
            with self.assertRaises(ValueError):
                close(ledger, ident, checks)

    def test_passing_stage_without_explicit_recheck_cannot_close(self):
        ident = self.repaired()
        checks = self.checks(ident)
        self.ledger['evidence']['code_review']['checked_findings'] = []
        with self.assertRaises(ValueError):
            close(self.ledger, ident, checks)

    def test_checks_before_repair_cannot_be_reused_to_close(self):
        ident = self.open_issue()
        checks = self.checks(ident)
        self.ledger = add_evidence(self.ledger, self.receipt('repair', 'repair', checked=[ident]))
        self.ledger = mark_repaired(self.ledger, [ident], 'repair')
        with self.assertRaises(ValueError):
            close(self.ledger, ident, checks)

    def test_each_changed_input_invalidates_and_reopens_closed_issue(self):
        ident = self.repaired()
        checks = self.checks(ident)
        self.ledger = close(self.ledger, ident, checks)
        for key in self.context:
            with self.subTest(key=key):
                changed = {**self.ledger['context'], key: 'f' * 64}
                ledger = invalidate(self.ledger, changed)
                self.assertEqual(ledger['findings'][ident]['status'], 'OPEN')
                self.assertEqual(ledger['evidence']['verification']['status'], 'STALE')
                self.assertEqual(ledger['evidence']['verification']['invalidated_by'], [key])
        self.assertEqual(self.ledger['findings'][ident]['status'], 'CLOSED')

    def test_unchanged_context_preserves_valid_receipts(self):
        self.repaired()
        self.assertEqual(invalidate(self.ledger, self.ledger['context']), self.ledger)

    def test_stale_failure_cannot_open_finding(self):
        self.open_issue()
        self.ledger = invalidate(self.ledger, {**self.context, 'rules_id': 'f' * 64})
        with self.assertRaises(ValueError):
            observe(self.ledger, 'failed', [self.item])

    def test_repeated_finding_keeps_identity_and_history(self):
        ident = self.open_issue()
        self.ledger = add_evidence(self.ledger, self.receipt('failed-again', 'code_review', status='FAILED'))
        self.ledger = observe(self.ledger, 'failed-again', [{**self.item, 'finding_id': ident}])
        self.assertEqual(list(self.ledger['findings']), [ident])
        self.assertEqual(self.ledger['findings'][ident]['observations'], ['failed', 'failed-again'])

    def test_other_reviewer_can_confirm_same_original_finding(self):
        ident = self.open_issue()
        self.ledger = add_evidence(self.ledger, self.receipt('verification-failed', 'verification', status='FAILED'))
        self.ledger = observe(self.ledger, 'verification-failed', [{**self.item, 'finding_id': ident}])
        self.assertEqual(list(self.ledger['findings']), [ident])
        self.assertEqual(self.ledger['findings'][ident]['origin_stage'], 'code_review')

    def test_finding_identity_cannot_be_reused_for_different_issue(self):
        self.open_issue()
        before = deepcopy(self.ledger)
        with self.assertRaises(ValueError):
            observe(self.ledger, 'failed', [{**self.item, 'criterion': 'different criterion'}])
        self.assertEqual(self.ledger, before)

    def test_unknown_duplicate_and_stale_evidence_are_rejected(self):
        self.open_issue()
        for receipt in [self.receipt('failed', 'verification'),
                        self.receipt('unknown', 'verification', checked=['missing'])]:
            with self.assertRaises(ValueError):
                add_evidence(self.ledger, receipt)
        receipt = self.receipt('old', 'verification')
        receipt['context']['candidate_id'] = 'f' * 64
        with self.assertRaises(ValueError):
            add_evidence(self.ledger, receipt)

    def test_empty_failure_or_changed_id_rejected(self):
        self.open_issue()
        for items in [[], [{**self.item, 'finding_id': 'different-id'}], [self.item, self.item]]:
            with self.assertRaises(ValueError):
                observe(self.ledger, 'failed', items)

    def test_unbound_input_or_malformed_context_rejected(self):
        for value in [{}, {**self.context, 'candidate_id': 'not-a-hash'}]:
            with self.assertRaises(ValueError):
                create(value)
        receipt = self.receipt('check', 'verification')
        receipt['depends_on'] = ['candidate_id']
        with self.assertRaises(ValueError):
            add_evidence(self.ledger, receipt)


if __name__ == '__main__':
    unittest.main()
