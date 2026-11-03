"""Check orchestration boundaries using independent temporary scripts."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_all import run_checks


class CheckAllTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "scripts").mkdir()

    def script(self, name, body):
        (self.root / "scripts" / name).write_text(body)

    def run_quiet(self, checks):
        output = StringIO()
        with redirect_stdout(output):
            result = run_checks(self.root, checks)
        return result, output.getvalue()

    def test_failure_preserves_exit_and_does_not_run_successor(self):
        self.script("first.py", "raise SystemExit(7)\n")
        self.script("later.py", "from pathlib import Path\nPath('unexpected').touch()\n")
        code, output = self.run_quiet(("first.py", "later.py"))
        self.assertEqual(code, 7)
        self.assertFalse((self.root / "unexpected").exists())
        self.assertNotIn("PASS:", output)

    def test_success_uses_repository_cwd_and_disables_bytecode(self):
        self.script("first.py", "from pathlib import Path\nimport sys\n"
                    "assert sys.dont_write_bytecode\n"
                    "assert Path('scripts/first.py').is_file()\n"
                    "Path('receipt').write_text('first')\n")
        self.script("second.py", "from pathlib import Path\n"
                    "assert Path('receipt').read_text() == 'first'\n")
        code, output = self.run_quiet(("first.py", "second.py"))
        self.assertEqual(code, 0)
        self.assertIn("PASS: 2 offline checks", output)

    def test_missing_check_is_failure(self):
        code, output = self.run_quiet(("missing.py",))
        self.assertNotEqual(code, 0)
        self.assertNotIn("PASS:", output)

    def test_timeout_stops_before_next_check(self):
        with patch("scripts.check_all.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture", 60)) as child:
            code, output = self.run_quiet(("first.py", "later.py"))
        self.assertEqual(code, 124)
        self.assertEqual(child.call_count, 1)
        self.assertNotIn("PASS:", output)

    def test_launch_failure_is_not_success(self):
        with patch("scripts.check_all.subprocess.run", side_effect=OSError):
            code, output = self.run_quiet(("first.py",))
        self.assertEqual(code, 2)
        self.assertNotIn("PASS:", output)

    def test_signal_termination_is_failure(self):
        with patch("scripts.check_all.subprocess.run", return_value=subprocess.CompletedProcess([], -15)):
            code, output = self.run_quiet(("first.py",))
        self.assertEqual(code, 143)
        self.assertNotIn("PASS:", output)


if __name__ == "__main__":
    unittest.main()
