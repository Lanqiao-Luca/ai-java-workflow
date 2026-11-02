"""Reuse the real Spring red baseline and missing-dependency controls in Docker."""
from pathlib import Path
import argparse,json,runpy,shutil,sys,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];CASE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from tools.execution.build_fixture import BuildFixture
from tools.execution.docker_io import DockerCLI,unpack
from tools.execution.docker_runtime import DockerGraphRun
from tools.execution.runtime import git,identity
from tools.execution.catalog import load_definition

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--docker',required=True,type=Path);p.add_argument('--socket',required=True);p.add_argument('--image',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists() or a.output.resolve().is_relative_to(ROOT):p.error('new output outside case required')
 _,catalog=load_definition(ROOT/'graphs/docker-spring.json',ROOT);hashes=runpy.run_path(str(CASE/'run.py'))['sources'](catalog)
 with BuildFixture('synthetic-docker-negatives-') as fixture:
  root=fixture.path;repo=root/'repo';shutil.copytree(ROOT/'examples/spring-build-graph/seed',repo);shutil.copytree(CASE/'overlay',repo,dirs_exist_ok=True);git(repo,'init','-b','main');git(repo,'add','.');git(repo,'commit','-m','Reused synthetic red baseline');base=git(repo,'rev-parse','HEAD').stdout.strip()
  client=DockerCLI(a.docker,a.socket,root/'client');results={}
  for mode in ['red_baseline','missing_dependency']:
   command=['{python}','-I','-B','-c',"import runpy;n=runpy.run_path('build_task.py');n['build']('maven','title');print('OK')"] if mode=='red_baseline' else ['{python}','-I','-B','build_task.py','title','maven']
   definition={'graph_id':mode.replace('_','-'),'max_parallel':1,'nodes':[
    {'id':'title','depends_on':[],'command':command,'allowed_write':['src/main/java/example/graph/TitleApi.java'],'success_pattern':'^OK$','timeout':120},
    {'id':'integration','depends_on':['title'],'command':['{python}','-c','print("OK")'],'allowed_write':[],'success_pattern':'^OK$','timeout':10}]}
   g=DockerGraphRun(repo,base,root/'runs',definition,client,a.image,limits={'seed_cache':mode=='red_baseline'})
   try:
    s=g.run();n=s['nodes']['title'];assert n['exit']!=0 and n['status']!='SUCCEEDED' and s['nodes']['integration']['status']=='BLOCKED'
    assert 'title' not in g.results and n['tree_stopped'] and git(repo,'rev-parse','HEAD').stdout.strip()==base
    row={'status':'EXPECTED_FAILURE','exit':n['exit'],'dependent':'BLOCKED','candidate_promoted':False,'tree_stopped':True,'source_head_unchanged':True}
    if mode=='red_baseline':
     cid=g.backend.records[str(g.resources['title'])]['containers']['task']['id'];name='TEST-example.graph.TitleApiTest.xml'
     raw=client.call(['container','cp',cid+':/sandbox/tmp/maven-output/surefire-reports/'+name,'-'],limit=1048576)[1]
     data=unpack(raw)[name]['data'];assert b'<!DOCTYPE' not in data and b'<!ENTITY' not in data
     attrs=ET.fromstring(data).attrib;row['junit']={k:int(attrs.get(k,0)) for k in ['tests','failures','errors','skipped']}
     assert row['junit']=={'tests':3,'failures':2,'errors':0,'skipped':0}
    else:
     text=(g.resources['title']/'sandbox/command.log').read_text();assert 'offline' in text.lower() and ('Non-resolvable parent POM' in text or 'not been downloaded' in text)
     row['offline_dependency_failure']=True
    assert not g.cleanup(discard_failed=True);row['known_synthetic_outputs_explicitly_removed']=True;results[mode]=row
   finally:g.close()
  fixture.safe_to_remove()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'synthetic':True,'status':'PASSED','source_id':identity(hashes),'source_sha256':hashes,'controls':results},indent=2)+'\n')
 print('PASS: same real red and offline-missing-dependency controls reject promotion in Docker')
if __name__=='__main__':main()
