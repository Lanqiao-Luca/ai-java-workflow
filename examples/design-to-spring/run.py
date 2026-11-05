"""Build the new public Spring candidate in a temporary workspace, never in repo."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.module_plan import validate_plan
CASE = Path(__file__).resolve().parent
SERVICE = 'src/main/java/example/reading/ReadingListService.java'
TESTS = {'validBatchChangesExactlyOneVersionAndKeepsTitlesOrder', 'invalidTailDoesNotPartiallyArchive',
         'unknownTailDoesNotPartiallyArchive', 'ownerCheckedBeforeBusinessPayloadOrVersion',
         'nullVersionNullIdsEmptyAndBlankRejectWithoutChange', 'duplicatesDoNotChangeCallerOrIncrementTwice',
         'currentVersionNoopPreservesSnapshot', 'staleNoopRejectsAndPreservesSnapshot',
         'snapshotsAreImmutable', 'concurrentOldVersionWritersCannotBothCommit',
         'realContextGetSerializesVersionAndOrderedItems', 'postArchivesThroughRealControllerAndService',
         'rejectedWebBatchLeavesEntireSnapshotUnchanged', 'forbiddenAndStaleStatusesAreMapped'}
RED_FAILURES = {'invalidTailDoesNotPartiallyArchive', 'unknownTailDoesNotPartiallyArchive',
                'rejectedWebBatchLeavesEntireSnapshotUnchanged'}


def source_hashes():
    files = [p for p in (CASE / 'app').rglob('*') if p.is_file()]
    files += [CASE / n for n in ('requirements.md', 'design.md', 'contract.json', 'plan.json')]
    return {p.relative_to(CASE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def candidate_id(hashes):
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def parse_tests(directory):
    seen, failures, errors, skipped = [], [], [], []
    for path in sorted(directory.glob('TEST-*.xml')):
        for test in ET.parse(path).getroot().findall('testcase'):
            name = test.attrib['name']
            seen.append(name)
            for tag, output in (('failure', failures), ('error', errors), ('skipped', skipped)):
                if test.find(tag) is not None:
                    output.append(name)
    return seen, failures, errors, skipped


def build(java_home, maven_home, repository, timeout=240, offline=False, log_path=None):
    if os.name != 'posix' or type(timeout) is not int or not 0 < timeout <= 600:
        raise ValueError('POSIX and a bounded timeout required')
    java_home, maven_home, repository = map(lambda p: Path(p).resolve(), (java_home, maven_home, repository))
    if repository.is_relative_to(ROOT):
        raise ValueError('Maven repository must be outside public source tree')
    java, maven = java_home / 'bin/java', maven_home / 'bin/mvn'
    if not java.is_file() or not maven.is_file():
        raise ValueError('usable explicit JDK/Maven homes required')
    contract = json.loads((CASE / 'contract.json').read_text())
    plan = json.loads((CASE / 'plan.json').read_text())
    if hashlib.sha256((CASE / 'design.md').read_bytes()).hexdigest() != contract['sha256']:
        raise ValueError('design bytes drift')
    validate_plan(plan, contract)
    hashes = source_hashes()
    declared = {p for m in plan['modules'] for p in m['writes']}
    if declared != {p for p in hashes if p.startswith('app/')}:
        raise ValueError('module write set does not match actual application')
    repository.mkdir(parents=True, exist_ok=True)
    report = {'candidate_id': candidate_id(hashes), 'source_sha256': hashes,
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Fictional single-JVM memory service; real Spring context, MockMvc and two-thread service checks',
              'production_auth': 'NOT_RUN', 'distributed_behavior': 'NOT_RUN', 'variants': []}
    with tempfile.TemporaryDirectory(prefix='reading-archive-') as temporary:
        temp = Path(temporary)
        env = {k: os.environ[k] for k in ('PATH', 'TMPDIR', 'SYSTEMROOT') if k in os.environ}
        env.update(JAVA_HOME=str(java_home), HOME=str(temp / 'home'), MAVEN_SKIP_RC='true')
        settings = temp / 'settings.xml'
        settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"><mirrors><mirror><id>public-central-only</id><mirrorOf>*</mirrorOf><url>https://repo.maven.apache.org/maven2</url></mirror></mirrors></settings>')
        probe = subprocess.run([str(java), '-version'], env=env, capture_output=True, text=True, timeout=10)
        if probe.returncode:
            raise ValueError('JDK probe failed')
        report['java'] = (probe.stderr or probe.stdout).strip().splitlines()[0]
        for variant in ('red', 'green'):
            app = temp / variant
            shutil.copytree(CASE / 'app', app)
            if variant == 'red':
                shutil.copyfile(CASE / 'fixtures/ReadingListService-red.java.txt', app / SERVICE)
            compiled = {p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(app.rglob('*')) if p.is_file()}
            command = [str(maven), '--batch-mode', '--no-transfer-progress', '--settings', str(settings),
                       '--global-settings', str(settings), '-Dmaven.repo.local=' + str(repository),
                       '-Duser.home=' + str(temp / 'home'), '-Dstyle.color=never', 'test']
            if offline:
                command.insert(1, '--offline')
            started = time.monotonic()
            process = subprocess.Popen(command, cwd=app, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, start_new_session=True)
            try:
                output, _ = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                report['status'] = 'UNKNOWN'
                return report
            if log_path:
                with Path(log_path).open('a') as stream:
                    stream.write(variant + '\n' + output + '\n')
            seen, failed, errors, skipped = parse_tests(app / 'target/surefire-reports')
            wanted = RED_FAILURES if variant == 'red' else set()
            accepted = (set(seen) == TESTS and len(seen) == len(TESTS) and set(failed) == wanted
                        and len(failed) == len(wanted) and not errors and not skipped
                        and process.returncode == (1 if wanted else 0))
            report['variants'].append({'variant': variant, 'compiled_source_sha256': compiled,
                                       'process_exit': process.returncode, 'tests': len(seen),
                                       'test_names': sorted(seen), 'failures': sorted(failed),
                                       'errors': errors, 'skipped': skipped, 'accepted': accepted,
                                       'seconds': round(time.monotonic() - started, 3)})
            if not accepted:
                report['status'] = 'FAILED'
                return report
    report['status'] = 'PASSED'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', required=True, type=Path)
    parser.add_argument('--maven-home', required=True, type=Path)
    parser.add_argument('--repository', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        parser.error('output must be outside public source tree')
    try:
        result = build(args.java_home, args.maven_home, args.repository, offline=args.offline,
                       log_path=args.output.with_suffix('.maven.log'))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('NOT_RUN: build prerequisites or candidate contract rejected (' + type(error).__name__ + ')')
        return 2
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'tests_per_variant': [v['tests'] for v in result['variants']]}))
    return 0 if result['status'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
