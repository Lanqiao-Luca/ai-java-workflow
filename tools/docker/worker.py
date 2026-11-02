"""Immutable image entrypoint. Only instance namespaces/volumes, no Docker API."""
from pathlib import Path
import ctypes,errno,hashlib,json,os,shutil,socket,subprocess,sys,time,signal

PREFIX='AJW_CONTAINER_RESULT='

def alive():
    own={1,os.getpid()};result=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit() or int(path.name) in own:continue
        try:
            # Comm may contain spaces/parentheses; state follows the last closing parenthesis.
            state=(path/'stat').read_text().rsplit(')',1)[1].split()[0]
            if state!='Z':result.append(int(path.name))
        except FileNotFoundError:pass
    return result


def snapshot():
    files={};root=Path('/workspace')
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if p.is_symlink() or any(x.startswith('.') for x in p.relative_to(root).parts):raise RuntimeError('unsafe output object')
        if p.is_dir():continue
        if not p.is_file() or p.stat().st_size>1048576 or len(files)>=256:raise RuntimeError('output limits')
        files[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&0o777}
    return files


def probe(values):
    results={}
    p=Path('/workspace/probe-positive');p.write_text('synthetic');p.unlink();results['workspace_write']=True
    for key,path in [('host_file_absent',values['host_canary']),('git_pointer_absent','/workspace/.git'),('docker_socket_absent','/var/run/docker.sock')]:
        assert not Path(path).exists();results[key]=True
    root_mounts=[line.split()[5].split(',') for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]=='/']
    assert len(root_mounts)==1 and 'ro' in root_mounts[0]  # A UID permission denial alone is not proof of read-only root.
    try:Path('/forbidden-root-write').write_text('denied');raise RuntimeError('root writable')
    except OSError as e:assert e.errno in {errno.EROFS,errno.EACCES};results['readonly_root']=True
    assert os.getuid()==1000 and os.getgid()==1000;results['non_root']=True
    status={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
    assert int(status['CapEff'],16)==0 and status['NoNewPrivs']=='1' and status['Seccomp']=='2'
    results['capabilities_dropped']=True;results['no_new_privileges']=True;results['seccomp_filter']=True
    assert sorted(p.name for p in Path('/sys/class/net').iterdir())==['lo'];results['only_loopback_interface']=True
    try:socket.create_connection(('192.0.2.1',9),timeout=.5);raise RuntimeError('network route available')
    except OSError:results['external_network_denied']=True
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
    c=socket.create_connection(server.getsockname(),timeout=1);a,_=server.accept();c.close();a.close();server.close();results['own_loopback_ipc']=True
    try:socket.create_connection(('127.0.0.1',values['host_port']),timeout=.5);raise RuntimeError('host loopback visible')
    except OSError:results['host_loopback_isolated']=True
    cg=Path('/sys/fs/cgroup');memory=(cg/'memory.max').read_text().strip();pids=(cg/'pids.max').read_text().strip();quota=(cg/'cpu.max').read_text().split()
    assert int(memory)==values['memory'] and int(pids)==values['pids'] and quota[0]!='max'
    assert int(quota[0])/int(quota[1])==values['cpus']
    results['memory_cgroup_limit']=True;results['pids_cgroup_limit']=True;results['cpu_cgroup_limit']=True
    # A detached child remains in this namespace and is waited for before success.
    child=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(.1)'],start_new_session=True)
    child.wait();assert child.returncode==0;results['fork_and_setsid_succeeded']=True
    assert not alive();results['namespace_drained']=True
    return results


def main():
    mode=sys.argv[1];spec=json.loads(sys.argv[2]);began=time.monotonic();deadline=began+spec['timeout']
    # Covers cache copy and probes as well as the child command, even if host polling stops.
    signal.signal(signal.SIGALRM,lambda *_:os._exit(124))
    signal.setitimer(signal.ITIMER_REAL,spec['timeout'])
    if mode=='probe':
        report={'exit':0,'reason':None,'probe':probe(spec),'workspace':snapshot()}
    else:
        if mode!='task':raise RuntimeError('unsupported entry mode')
        if spec.get('copy_cache',True):
            for tool in ['maven','gradle']:shutil.copytree('/opt/cache-seed/'+tool,'/sandbox/home/'+tool)
        env={'PATH':'/usr/bin:/bin','HOME':'/sandbox/home','TMPDIR':'/sandbox/tmp','LC_ALL':'C.UTF-8',
             'JAVA_HOME':'/opt/java/openjdk','MAVEN_HOME':'/opt/maven','GRADLE_HOME':'/opt/gradle',
             'GRADLE_USER_HOME':'/sandbox/home/gradle','PYTHONDONTWRITEBYTECODE':'1'}
        events=Path('/sys/fs/cgroup/memory.events')
        def oom_count():return int(dict(line.split() for line in events.read_text().splitlines()).get('oom_kill','0'))
        oom_before=oom_count()
        command_started=time.monotonic()
        process=subprocess.Popen(spec['command'],cwd='/workspace',env=env)
        reason=None
        while process.poll() is None:
            if time.monotonic()>=deadline:
                # Exiting the PID-namespace init chain stops all descendants, including setsid.
                print(PREFIX+json.dumps({'exit':124,'reason':'TIMEOUT'}),flush=True);os._exit(124)
            time.sleep(.02)
        process.wait();command_ended=time.monotonic();drain=min(deadline,time.monotonic()+3)
        while alive() and time.monotonic()<drain:time.sleep(.02)
        if alive():reason='BACKGROUND_PROCESS'
        oom_kills=oom_count()-oom_before
        if oom_kills:reason='OOM_KILLED'
        report={'exit':process.returncode,'reason':reason,'workspace':snapshot(),'oom_kills':oom_kills,'command_window':[command_started,command_ended]}
    print(PREFIX+json.dumps(report,sort_keys=True),flush=True)
    return 0 if report['exit']==0 and report['reason'] is None else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(PREFIX+json.dumps({'exit':1,'reason':type(exc).__name__}),flush=True);raise SystemExit(1)
