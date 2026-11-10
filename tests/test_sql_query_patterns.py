"""Exercise the public SQL case entry from an unrelated working directory."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SqlQueryPatternCaseTests(unittest.TestCase):
    def test_public_entry_executes_four_controls_without_output_files(self):
        entry = ROOT / 'workflows/examples/sql-query-patterns/run.py'
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.run([sys.executable, '-B', str(entry)], cwd=directory,
                                     capture_output=True, text=True, timeout=15)
            self.assertEqual(process.returncode, 0, process.stderr)
            report = json.loads(process.stdout)
            self.assertEqual(set(report['results']),
                             {'n_plus_one', 'parent_pagination', 'date_boundary', 'proposed_unique'})
            self.assertEqual(report['scope']['external_connections'], 0)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
