"""Historical receipts must bind original public bytes even after live method edits."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from tools import public_history


class PublicHistoryTests(unittest.TestCase):
    def test_changed_live_method_does_not_relabel_historical_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs/public-baseline').mkdir(parents=True)
            (root / 'current.md').write_text('new current method')
            old = b'original public method'
            (root / 'docs/public-baseline/old.txt').write_bytes(old)
            index = root / 'docs/public-baseline/sources.json'
            data = {'version': 1, 'sources': {'current.md': {
                'path': 'docs/public-baseline/old.txt', 'sha256': hashlib.sha256(old).hexdigest()}}}
            index.write_text(json.dumps(data))
            with patch.object(public_history, 'INDEX_SHA256', hashlib.sha256(index.read_bytes()).hexdigest()):
                self.assertEqual(public_history.source_bytes(root, 'current.md'), old)
                (root / 'docs/public-baseline/old.txt').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    public_history.source_bytes(root, 'current.md')

    def test_manifest_cannot_redirect_a_pinned_historical_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs/public-baseline').mkdir(parents=True)
            (root / 'docs/public-baseline/sources.json').write_text('{}')
            with self.assertRaises(ValueError):
                public_history.source_bytes(root, 'current.md')


if __name__ == '__main__':
    unittest.main()
