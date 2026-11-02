"""Real local Docker tests. Explicit Engine/image mandatory; missing setup exits NOT_RUN."""
from pathlib import Path
from unittest.mock import patch
import argparse,json,sys,tempfile,threading,time,unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.execution.build_fixture import BuildFixture
from tools.execution.docker_io import DockerCLI,DockerUnavailable
from tools.execution.docker_runtime import DockerGraphRun
from tools.execution.runtime import git,Rejected
CONFIG=None

class DockerKernelTests(unittest.TestCase):
 def setUp(self):
  self.fixture=BuildFixture('synthetic-docker-regression-');self.root=self.fixture.path;self.repo=self.root/'repo';self.repo.mkdir()
  git(self.repo,'init','-b','main');(self.repo/'input.txt').write_text('synthetic public fixture');git(self.repo,'add','.');git(self.repo,'commit','-m','Synthetic test base')
  self.client=DockerCLI(CONFIG.docker,CONFIG.socket,self.root/'client');self.graphs=[]
 def tearDown(self):
  failed=any(t is self for t,e in self._outcome.result.failures+self._outcome.result.errors)
  try:
   if not failed:
    for g in self.graphs:
     self.assertFalse(g.backend.unsafe_resources);self.assertFalse(g.cleanup(discard_failed=True))
    self.fixture.safe_to_remove()
  finally:
   for g in self.graphs:g.close()
   self.fixture.__exit__(RuntimeError if failed else None,None,None)
 def graph(self,program,timeout=15,write=None,limits=None):
  options={'memory_mb':64,'cpus':1,'pids':32,'seed_cache':False};options.update(limits or {})
  definition={'graph_id':'test-'+str(len(self.graphs)),'max_parallel':1,'nodes':[{'id':'work','depends_on':[],'command':['{python}','-I','-B','-c',program],
   'allowed_write':write or [],'success_pattern':'^OK$','timeout':timeout}]}
  g=DockerGraphRun(self.repo,'HEAD',self.root/'runs',definition,self.client,CONFIG.image,limits=options);self.graphs.append(g);return g
 def test_real_namespace_permissions_limits_and_cleanup(self):
  g=self.graph('print("OK")');s=g.run();self.assertEqual(s['status'],'SUCCEEDED')
  self.assertTrue(all(s['graph_resource']['probe'].values()));self.assertTrue(all(s['nodes']['work']['probe'].values()));self.assertTrue(s['nodes']['work']['tree_stopped'])
 def test_declared_source_is_promoted_from_stopped_container(self):
  g=self.graph('from pathlib import Path;Path("out.txt").write_text("synthetic");print("OK")',write=['out.txt'])
  self.assertEqual(g.run()['status'],'SUCCEEDED');self.assertEqual((g.resources['work']/'worktree/out.txt').read_text(),'synthetic')
 def test_undeclared_source_is_not_promoted(self):
  g=self.graph('from pathlib import Path;Path("extra.txt").write_text("synthetic");print("OK")')
  self.assertEqual(g.run()['nodes']['work']['status'],'FAILED');self.assertNotIn('work',g.results);self.assertFalse((g.resources['work']/'worktree/extra.txt').exists())
 def test_symlink_output_is_not_promoted(self):
  g=self.graph('from pathlib import Path;Path("out.txt").symlink_to("input.txt");print("OK")',write=['out.txt'])
  self.assertNotEqual(g.run()['nodes']['work']['status'],'SUCCEEDED');self.assertNotIn('work',g.results)
 def test_timeout_stops_namespace_including_detached_child(self):
  g=self.graph('import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True);time.sleep(30)',timeout=2)
  n=g.run()['nodes']['work'];self.assertEqual(n['reason'],'TIMEOUT');self.assertTrue(n['tree_stopped'])
  cid=g.backend.records[str(g.resources['work'])]['containers']['task']['id'];v=g.backend._inspect(g.resources['work'],cid);self.assertFalse(v['State']['Running']);self.assertEqual(v['State']['Pid'],0)
 def test_container_deadline_without_host_watchdog(self):
  g=self.graph('print("unused")');resource,_,_=g._prepare('work',[])
  lease=g.pool.acquire(threading.Event(),time.monotonic()+2);cid=None
  try:
   spec={'timeout':.5,'command':['/usr/bin/python3','-c','import time;time.sleep(20)'],'copy_cache':False}
   cid=g.backend._create(resource,'task',spec);self.client.call(['container','start',cid])
   end=time.monotonic()+5
   while g.backend._inspect(resource,cid)['State']['Running'] and time.monotonic()<end:time.sleep(.03)
   state=g.backend._inspect(resource,cid)['State'];self.assertFalse(state['Running']);self.assertEqual(state['ExitCode'],124);self.assertEqual(state['Pid'],0)
  finally:
   if cid and g.backend._inspect(resource,cid)['State']['Running']:self.client.call(['container','kill',cid])
   if cid:self.assertFalse(g.backend._inspect(resource,cid)['State']['Running'])
   g.pool.release(lease);g.state['status']='INCOMPLETE';g.state['nodes']['work']['status']='FAILED';g._save()

 def test_cancel_stops_entire_namespace(self):
  g=self.graph('import time;time.sleep(30)',timeout=20)
  def request():
   end=time.monotonic()+10
   while time.monotonic()<end:
    record=g.backend.records.get(str(g.directory/'work'),{})
    if record.get('containers',{}).get('task',{}).get('status')=='RUNNING':g.cancel.set();return
    time.sleep(.02)
  control=threading.Thread(target=request);control.start();s=g.run();control.join(2)
  self.assertEqual(s['nodes']['work']['reason'],'CANCELLED');self.assertTrue(s['nodes']['work']['tree_stopped'])
 def test_background_setsid_cannot_survive_container_completion(self):
  g=self.graph('import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True);print("OK")')
  n=g.run()['nodes']['work'];self.assertEqual(n['reason'],'BACKGROUND_PROCESS');self.assertNotIn('work',g.results)
  cid=g.backend.records[str(g.resources['work'])]['containers']['task']['id'];self.assertEqual(g.backend._inspect(g.resources['work'],cid)['State']['Pid'],0)
 def test_memory_oom_is_real_and_not_promoted(self):
  g=self.graph('allocation=bytearray(256*1024*1024);print("OK")')
  n=g.run()['nodes']['work'];self.assertEqual(n['reason'],'OOM_KILLED');self.assertNotIn('work',g.results)
 def test_pid_cgroup_refuses_excess_forks(self):
  program='''import os,errno,signal
children=[]
try:
 for i in range(64):
  try:pid=os.fork()
  except OSError as e:
   assert e.errno==errno.EAGAIN;print("OK",flush=True);break
  if pid==0:signal.pause();os._exit(0)
  children.append(pid)
 else:raise RuntimeError("PID limit not enforced")
finally:
 for pid in children:os.kill(pid,signal.SIGTERM)
 for pid in children:os.waitpid(pid,0)
'''
  g=self.graph(program);self.assertEqual(g.run()['status'],'SUCCEEDED')
 def test_dirty_host_retains_corresponding_docker_evidence(self):
  g=self.graph('print("OK")');self.assertEqual(g.run()['status'],'SUCCEEDED');wt=g.resources['work']/'worktree';(wt/'input.txt').write_text('synthetic drift')
  self.assertIn('work',g.cleanup());record=g.backend.records[str(g.resources['work'])];self.assertNotEqual(record['status'],'REMOVED')
  for name in record['volumes'].values():self.assertEqual(g.backend._volume(g.resources['work'],name)['Name'],name)
  git(wt,'restore','input.txt')
 def test_closed_owner_refuses_docker_cleanup(self):
  g=self.graph('print("OK")');self.assertEqual(g.run()['status'],'SUCCEEDED')
  original=g.lock
  class Closed:closed=True
  g.lock=Closed()
  try:
   with self.assertRaises(Rejected):g.cleanup()
   self.assertTrue(all(r['status']!='REMOVED' for r in g.backend.records.values()))
  finally:g.lock=original
 def test_control_plane_failure_retains_active_pool_and_outputs(self):
  g=self.graph('print("OK")');real=self.client.call
  def fail_logs(args,*a,**kw):
   if args[:2]==['container','logs']:raise DockerUnavailable('synthetic lost response after real stop')
   return real(args,*a,**kw)
  with patch.object(self.client,'call',side_effect=fail_logs):
   with self.assertRaises(DockerUnavailable):g.run()
  self.assertTrue((g.pool.area/'quarantine.json').is_file());self.assertEqual(json.loads((g.pool.area/'0.lock').read_text())['state'],'active')
  with self.assertRaises(Rejected):g.cleanup()
  # Explicit test-only external audit: real Engine confirms these owned objects stopped.
  for resource in g.resources.values():
   record=g.backend.records[str(resource)]
   for item in record['containers'].values():self.assertFalse(g.backend._inspect(resource,item['id'])['State']['Running'])
  g.backend.unsafe_resources.clear()  # No automatic pool reset/retry is added to production.

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--docker',type=Path);p.add_argument('--socket');p.add_argument('--image');CONFIG,rest=p.parse_known_args()
 if not all([CONFIG.docker,CONFIG.socket,CONFIG.image]):print('NOT_RUN: explicit local Docker Engine and prepared image required');raise SystemExit(2)
 unittest.main(argv=[sys.argv[0],*rest])
