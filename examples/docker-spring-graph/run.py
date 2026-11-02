"""Same synthetic Spring seed; real Docker isolation on explicit Linux/macOS host."""
from pathlib import Path
import argparse,hashlib,json,platform,shutil,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];CASE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from tools.execution.build_fixture import BuildFixture
from tools.execution.catalog import load_definition
from tools.execution.runtime import git,identity
from tools.execution.docker_io import DockerCLI
from tools.execution.docker_runtime import DockerGraphRun


def sources(catalog):
 names=['tools/execution/runtime.py','tools/execution/catalog.py','tools/execution/build_fixture.py','tools/execution/build_runtime.py','tools/execution/build_cache.py',
        'tools/execution/docker_io.py','tools/execution/docker_runtime.py','tools/docker/worker.py','tools/docker/prewarm.py','tools/docker/Dockerfile',
        'scripts/run_docker_graph.py','examples/docker-spring-graph/run.py','examples/docker-spring-graph/build.py',
        'examples/docker-spring-graph/negative.py','tests/test_docker_io.py','tests/test_docker_backend.py']+list(catalog['source_sha256'])
 names += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'examples/spring-build-graph/seed').rglob('*')) if p.is_file()]
 names += [p.relative_to(ROOT).as_posix() for p in sorted((CASE/'overlay').rglob('*')) if p.is_file()]
 return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(set(names))}


def sanitized_build(receipt):
 pids=receipt.pop('test_jvm_pids');launcher=receipt.pop('launcher_pid')
 assert pids and launcher not in pids
 receipt['distinct_test_jvm']=True
 return receipt


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--docker',required=True,type=Path);p.add_argument('--socket',required=True);p.add_argument('--image',required=True)
 p.add_argument('--host-description',required=True,choices=['macos-vm-engine','linux-native-engine','linux-vm-engine'])
 p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists() or a.output.resolve().is_relative_to(ROOT):p.error('new output outside case required')
 host=platform.system()
 if (host=='Darwin')!=(a.host_description=='macos-vm-engine'):p.error('host description does not match executing OS')
 definition,catalog=load_definition(ROOT/'graphs/docker-spring.json',ROOT);hashes=sources(catalog)
 with BuildFixture('synthetic-docker-spring-') as fixture:
  root=fixture.path;repo=root/'repo';shutil.copytree(ROOT/'examples/spring-build-graph/seed',repo);shutil.copytree(CASE/'overlay',repo,dirs_exist_ok=True)
  git(repo,'init','-b','main');git(repo,'add','.');git(repo,'commit','-m','Independent reused Spring seed');base=git(repo,'rev-parse','HEAD').stdout.strip()
  client=DockerCLI(a.docker,a.socket,root/'docker-client')
  g=DockerGraphRun(repo,base,root/'runs',definition,client,a.image,host_capacity=2)
  try:
   state=g.run()
   if state['status']!='SUCCEEDED':raise RuntimeError('Docker Graph failed; original runtime retained')
   n=state['nodes'];overlap=max(n[x]['started_at'] for x in ['title','tags'])<min(n[x]['ended_at'] for x in ['title','tags'])
   waited=n['integration']['started_at']>=max(n[x]['ended_at'] for x in ['title','tags'])
   merged=all(git(g.resources['integration']/'worktree','merge-base','--is-ancestor',n[x]['commit'],n['integration']['input_commit'],check=False).returncode==0 for x in ['title','tags'])
   commands_overlap=max(n[x]['command_window'][0] for x in ['title','tags'])<min(n[x]['command_window'][1] for x in ['title','tags'])
   assert overlap and commands_overlap and waited and merged and git(repo,'rev-parse','HEAD').stdout.strip()==base
   builds={}
   for name,tools in [('title',['maven']),('tags',['gradle']),('integration',['maven','gradle'])]:
    builds[name]={tool:sanitized_build(g.backend.read_receipt(g.resources[name],tool)) for tool in tools}
    assert n[name]['tree_stopped']
   assert not g.cleanup()
   assert all(r['status']=='REMOVED' for r in g.backend.records.values())
   assert all(not (r/'worktree').exists() for r in g.resources.values())
   report={'kind':'docker_spring_graph_receipt','synthetic':True,'status':'PASSED','host_os':host,'host_description':a.host_description,
     'container_os':'linux','image_id':a.image,'image_arch':g.backend.image_arch,'source_id':identity(hashes),'source_sha256':hashes,'catalog':catalog,
     'instance_count':4,'max_parallel':2,'host_capacity':2,'peak_parallel':state['peak_parallel'],
     'build_commands_overlap':commands_overlap,'independent_workflows_overlap':overlap,'integration_waited':waited,'merged_both_commits':merged,'source_head_unchanged':True,
     'resources_removed':True,'all_owned_containers_and_volumes_removed':True,'graph_probe':state['graph_resource']['probe'],
     'builds':builds,'nodes':{}}
   for name,v in n.items():report['nodes'][name]={k:x for k,x in v.items() if k not in {'started_at','ended_at','container_id','command_window'}}
  finally:g.close()
  fixture.safe_to_remove()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
 print('PASS: real Docker Spring Graph; two build tools concurrent, merged suites/JARs, isolated limits and resource cleanup')
if __name__=='__main__':main()
