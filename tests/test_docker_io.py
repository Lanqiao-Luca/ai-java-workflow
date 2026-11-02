"""Portable parser/ownership policy tests; no Docker daemon or real sandbox claim."""
from pathlib import Path
from unittest.mock import patch
import io,json,sys,tarfile,tempfile,unittest
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.execution.docker_io import pack,unpack,manifest,source_files,DockerCLI
from tools.execution.docker_runtime import DockerSandbox,OWNER,RESOURCE
from tools.execution.runtime import Rejected

class DockerIOTests(unittest.TestCase):
 def test_source_archive_roundtrip_and_uid(self):
  data={'src/App.java':{'data':b'independent fixture','mode':0o644}}
  blob=pack(data);self.assertEqual(unpack(blob),data)
  with tarfile.open(fileobj=io.BytesIO(blob)) as t:
   self.assertEqual(t.getmembers()[0].uid,1000);self.assertGreater(t.getmembers()[0].mtime,0)  # Maven resource copying must see a real timestamp.
 def archive(self,name,kind=tarfile.REGTYPE,data=b'a',mode=0o644):
  out=io.BytesIO()
  with tarfile.open(fileobj=out,mode='w') as tar:
   m=tarfile.TarInfo(name);m.type=kind;m.linkname='outside';m.mode=mode;m.size=len(data) if kind==tarfile.REGTYPE else 0
   tar.addfile(m,io.BytesIO(data) if m.size else None)
  return out.getvalue()
 def test_tar_traversal_absolute_hidden_links_and_devices_rejected(self):
  for blob in [self.archive('../escape'),self.archive('/escape'),self.archive('.git/config'),self.archive('link',tarfile.SYMTYPE),self.archive('link',tarfile.LNKTYPE),self.archive('device',tarfile.CHRTYPE),self.archive('setuid',mode=0o4755)]:
   with self.subTest(blob=blob[:12]):
    with self.assertRaises(Rejected):unpack(blob)
 def test_duplicate_and_oversize_archives_rejected(self):
  out=io.BytesIO()
  with tarfile.open(fileobj=out,mode='w') as t:
   for i in range(2):m=tarfile.TarInfo('same.txt');m.size=1;t.addfile(m,io.BytesIO(b'a'))
  with self.assertRaises(Rejected):unpack(out.getvalue())
  with self.assertRaises(Rejected):unpack(b'0'*(8*1024*1024+1))
 def test_source_git_is_excluded_but_symlink_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'.git').write_text('private pointer');(root/'input.txt').write_text('synthetic')
   self.assertEqual(set(source_files(root)),{'input.txt'})
   (root/'link').symlink_to(root/'input.txt')
   with self.assertRaises(Rejected):source_files(root)
 def test_remote_socket_and_existing_configuration_rejected(self):
  with self.assertRaises(Rejected):DockerCLI(sys.executable,'tcp://remote.invalid:2376','unused-config')
 def test_image_and_resource_limits_are_mandatory(self):
  for image,options in [('latest',{}),('sha256:'+'a'*64,{'memory_mb':0}),('sha256:'+'a'*64,{'pids':-1}),('sha256:'+'a'*64,{'cpus':0})]:
   with self.assertRaises(Rejected):DockerSandbox(None,image,None,**options)
 def test_container_policy_rejects_host_access_and_missing_limits(self):
  s=object.__new__(DockerSandbox);s.image='sha256:'+'a'*64;s.memory=64*1048576;s.cpus=1;s.pids=32
  resource=Path('/synthetic-resource');s.records={str(resource):{'volumes':{'workspace':'w','home':'h','tmp':'t'}}}
  value={'Image':s.image,'Config':{'User':'1000:1000','WorkingDir':'/workspace'},'Mounts':[{'Type':'volume','RW':True,'Name':n,'Destination':d} for n,d in [('w','/workspace'),('h','/sandbox/home'),('t','/sandbox/tmp')]],'HostConfig':{'ReadonlyRootfs':True,'Privileged':False,'NetworkMode':'none','PidMode':'','IpcMode':'private','CgroupnsMode':'private','CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'Memory':s.memory,'MemorySwap':s.memory,'NanoCpus':1000000000,'PidsLimit':32,'Init':True,'AutoRemove':False,'RestartPolicy':{'Name':'no'}}}
  s._policy(resource,value)
  for key,bad in [('Privileged',True),('NetworkMode','host'),('PidMode','host'),('Memory',0),('PidsLimit',-1),('CapAdd',['SYS_ADMIN']),('PortBindings',{'80/tcp':[]})]:
   old=value['HostConfig'].get(key);value['HostConfig'][key]=bad
   with self.assertRaises(Rejected):s._policy(resource,value)
   if old is None:value['HostConfig'].pop(key)
   else:value['HostConfig'][key]=old
 def test_unowned_volume_cannot_be_deleted(self):
  class Client:
   def json(self,args):return [{'Name':'volume','Labels':{OWNER:'different',RESOURCE:'resource'}}]
  s=object.__new__(DockerSandbox);s.client=Client();s.records={'r':{'owner':'mine','resource':'resource'}}
  with self.assertRaises(Rejected):s._volume(Path('r'),'volume')

if __name__=='__main__':unittest.main()
