"""Run/resume the bounded synthetic native workflow; credentials stay on the host."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.native_flow import FlowRejected, NativeFlow, digest
from tools.native_recovery import RecoveryRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--maven-home', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--native-timeout', type=int, default=600)
    parser.add_argument('--max-rounds', type=int, default=3, help='Initial round included, maximum 5')
    parser.add_argument('--budget-seconds', type=int, default=3600)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--pause-after', choices=['requirements', 'implementation', 'verification', 'code_review'])
    parser.add_argument('--public-synthetic-input', action='store_true')
    parser.add_argument('--allow-host-trust-registration', action='store_true')
    args = parser.parse_args()
    if not args.public_synthetic_input or not args.allow_host_trust_registration:
        parser.error('acknowledge public synthetic model input and host project trust registration')
    if not 1 <= args.native_timeout <= 3600:
        parser.error('native timeout must be 1..3600')
    for home, executable in [(args.java_home, 'bin/java'), (args.maven_home, 'bin/mvn')]:
        if not (home.resolve() / executable).is_file():
            parser.error('missing explicitly selected tool')
    case = ROOT / 'examples/native-spring-workflow'
    seed = {}
    for path in sorted((case / 'seed').rglob('*')):
        if path.is_symlink():
            parser.error('linked seed rejected')
        if path.is_file():
            seed[path.relative_to(case / 'seed').as_posix()] = path.read_bytes()
    seed['app/src/test/java/example/nativeflow/LabelContractTest.java'] = (case / 'acceptance/LabelContractTest.java').read_bytes()
    runner = (ROOT / 'tools/native_build.py').read_bytes()
    flow = None

    def build(workspace, offline):
        remaining = flow.deadline - time.time()
        if remaining < 2:
            raise FlowRejected('budget expired before build')
        command = [sys.executable, '-B', 'verify.py', '--timeout', str(min(240, int(remaining) - 1))]
        if offline:
            command.append('--offline')
        report_path = workspace / '.build/validation.json'
        report_path.unlink(missing_ok=True)
        process = subprocess.run(command, cwd=workspace, stdin=subprocess.DEVNULL,
                                 timeout=min(270, remaining))
        report = json.loads(report_path.read_text())
        if process.returncode not in (0, 1) or (process.returncode == 0) != (report.get('status') == 'PASSED'):
            raise FlowRejected('build process and report disagree')
        return report

    def prepare(workspace, node, workflow):
        if not workflow['validate']:
            return
        (workspace / 'verify.py').write_bytes(runner)
        (workspace / '.run-config.json').write_text(json.dumps({
            'java_home': str(args.java_home.resolve()), 'maven_home': str(args.maven_home.resolve()),
            'repository': str(workspace / '.build/repository')}) + '\n')
        # Failed tests are expected when implementation needs repair. Warm public dependencies,
        # then let the independent verifier diagnose; preparation itself does not accept a stage.
        build(workspace, offline=False)

    def validate(workspace, node, workflow):
        if (workspace / 'verify.py').read_bytes() != runner:
            raise FlowRejected('frozen runner changed')
        return build(workspace, offline=True)

    context = digest({'java_home': str(args.java_home.resolve()), 'maven_home': str(args.maven_home.resolve()),
                      'codex': args.codex, 'native_timeout': args.native_timeout,
                      'runner_sha256': hashlib.sha256(runner).hexdigest()})
    try:
        flow = NativeFlow(seed, ROOT, ROOT / 'graphs/native-java-spring.json', args.run_root,
                          codex=args.codex, timeout=args.native_timeout, prepare=prepare, validate=validate,
                          resume=args.resume)
        state = RecoveryRunner(flow, max_rounds=args.max_rounds, budget_seconds=args.budget_seconds,
                               context_id=context, pause_after=args.pause_after).run()
    except (FlowRejected, OSError, ValueError) as exc:
        print('Native recovery REJECTED:', type(exc).__name__, '; inspect local checkpoint and prerequisites')
        return 2
    print('Native recovery:', state['status'], '; round:', state['round'], '; attempts:', state['attempts'])
    print('Private attempts and state retained; no GitHub publication performed')
    return 0 if state['status'] == 'SUCCEEDED' else 3 if state['status'] == 'PAUSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
