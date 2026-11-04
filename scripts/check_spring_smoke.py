"""Build the published frozen Spring candidate, without invoking native models."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--maven-home', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='public-spring-ci-') as temporary:
        workspace = Path(temporary)
        shutil.copytree(ROOT / 'examples/native-spring-workflow/final/app', workspace / 'app')
        (workspace / 'verify.py').write_bytes((ROOT / 'tools/native_build.py').read_bytes())
        (workspace / '.run-config.json').write_text(json.dumps({
            'java_home': str(args.java_home.resolve()), 'maven_home': str(args.maven_home.resolve()),
            'repository': str(workspace / '.build/repository')}) + '\n')
        result = subprocess.run([sys.executable, '-B', 'verify.py'], cwd=workspace, timeout=270)
        return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
