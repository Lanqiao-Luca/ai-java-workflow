"""Build an independently synthetic native-workflow fixture with explicit public tools.
Copies of this file run as verify.py in an instance. No raw logs or absolute tool paths
are printed or included in validation.json. This runner is not an OS sandbox.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import subprocess
import xml.etree.ElementTree as ET

CONTRACT_CLASS = 'example.nativeflow.LabelContractTest'
EXPECTED = {
    'springBeanAndControllerAreWired', 'trimCaseAndStableDeduplication', 'emptyListIsValid',
    'nullListIsRejected', 'nullItemIsRejected', 'blankItemRejectsWholeRequest',
    'exactlySixteenCharactersAreAccepted', 'seventeenCharactersAreRejected',
    'duplicatesDoNotConsumeDistinctLimit', 'fifthDistinctLabelIsRejected',
    'rootLocaleSurvivesTurkishDefault', 'callerInputListIsNotMutated', 'lengthIsCheckedAfterRootLowercase',
}


def sources(workspace):
    app = workspace / 'app'
    paths = [app / 'pom.xml'] + sorted((app / 'src').rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('linked source')
    files = [p for p in paths if p.is_file()]
    if not (app / 'pom.xml').is_file():
        raise ValueError('missing POM')
    return {p.relative_to(workspace).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def identity(mapping):
    return hashlib.sha256(json.dumps(mapping, sort_keys=True).encode()).hexdigest()


def parse_reports(directory):
    cases, failures, errors, skipped, required = [], [], [], [], []
    if directory.is_symlink(): raise ValueError('linked reports')
    for path in sorted(directory.glob('TEST-*.xml')):
        if path.is_symlink(): raise ValueError('linked report')
        tree = ET.parse(path).getroot()
        for case in tree.findall('.//testcase'):
            classname = case.attrib.get('classname', '')
            name = case.attrib['name']
            key = classname + '#' + name
            cases.append(key)
            if classname == CONTRACT_CLASS:
                required.append(name)
            if case.find('failure') is not None: failures.append(key)
            if case.find('error') is not None: errors.append(key)
            if case.find('skipped') is not None: skipped.append(key)
    return {'tests': len(cases), 'test_names': sorted(cases), 'failures': sorted(failures),
            'errors': sorted(errors), 'skipped': sorted(skipped),
            'contract_complete': len(required) == len(EXPECTED) and set(required) == EXPECTED}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=int, default=240)
    parser.add_argument('--offline', action='store_true', help='Resolve only from the explicitly prepared public cache')
    args = parser.parse_args()
    workspace = Path.cwd().resolve()
    build = workspace / '.build'
    if build.is_symlink() or (build.exists() and not build.is_dir()):
        raise SystemExit('REJECTED: invalid instance build directory')
    build.mkdir(mode=0o700, exist_ok=True)
    result_path = build / 'validation.json'
    result_path.unlink(missing_ok=True)
    result = {'status': 'FAILED', 'synthetic': True, 'offline': args.offline, 'source_sha256': {}, 'candidate_id': None,
              'tests': 0, 'test_names': [], 'failures': [], 'errors': [], 'skipped': [],
              'contract_complete': False, 'process_exit': None,
              'scope': 'Spring context and MockMvc only; no HTTP listener, database or deployment'}
    category = 'input_admission'
    process = None
    try:
        if os.name != 'posix' or not 1 <= args.timeout <= 900:
            raise ValueError('POSIX and bounded timeout required')
        config_path = workspace / '.run-config.json'
        if config_path.is_symlink(): raise ValueError('linked configuration')
        config = json.loads(config_path.read_text())
        if set(config) != {'java_home', 'maven_home', 'repository'}:
            raise ValueError('explicit tool/cache configuration required')
        selected = {}
        for key, value in config.items():
            if not isinstance(value, str) or not Path(value).is_absolute():
                raise ValueError('absolute explicit tool/cache path required')
            selected[key] = Path(value).resolve()
        if (workspace / 'app/.mvn').exists():
            raise ValueError('project Maven injection not allowed')
        for name in ['settings.xml', 'maven.log', 'home', 'target']:
            if (build / name).is_symlink(): raise ValueError('linked build output')
        if selected['repository'].is_relative_to(workspace / 'app'):
            raise ValueError('cache inside source')
        selected['repository'].mkdir(parents=True, exist_ok=True)
        java = selected['java_home'] / 'bin/java'
        maven = selected['maven_home'] / 'bin/mvn'
        if not java.is_file() or not maven.is_file(): raise ValueError('missing explicit tools')
        before = sources(workspace)
        result['source_sha256'] = before
        result['candidate_id'] = identity(before)
        settings = build / 'settings.xml'
        settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0">'
            '<mirrors><mirror><id>explicit-public-central</id><mirrorOf>*</mirrorOf>'
            '<url>https://repo.maven.apache.org/maven2</url></mirror></mirrors></settings>')
        task_home = build / 'home'; task_home.mkdir(exist_ok=True)
        task_tmp = build / 'tmp'; task_tmp.mkdir(exist_ok=True)
        if task_tmp.is_symlink(): raise ValueError('linked temporary directory')
        # Construct a minimal instance environment. Never inherit service, cloud,
        # database, proxy, authentication or arbitrary caller variables.
        env = {'PATH': str(selected['java_home'] / 'bin') + os.pathsep + os.defpath,
               'JAVA_HOME': str(selected['java_home']), 'MAVEN_SKIP_RC': 'true',
               'HOME': str(task_home), 'MAVEN_CONFIG': str(task_home),
               'TMPDIR': str(task_tmp), 'TMP': str(task_tmp), 'TEMP': str(task_tmp),
               'LANG': 'C.UTF-8'}
        command = [str(maven), '--batch-mode', '--no-transfer-progress', '--settings', str(settings),
            '--global-settings', str(settings), '-Dmaven.repo.local=' + str(selected['repository']),
            '-Duser.home=' + str(task_home), '-Dstyle.color=never',
            '-Dworkflow.build.directory=' + str(build / 'target'),
            '-f', str(workspace / 'app/pom.xml'), 'clean', 'test']
        if args.offline:
            command.insert(1, '--offline')
        category = 'build_execution'
        with (build / 'maven.log').open('wb') as log:
            process = subprocess.Popen(command, cwd=workspace / 'app', env=env,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                result['process_exit'] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                category = 'build_timeout'
                os.killpg(process.pid, signal.SIGKILL)
                result['process_exit'] = process.wait()
                raise ValueError('build deadline')
        category = 'junit_or_source_mismatch'
        result.update(parse_reports(build / 'target/surefire-reports'))
        after = sources(workspace)
        if before != after: raise ValueError('source changed during build')
        if (result['process_exit'] == 0 and result['contract_complete']
                and not result['failures'] and not result['errors'] and not result['skipped']):
            result['status'] = 'PASSED'
            category = 'passed'
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError):
        # Raw exception strings can contain machine paths or connection details.
        pass
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        result['category'] = category
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Synthetic Spring verification:', result['status'], 'tests=' + str(result['tests']),
          'category=' + category)
    return 0 if result['status'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
