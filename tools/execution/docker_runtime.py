"""Linux-container backend for explicit local Docker Engine on Linux/macOS.

Docker is the trusted control plane. Workers get no bind mounts, host socket,
credentials, privileged flags or host namespaces. Worktree promotion stays on host.
"""
from pathlib import Path
import fcntl,hashlib,json,os,platform,re,shutil,socket,threading,time,uuid
from .runtime import (GraphRun,LeasePool,Rejected,atomic,identity,inspect_repo,relative,
                      validate,workspace_identity)
from .docker_io import DockerCLI,DockerUnavailable,source_files,manifest,pack,unpack

OWNER='io.ai-java-workflow.owner'
RESOURCE='io.ai-java-workflow.resource'
IMAGE_LABEL='io.ai-java-workflow.fixture'


class DockerSandbox:
    python='/usr/bin/python3'
    def __init__(self,client,image,pool,memory_mb=2048,cpus=2,pids=256,seed_cache=True):
        if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise Rejected('immutable local image ID required')
        if type(memory_mb) is not int or not 64<=memory_mb<=8192:raise Rejected('memory limit required')
        if type(pids) is not int or not 16<=pids<=512:raise Rejected('PID limit required')
        if type(cpus) not in {int,float} or not .25<=cpus<=8:raise Rejected('CPU limit required')
        if type(seed_cache) is not bool:raise Rejected('cache mode must be explicit boolean')
        self.seed_cache=seed_cache
        self.client=client;self.image=image;self.pool=pool;self.memory=memory_mb*1048576;self.cpus=cpus;self.pids=pids
        self.unsafe_resources=set();self.records={};self.inputs={};self.host_input_ids={}
        kind=client.call(['info','--format','{{.OSType}} {{.CgroupVersion}}'])[1].decode().strip()
        if kind!='linux 2':raise Rejected('Linux Docker Engine with cgroups v2 required')
        image_info=client.json(['image','inspect',image,'--format','{{json .}}'])
        if (image_info['Id']!=image or image_info['Os']!='linux'
                or (image_info['Config'].get('Labels') or {}).get(IMAGE_LABEL)!='spring-build-v1'
                or image_info['Config'].get('Volumes')
                or (image_info['Config'].get('Labels') or {}).get('io.ai-java-workflow.worker-sha256')!=hashlib.sha256((Path(__file__).resolve().parents[1]/'docker/worker.py').read_bytes()).hexdigest()):
            raise Rejected('unverified build image or implicit image volumes')
        self.image_arch=image_info['Architecture']

    def _save(self,resource):atomic(resource/'docker-state.json',self.records[str(resource)])

    def _quarantine(self,resource):
        self.unsafe_resources.add(str(resource))
        atomic(self.pool.area/'quarantine.json',{'reason':'Docker resource state unknown'})
        self.records[str(resource)]['status']='UNKNOWN';self._save(resource)

    def prepare(self,resource,common):
        area=resource/'sandbox';area.mkdir()
        for name in ['home','tmp']:(area/name).mkdir()
        prefix='ajw-'+uuid.uuid4().hex
        record={'owner':uuid.uuid4().hex,'resource':prefix,'status':'PREPARING','volumes':{},'containers':{}}
        self.records[str(resource)]=record;self.inputs[str(resource)]=source_files(resource/'worktree');self.host_input_ids[str(resource)]=workspace_identity(resource/'worktree')
        for kind in ['workspace','home','tmp']:record['volumes'][kind]=prefix+'-'+kind
        self._save(resource)  # Names and ownership exist before any daemon-side allocation.
        try:
            for name in record['volumes'].values():
                self.client.call(['volume','create','--label',OWNER+'='+record['owner'],'--label',RESOURCE+'='+prefix,name])
                self._volume(resource,name)
            record['status']='PREPARED';self._save(resource)
        except BaseException:self._quarantine(resource);raise

    def _volume(self,resource,name):
        record=self.records[str(resource)];value=self.client.json(['volume','inspect',name])[0]
        labels=value.get('Labels') or {}
        if value['Name']!=name or labels.get(OWNER)!=record['owner'] or labels.get(RESOURCE)!=record['resource']:
            raise Rejected('volume ownership mismatch')
        return value

    def _inspect(self,resource,cid):
        record=self.records[str(resource)];value=self.client.json(['container','inspect',cid])[0]
        labels=value['Config'].get('Labels') or {}
        if (value['Id']!=cid or labels.get(OWNER)!=record['owner'] or labels.get(RESOURCE)!=record['resource']):
            raise Rejected('container ownership mismatch')
        return value

    def _policy(self,resource,value):
        record=self.records[str(resource)];h=value['HostConfig'];config=value['Config']
        expected={'workspace':'/workspace','home':'/sandbox/home','tmp':'/sandbox/tmp'}
        mounts=value['Mounts']
        if (len(mounts)!=3 or any(m['Type']!='volume' or not m['RW'] for m in mounts)
                or {m['Name']:m['Destination'] for m in mounts}!={record['volumes'][k]:v for k,v in expected.items()}):
            raise Rejected('unexpected container mounts')
        if (value['Image']!=self.image or config['User']!='1000:1000' or config['WorkingDir']!='/workspace'
                or not h['ReadonlyRootfs'] or h['Privileged'] or h['NetworkMode']!='none'
                or h['PidMode'] not in {'','private'} or h['IpcMode']!='private' or h['CgroupnsMode']!='private'
                or h.get('Binds') or h.get('Devices') or h.get('PortBindings') or h.get('CapAdd')
                or [x.upper() for x in h.get('CapDrop',[])]!=['ALL']
                or not any(x.split(':')[0]=='no-new-privileges' for x in h.get('SecurityOpt',[]))
                or h['Memory']!=self.memory or h['MemorySwap']!=self.memory
                or h['NanoCpus']!=int(self.cpus*1000000000) or h['PidsLimit']!=self.pids
                or not h.get('Init') or h['AutoRemove'] or h['RestartPolicy']['Name']!='no'):
            raise Rejected('container runtime policy mismatch')

    def _create(self,resource,mode,spec):
        record=self.records[str(resource)];name=record['resource']+'-'+mode
        if mode in record['containers']:raise Rejected('execution phase cannot replay')
        record['containers'][mode]={'name':name,'id':None,'status':'INTENT'};self._save(resource)
        args=['container','create','--name',name,'--label',OWNER+'='+record['owner'],'--label',RESOURCE+'='+record['resource'],
              '--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges',
              '--network','none','--ipc','private','--cgroupns','private','--init','--restart','no',
              '--memory',str(self.memory),'--memory-swap',str(self.memory),'--cpus',str(self.cpus),'--pids-limit',str(self.pids),
              '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=1','--log-opt','compress=false',
              '--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777','--workdir','/workspace',
              '--entrypoint','/usr/bin/python3']
        for kind,target in [('workspace','/workspace'),('home','/sandbox/home'),('tmp','/sandbox/tmp')]:
            self._volume(resource,record['volumes'][kind])
            args+=['--mount','type=volume,src='+record['volumes'][kind]+',dst='+target]
        args += [self.image,'-I','-B','/opt/ajw/worker.py',mode,json.dumps(spec,separators=(',',':'))]
        cid=self.client.call(args)[1].decode().strip()
        if not re.fullmatch('[0-9a-f]{64}',cid):raise DockerUnavailable('unconfirmed created container identity')
        record['containers'][mode].update(id=cid,status='CREATED');self._save(resource)
        value=self._inspect(resource,cid);self._policy(resource,value)
        if mode=='probe':self.client.call(['container','cp','-a','-',cid+':/workspace'],data=pack(self.inputs[str(resource)]))
        return cid

    def execute(self,resource,command,timeout,cancel,extra_env=None,log_name='command'):
        record=self.records[str(resource)];mode='probe' if log_name=='probe' else 'task'
        spec={'timeout':timeout,'command':command,'memory':self.memory,'cpus':self.cpus,'pids':self.pids,'copy_cache':self.seed_cache}
        if extra_env:spec.update(extra_env)
        lease=None;cid=None;stopped=False;started=time.monotonic();began=None;reason=None
        try:
            try:lease=self.pool.acquire(cancel,started+timeout)
            except Rejected:
                reason='POOL_QUARANTINED' if (self.pool.area/'quarantine.json').exists() else 'CANCELLED' if cancel.is_set() else 'TIMEOUT'
                return {'exit':None,'reason':reason,'text':'','log_sha256':None,'started_at':None,'ended_at':None,'tree_stopped':True}
            cid=self._create(resource,mode,spec)
            if cancel.is_set():reason='CANCELLED'
            elif time.monotonic()-started>=timeout:reason='TIMEOUT'
            if reason is None:
                began=time.monotonic();self.client.call(['container','start',cid]);record['containers'][mode]['status']='RUNNING';self._save(resource)
            while True:
                value=self._inspect(resource,cid)
                if not value['State']['Running']:stopped=True;break
                if cancel.is_set():reason='CANCELLED'
                elif time.monotonic()-started>=timeout:reason='TIMEOUT'
                if reason:
                    self.client.call(['container','kill','--signal','KILL',cid])
                time.sleep(.03)
            record['containers'][mode]['status']='STOPPED';self._save(resource)
            # inspect stopped before logs/cp and before a host lease may be released.
            _,out,err=self.client.call(['container','logs',cid],limit=65536);log=out+err
            if len(log)>65536:raise DockerUnavailable('combined container output limit')
            (resource/'sandbox'/(log_name+'.log')).write_bytes(log)
            text=log.decode('utf-8',errors='replace');prefix='AJW_CONTAINER_RESULT='
            lines=[line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
            receipt=json.loads(lines[0]) if len(lines)==1 else {}
            code=value['State']['ExitCode']
            if value['State'].get('OOMKilled'):reason='OOM_KILLED'
            elif code==124:reason='TIMEOUT'
            elif reason is None:reason=receipt.get('reason') or (None if receipt else 'MISSING_CONTAINER_RECEIPT')
            if receipt.get('exit')!=0 and reason is None:reason='COMMAND_FAILED'
            return {'exit':code,'reason':reason,'text':text,'log_sha256':hashlib.sha256(log).hexdigest(),
                    'started_at':began,'ended_at':time.monotonic(),'tree_stopped':True,
                    'container_workspace':receipt.get('workspace'),'probe':receipt.get('probe'),
                    'container_id':cid,'command_window':receipt.get('command_window'),'memory_limit':self.memory,'cpu_limit':self.cpus,'pids_limit':self.pids}
        except BaseException:
            # Even if a create/start response was lost, never assume absence or reuse capacity.
            if cid:
                try:
                    value=self._inspect(resource,cid)
                    if value['State']['Running']:self.client.call(['container','kill','--signal','KILL',cid])
                    stopped=not self._inspect(resource,cid)['State']['Running']
                except Exception:stopped=False
            stopped=False  # Any interrupted daemon operation keeps ACTIVE until explicit inspection.
            self._quarantine(resource)
            raise
        finally:
            if lease:
                if stopped:self.pool.release(lease)
                elif cid is None and not record['containers'].get(mode):self.pool.release(lease)
                else:
                    self._quarantine(resource)
                    fcntl.flock(lease,fcntl.LOCK_UN);lease.close()  # ACTIVE remains durable.

    def probe(self,resource,common):
        canary=resource.parent/(resource.name+'-host-canary');canary.write_text('independent host canary')
        server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
        try:
            result=self.execute(resource,[],30,threading.Event(),{'host_canary':str(canary),'host_port':server.getsockname()[1]},'probe')
            if result['exit']!=0 or result['reason'] or not result['probe'] or not all(v is True for v in result['probe'].values()):
                raise Rejected('real container isolation probe failed')
            if manifest(self.export(resource,result['container_id']))!=manifest(self.inputs[str(resource)]):raise Rejected('probe changed inputs')
            if canary.read_text()!='independent host canary':raise Rejected('host canary changed')
            return result['probe']
        finally:server.close();canary.unlink(missing_ok=True)

    def export(self,resource,cid):
        if self._inspect(resource,cid)['State']['Running']:raise Rejected('cannot export running container')
        data=self.client.call(['container','cp',cid+':/workspace/.','-'])[1]
        return unpack(data)

    def read_receipt(self,resource,tool):
        if tool not in {'maven','gradle'}:raise Rejected('unknown report')
        cid=self.records[str(resource)]['containers']['task']['id']
        if self._inspect(resource,cid)['State']['Running']:raise Rejected('container still running')
        data=self.client.call(['container','cp',cid+':/sandbox/tmp/'+tool+'-receipt.json','-'],limit=1048576)[1]
        files=unpack(data)
        if set(files)!={tool+'-receipt.json'}:raise Rejected('unexpected report archive')
        return json.loads(files[tool+'-receipt.json']['data'])

    def check_stopped(self,resource):
        if str(resource) in self.unsafe_resources:raise Rejected('unknown Docker resources retained')
        record=self.records[str(resource)]
        for item in record['containers'].values():
            if item.get('status')=='REMOVED':continue
            if not item.get('id'):raise Rejected('unconfirmed container retained')
            if self._inspect(resource,item['id'])['State']['Running']:raise Rejected('live container retained')
        for name in record['volumes'].values():
            if name not in record.get('removed_volumes',[]):self._volume(resource,name)

    def cleanup(self,resource):
        if str(resource) in self.unsafe_resources:raise Rejected('unknown Docker resources retained')
        record=self.records[str(resource)]
        for phase,item in record['containers'].items():
            if item.get('status')=='REMOVED':continue
            if not item.get('id'):raise Rejected('unconfirmed container retained')
            value=self._inspect(resource,item['id'])
            if value['State']['Running']:raise Rejected('live container retained')
            self.client.call(['container','rm',item['id']]);item['status']='REMOVED';self._save(resource)
        removed=record.setdefault('removed_volumes',[])
        for name in record['volumes'].values():
            if name in removed:continue
            self._volume(resource,name);self.client.call(['volume','rm',name]);removed.append(name);self._save(resource)
        record['status']='REMOVED';self._save(resource)


class DockerGraphRun(GraphRun):
    """Shared broker/state methods with explicit portable admission (no Seatbelt init)."""
    def __init__(self,repo,base,runtime_root,definition,client,image,host_capacity=None,limits=None):
        if platform.system() not in {'Darwin','Linux'}:raise Rejected('Linux/macOS Docker host required')
        self.nodes=validate(definition);self.repo,self.common,self.base=inspect_repo(repo,base)
        self.config_id=hashlib.sha256((self.common/'config').read_bytes()).hexdigest();self.root=Path(runtime_root).resolve()
        if self.root.is_relative_to(self.repo) or self.repo.is_relative_to(self.root):raise Rejected('runtime root must be outside source')
        if self.root in {Path('/'),Path.home(),Path('/Users'),Path('/home')}:raise Rejected('overbroad runtime root')
        if self.root.exists() and any(self.root.iterdir()) and not (self.root/'.execution-root').is_file():raise Rejected('unrelated runtime files')
        self.root.mkdir(parents=True,exist_ok=True);marker=self.root/'.execution-root'
        if not marker.exists():marker.write_text('execution-root-v1\n')
        if marker.read_text()!='execution-root-v1\n':raise Rejected('unknown runtime root')
        self.pool=LeasePool(self.root,host_capacity,definition['max_parallel'])
        if definition['max_parallel']>self.pool.capacity:raise Rejected('Graph exceeds host pool')
        self.backend=DockerSandbox(client,image,self.pool,**(limits or {}));self.directory=self.root/definition['graph_id']
        self.directory.mkdir();os.chmod(self.directory,0o700);self.lock=(self.directory/'owner.lock').open('x');fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.definition=definition;self.java_home=None;self.cancel=threading.Event();self.resources={};self.results={};self.expected_heads={};self.git_pointers={};self.input_ids={}
        self.state={'graph_id':definition['graph_id'],'definition_id':identity(definition),'base_commit':self.base,'status':'CREATED',
                    'max_parallel':definition['max_parallel'],'host_capacity':self.pool.capacity,'peak_parallel':0,
                    'nodes':{n:{'status':'PENDING','run_id':definition['graph_id']+'/'+n,'parent_run_id':definition['graph_id']} for n in self.nodes},
                    'events':[],'cleanup':'not_requested','execution_mode':'docker_linux_container','image_id':image}
        self._save()

    def _prepare(self,name,deps):
        resource,branch,probe=super()._prepare(name,deps);self.input_ids[name]=self.backend.host_input_ids[str(resource)]
        return resource,branch,probe

    def _execute(self,node,resource):
        command=[self.backend.python if x=='{python}' else x for x in node['command']]
        result=self.backend.execute(resource,command,node['timeout'],self.cancel)
        result['success']=result['exit']==0 and result['reason'] is None and node['success_pattern'][1:-1] in result['text'].splitlines()
        if result['success']:
            name=node['id'];wt=resource/'worktree';files=self.backend.export(resource,result['container_id'])
            if manifest(files)!=result['container_workspace']:raise Rejected('container output drift')
            if workspace_identity(wt)!=self.input_ids[name]:raise Rejected('host input drift during isolated execution')
            baseline=self.backend.inputs[str(resource)];allowed=set(node['allowed_write'])
            if any(files.get(n)!=baseline.get(n) for n in set(files)|set(baseline) if n not in allowed):raise Rejected('container logical write set exceeded')
            for n in allowed:
                relative(n);target=wt/n
                if n in files:
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(files[n]['data']);target.chmod(files[n]['mode'])
                elif target.exists():target.unlink()
        result.pop('container_workspace',None);result.pop('probe',None)
        result['workspace_id']=workspace_identity(resource/'worktree')
        return result

    def _save(self):
        if (self.state.get('cleanup')=='worktrees_removed'
                and any(r['status']!='REMOVED' for r in self.backend.records.values())):
            self.state['cleanup']='docker_cleanup_pending'
        super()._save()

    def cleanup(self,discard_failed=False):
        if self.lock.closed:raise Rejected('cleanup requires live owner lease')
        if self.state['status'] in {'CREATED','RUNNING','UNKNOWN'} or self.backend.unsafe_resources:raise Rejected('unknown/live Docker execution retained')
        retained=[];eligible={}
        for name,resource in self.resources.items():
            if name!='graph' and self.state['nodes'][name]['status']!='SUCCEEDED' and not discard_failed:retained.append(name);continue
            self.backend.check_stopped(resource);eligible[name]=resource
        all_resources=self.resources
        try:
            self.resources=eligible;host_retained=super().cleanup();retained+=host_retained
        finally:self.resources=all_resources
        # Only after the host broker has actually removed a clean, unchanged
        # worktree may its corresponding original Docker outputs be discarded.
        for name,resource in eligible.items():
            if name not in host_retained and self.state.get('resource_cleanup',{}).get(name)=='cleaned':
                self.backend.cleanup(resource)
        self.state['cleanup']='retained_outputs' if retained else 'worktrees_removed'
        self.state['retained']=retained;self._save()
        return retained
