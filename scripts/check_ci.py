"""Portable regression suite: no model, real sandbox, Docker daemon or Java build."""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for pattern in ('test_public_history.py', 'test_check_all.py', 'test_native_*.py', 'test_loop_*.py', 'test_goal_graph_*.py', 'test_docker_io.py'):
        suite.addTests(loader.discover(str(ROOT / 'tests'), pattern=pattern))
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
