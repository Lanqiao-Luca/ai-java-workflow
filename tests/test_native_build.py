"""Synthetic subprocess/XML contract tests. These do NOT run Maven or Spring."""
from pathlib import Path
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools import native_build


class BuildRunnerTests(unittest.TestCase):
    def run_case(self, mode, offline=False):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / 'workspace'; workspace.mkdir()
            (workspace / 'app/src').mkdir(parents=True)
            (workspace / 'app/pom.xml').write_text('synthetic POM fixture')
            (workspace / 'app/src/Fixture.java').write_text('synthetic source fixture')
            jdk = root / 'jdk/bin'; jdk.mkdir(parents=True)
            (jdk / 'java').write_text('fixture tool, never executed')
            tools = root / 'maven/bin'; tools.mkdir(parents=True)
            script = tools / 'mvn'
            script.write_text('#!' + sys.executable + '\n' + '''import sys,os
from pathlib import Path
import xml.etree.ElementTree as ET
mode = ''' + repr(mode) + '''
assert 'JAVA_TOOL_OPTIONS' not in os.environ
assert 'MAVEN_OPTS' not in os.environ
for key in ['SPRING_DATASOURCE_PASSWORD', 'DB_PASSWORD', 'AWS_SECRET_ACCESS_KEY',
            'AZURE_CLIENT_SECRET', 'GOOGLE_APPLICATION_CREDENTIALS', 'OPENAI_API_KEY',
            'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NETRC', 'PYTHONPATH',
            'CUSTOM_WORK_SECRET']:
 assert key not in os.environ, 'caller variable leaked: ' + key
assert os.environ['PATH'] == str(Path(os.environ['JAVA_HOME']) / 'bin') + os.pathsep + os.defpath
assert os.environ['TMPDIR'] == os.environ['TMP'] == os.environ['TEMP']
assert Path(os.environ['TMPDIR']).parent == Path(os.environ['HOME']).parent
assert os.environ['MAVEN_CONFIG'] == os.environ['HOME']
assert sys.argv.count('--offline') == ''' + repr(1 if offline else 0) + '''
out = Path(next(a.split('=',1)[1] for a in sys.argv if a.startswith('-Dworkflow.build.directory=')))
reports = out / 'surefire-reports'; reports.mkdir(parents=True)
methods = ''' + repr(sorted(native_build.EXPECTED)) + '''
if mode == 'missing': methods.pop()
suite=ET.Element('testsuite')
for n in methods:
 case=ET.SubElement(suite,'testcase',classname='example.nativeflow.LabelContractTest',name=n)
 if mode in ['failure','error','skipped'] and n == methods[0]: ET.SubElement(case,mode)
ET.ElementTree(suite).write(reports/'TEST-fixture.xml')
if mode == 'drift': Path('src/Fixture.java').write_text('changed source')
sys.exit(1 if mode == 'exit_failure' else 0)
''')
            script.chmod(0o700)
            config = {'java_home': str(jdk.parent), 'maven_home': str(tools.parent), 'repository': str(root/'cache')}
            if mode == 'extra_config': config['offline'] = True
            config_bytes = json.dumps(config)
            (workspace/'.run-config.json').write_text(config_bytes)
            if mode == 'injection': (workspace/'app/.mvn').mkdir()
            previous = Path.cwd()
            try:
                os.chdir(workspace)
                with patch.object(sys,'argv',['verify.py'] + (['--offline'] if offline else [])), patch.dict(os.environ, dict.fromkeys(['JAVA_TOOL_OPTIONS', 'MAVEN_OPTS',
                     'SPRING_DATASOURCE_PASSWORD', 'DB_PASSWORD', 'AWS_SECRET_ACCESS_KEY',
                     'AZURE_CLIENT_SECRET', 'GOOGLE_APPLICATION_CREDENTIALS', 'OPENAI_API_KEY',
                     'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NETRC', 'PYTHONPATH',
                     'CUSTOM_WORK_SECRET'], 'synthetic-never-forward')), contextlib.redirect_stdout(io.StringIO()):
                    code=native_build.main()
            finally: os.chdir(previous)
            self.assertEqual((workspace/'.run-config.json').read_text(), config_bytes)
            result=json.loads((workspace/'.build/validation.json').read_text())
            self.assertNotIn(str(root),json.dumps(result))
            return code,result

    def test_complete_fixture_and_secret_free_child_environment(self):
        code,result=self.run_case('valid')
        self.assertEqual(code,0)
        self.assertEqual(result['tests'],len(native_build.EXPECTED))
        self.assertEqual(result['status'],'PASSED')
        self.assertTrue(result['source_sha256'])

    def test_offline_is_explicit_cli_choice_and_configuration_is_unchanged(self):
        for offline in [False, True]:
            with self.subTest(offline=offline):
                code, result = self.run_case('valid', offline=offline)
                self.assertEqual(code, 0)
                self.assertEqual(result['offline'], offline)

    def test_offline_is_not_accepted_as_fourth_configuration_key(self):
        code, result = self.run_case('extra_config', offline=True)
        self.assertEqual(code, 1)
        self.assertEqual(result['category'], 'input_admission')

    def test_missing_required_assertion_rejected(self):
        self.assertEqual(self.run_case('missing')[0],1)

    def test_failure_error_and_skip_each_rejected(self):
        for mode in ['failure','error','skipped']:
            with self.subTest(mode=mode):self.assertEqual(self.run_case(mode)[0],1)

    def test_exit_failure_rejected_despite_green_xml(self):
        self.assertEqual(self.run_case('exit_failure')[0],1)

    def test_source_drift_rejected(self):
        self.assertEqual(self.run_case('drift')[0],1)

    def test_project_maven_injection_rejected(self):
        self.assertEqual(self.run_case('injection')[0],1)


if __name__=='__main__':unittest.main()
