"""Check observable header, coverage and archive invariants in temporary repositories."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from tools.document_contracts import ContractError, check, fields

TEXT = '**目的**：帮助当前使用者确认候选与验收。\n\n**适用于**：已明确范围的本地文档维护。\n\n# 合同\n'


class DocumentContractsTests(unittest.TestCase):
    def test_native_skill_frontmatter_is_preserved(self):
        self.assertIn('目的', fields('---\nname: demo\ndescription: local example\n---\n' + TEXT))

    def test_title_before_declarations_is_not_accepted(self):
        with self.assertRaises(ContractError):
            fields('# 先写标题\n\n' + TEXT)

    def test_generic_or_missing_purpose_is_not_accepted(self):
        for text in [TEXT.replace('帮助当前使用者确认候选与验收。', '待填'),
                     TEXT.replace('帮助当前使用者确认候选与验收。', '将研发经验表达为可复用、可验证的方法。'),
                     TEXT.replace('**适用于**：已明确范围的本地文档维护。', '')]:
            with self.subTest(text=text), self.assertRaises(ContractError):
                fields(text)

    def test_unclosed_frontmatter_is_rejected(self):
        with self.assertRaises(ContractError):
            fields('---\nname: demo\n' + TEXT)

    def fixture(self, root):
        (root / 'docs').mkdir()
        (root / 'current.md').write_text(TEXT)
        original = b'# Published original\n'
        (root / 'old.md').write_bytes(original)
        data = {'version': 1, 'documents': {'current.md': {'mode': 'current'}, 'old.md': {
            'mode': 'preserved', 'sha256': hashlib.sha256(original).hexdigest(),
            'purpose': 'Preserve original published evidence.', 'applies_to': 'Historical checks only.',
            'reason': 'Existing source-bound receipt; do not rewrite.'}}}
        index = root / 'docs/document-contract-index.json'
        index.write_text(json.dumps(data))
        return index, data

    def test_current_and_archive_use_different_declaration_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            self.assertEqual(check(root), {'current': 1, 'preserved': 1})

    def test_archive_changes_are_rejected_without_rewriting_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / 'old.md').write_text(TEXT)
            with self.assertRaises(ContractError):
                check(root)

    def test_unregistered_document_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / 'new.md').write_text(TEXT)
            with self.assertRaises(ContractError):
                check(root)

    def test_archive_sidecar_needs_real_purpose_and_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index, data = self.fixture(root)
            data['documents']['old.md']['purpose'] = ''
            index.write_text(json.dumps(data))
            with self.assertRaises(ContractError):
                check(root)

    def test_archived_symlink_is_rejected_even_when_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            (root / 'old.md').unlink()
            (root / 'old.md').symlink_to(root / 'current.md')
            with self.assertRaises(ContractError):
                check(root)


if __name__ == '__main__':
    unittest.main()
