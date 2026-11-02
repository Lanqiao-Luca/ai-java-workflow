"""Synthetic macOS build-tree regression. No company data, no downloads or services."""
from pathlib import Path
from unittest.mock import patch
import json,runpy,sys,tempfile,threading,time,unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.execution.build_runtime import BuildGraphRun,BuildTree
from tools.execution.build_cache import seal,verify
from tools.execution.build_fixture import BuildFixture,run_preparation
from tools.execution.runtime import git,Rejected

def node(program,timeout=10):
 return {'id':'work','depends_on':[],'command':['{python}','-I','-B','-c',program],'allowed_write':[],'success_pattern':'^OK$','timeout':timeout}

class BuildExecutionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.repo=self.root/'repo';self.repo.mkdir()
  git(self.repo,'init','-b','main');(self.repo/'input.txt').write_text('independent synthetic');git(self.repo,'add','input.txt');git(self.repo,'commit','-m','Synthetic input');self.runs=[]
 def tearDown(self):
  for g in self.runs:g.close()
  self.temp.cleanup()
 def graph(self,program,timeout=10,seeds=None,daemon=False):
  g=BuildGraphRun(self.repo,'HEAD',self.root/'runs',{'graph_id':'build','max_parallel':1,'nodes':[node(program,timeout)]},cache_seeds=seeds,allow_observed_daemon=daemon);self.runs.append(g);return g
 def test_child_inherits_sandbox_and_foreground_build_succeeds(self):
  g=self.graph('import subprocess,sys; subprocess.run([sys.executable,"-I","-c","import time;time.sleep(.15)"],check=True); print("OK")')
  s=g.run();self.assertEqual(s['status'],'SUCCEEDED');self.assertTrue(s['nodes']['work']['child_seen']);self.assertTrue(s['nodes']['work']['tree_stopped']);self.assertTrue(all(s['nodes']['work']['probe'].values()));self.assertEqual(g.cleanup(),[])
 def test_timeout_stops_observed_children(self):
  g=self.graph('import subprocess,sys; subprocess.run([sys.executable,"-c","import time;time.sleep(20)"])',.6)
  s=g.run();self.assertEqual(s['nodes']['work']['reason'],'TIMEOUT');self.assertTrue(s['nodes']['work']['tree_stopped']);self.assertNotIn('work',g.results)
 def test_cancellation_stops_observed_children(self):
  g=self.graph('import subprocess,sys; subprocess.run([sys.executable,"-c","import time;time.sleep(20)"])')
  def request():
   end=time.monotonic()+10
   while time.monotonic()<end:
    if g.state['nodes']['work']['status']=='RUNNING':time.sleep(.3);g.cancel.set();return
    time.sleep(.02)
  t=threading.Thread(target=request);t.start();s=g.run();t.join(2)
  self.assertEqual(s['nodes']['work']['reason'],'CANCELLED');self.assertTrue(s['nodes']['work']['tree_stopped'])
 def test_observed_detached_child_refuses_promotion(self):
  g=self.graph('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"],start_new_session=True);time.sleep(2);print("OK")')
  s=g.run();self.assertEqual(s['nodes']['work']['reason'],'DETACHED_PROCESS');self.assertTrue(s['nodes']['work']['tree_stopped']);self.assertNotIn('work',g.results)
 def test_background_child_refuses_promotion(self):
  g=self.graph('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"]);time.sleep(.2);print("OK")')
  s=g.run();self.assertEqual(s['nodes']['work']['reason'],'BACKGROUND_PROCESS');self.assertTrue(s['nodes']['work']['tree_stopped'])
 def test_observer_exception_keeps_active_lease_and_resources(self):
  g=self.graph('print("OK")')
  # Fail before creating a child: no permission to guess that observation succeeded.
  with patch.object(BuildTree,'live',side_effect=Rejected('synthetic observation failure')):
   with self.assertRaises(Rejected):g.run()
  self.assertTrue((g.pool.area/'quarantine.json').is_file())
  self.assertEqual(json.loads((g.pool.area/'0.lock').read_text())['state'],'active')
  with self.assertRaises(Rejected):g.cleanup()
 def test_opted_in_observed_daemon_must_exit(self):
  g=self.graph('import subprocess,sys; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(.3)"],start_new_session=True);p.wait();print("OK")',daemon=True)
  s=g.run();self.assertEqual(s['status'],'SUCCEEDED');self.assertTrue(s['nodes']['work']['observed_detached']);self.assertTrue(s['nodes']['work']['tree_stopped'])
 def test_opted_in_daemon_cannot_remain_after_foreground_exit(self):
  g=self.graph('import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"],start_new_session=True);time.sleep(.2);print("OK")',daemon=True)
  s=g.run();self.assertEqual(s['nodes']['work']['reason'],'BACKGROUND_PROCESS');self.assertTrue(s['nodes']['work']['tree_stopped']);self.assertNotIn('work',g.results)
 def test_cache_manifest_detects_drift_and_configuration(self):
  seed=self.root/'cache';seed.mkdir();(seed/'artifact.jar').write_text('synthetic artifact');seal(seed,'maven');verify(seed,'maven')
  (seed/'artifact.jar').write_text('changed')
  with self.assertRaises(Rejected):verify(seed,'maven')
  (seed/'settings.xml').write_text('not accepted')
  with self.assertRaises(Rejected):seal(seed,'maven')
 def test_cache_copy_is_instance_private(self):
  seed=self.root/'cache';seed.mkdir();(seed/'artifact.jar').write_text('synthetic artifact');seal(seed,'maven')
  g=self.graph('import pathlib,os; p=pathlib.Path(os.environ["HOME"])/"maven/artifact.jar";p.write_text("local only");print("OK")',seeds={'maven':seed})
  self.assertEqual(g.run()['status'],'SUCCEEDED');self.assertEqual((seed/'artifact.jar').read_text(),'synthetic artifact');self.assertEqual(g.cleanup(),[])

 def test_queue_cancellation_timeout_and_quarantine_stay_distinct(self):
  g=self.graph('print("OK")');resource,_,_=g._prepare('graph',[])
  lease=g.pool.acquire(threading.Event(),time.monotonic()+1)
  try:
   cancel=threading.Event();cancel.set()
   r=g.backend.execute(resource,[g.backend.python,'-c','print(1)'],.1,cancel)
   self.assertEqual(r['reason'],'CANCELLED');self.assertIsNone(r['started_at'])
   r=g.backend.execute(resource,[g.backend.python,'-c','print(1)'],.1,threading.Event())
   self.assertEqual(r['reason'],'TIMEOUT');self.assertIsNone(r['started_at'])
   (g.pool.area/'quarantine.json').write_text('{}')
   r=g.backend.execute(resource,[g.backend.python,'-c','print(1)'],.1,threading.Event())
   self.assertEqual(r['reason'],'POOL_QUARANTINED');self.assertIsNone(r['started_at'])
  finally:g.pool.release(lease)
 def test_invalid_cache_rejects_before_allocating_run(self):
  seed=self.root/'unmarked-cache';seed.mkdir()
  with self.assertRaises(Rejected):self.graph('print("OK")',seeds={'maven':seed})
  self.assertFalse((self.root/'runs').exists())

 def test_failed_fixture_retains_original_path_and_state(self):
  with self.assertRaisesRegex(RuntimeError,'synthetic unknown'):
   with BuildFixture('owned-',self.root) as fixture:
    (fixture.path/'state.json').write_text('{"status":"UNKNOWN"}')
    raise RuntimeError('synthetic unknown')
  self.assertTrue(fixture.path.is_dir());self.assertEqual(json.loads((fixture.path/'state.json').read_text())['status'],'UNKNOWN')
 def test_fixture_only_removes_verified_success(self):
  with BuildFixture('unverified-',self.root) as retained:pass
  self.assertTrue(retained.path.is_dir())
  with BuildFixture('success-',self.root) as removed:removed.safe_to_remove()
  self.assertFalse(removed.path.exists())
 def preparation(self,program,timeout=5):
  return run_preparation([sys.executable,'-I','-B','-c',program],self.root,
    {'PATH':'/usr/bin:/bin','HOME':str(self.root),'LC_ALL':'C'},self.root/'prep.log',self.root/'prep-state.json',timeout)
 def test_preparation_timeout_stops_helper_and_child(self):
  r=self.preparation('import subprocess,sys;subprocess.run([sys.executable,"-c","import time;time.sleep(20)"])',.5)
  self.assertEqual(r['reason'],'TIMEOUT');self.assertTrue(r['tree_stopped']);self.assertEqual(json.loads((self.root/'prep-state.json').read_text())['status'],'FAILED')
 def test_preparation_waits_for_observed_single_use_daemon(self):
  began=time.monotonic()
  r=self.preparation('import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(.4)"],start_new_session=True);time.sleep(.1)')
  self.assertEqual(r['exit'],0);self.assertIsNone(r['reason']);self.assertTrue(r['tree_stopped']);self.assertTrue(r['observed_detached']);self.assertGreater(time.monotonic()-began,.3)
 def test_preparation_observer_failure_preserves_unknown_state(self):
  with patch.object(BuildTree,'live',side_effect=Rejected('synthetic observer failure')):
   with self.assertRaises(Rejected):self.preparation('import time;time.sleep(20)')
  self.assertEqual(json.loads((self.root/'prep-state.json').read_text())['status'],'UNKNOWN')

 def test_copied_cache_identity_is_checked_before_execution(self):
  import shutil
  seed=self.root/'cache';seed.mkdir();(seed/'artifact.jar').write_text('synthetic artifact');seal(seed,'maven')
  g=self.graph('print("OK")',seeds={'maven':seed});copy=shutil.copytree
  def corrupt(source,destination,*a,**kw):
   result=copy(source,destination,*a,**kw);(Path(destination)/'artifact.jar').write_text('changed after admission');return result
  with patch('tools.execution.build_runtime.shutil.copytree',side_effect=corrupt):state=g.run()
  self.assertEqual(state['nodes']['work']['status'],'FAILED');self.assertNotIn('work',g.results)
  self.assertFalse((g.resources['work']/'sandbox/command.log').exists())

if __name__=='__main__':unittest.main()
