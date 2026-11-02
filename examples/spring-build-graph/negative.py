"""Real offline Maven negative controls: broken baseline and missing public dependency."""
from pathlib import Path
import argparse,json,shutil,sys,tempfile,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];CASE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from tools.execution.build_runtime import BuildGraphRun
from tools.execution.build_cache import seal
from tools.execution.runtime import git

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['java-home','maven-home','prepared-home','output']:p.add_argument('--'+name,required=True,type=Path)
 a=p.parse_args()
 if a.output.exists() or a.output.resolve().is_relative_to(CASE):p.error('output must be new and outside case')
 tools={'JAVA_HOME':a.java_home.resolve(strict=True),'MAVEN_HOME':a.maven_home.resolve(strict=True)}
 results={}
 with tempfile.TemporaryDirectory(prefix='synthetic-build-negative-') as directory:
  root=Path(directory).resolve();repo=root/'repo';shutil.copytree(CASE/'seed',repo);git(repo,'init','-b','main');git(repo,'add','.');git(repo,'commit','-m','Independent red fixture');base=git(repo,'rev-parse','HEAD').stdout.strip()
  empty=root/'empty-public-cache';empty.mkdir();seal(empty,'maven')
  for mode in ['red_baseline','missing_dependency']:
   command=['{python}','-I','-B','-c',"import runpy;n=runpy.run_path('build_task.py');n['build']('maven','title');print('OK')"] if mode=='red_baseline' else ['{python}','-I','-B','build_task.py','title','maven']
   definition={'graph_id':mode.replace('_','-'),'max_parallel':1,'nodes':[
    {'id':'title','depends_on':[],'command':command,'allowed_write':['src/main/java/example/graph/TitleApi.java'],'success_pattern':'^OK$','timeout':120},
    {'id':'integration','depends_on':['title'],'command':['{python}','-c','print("OK")'],'allowed_write':[],'success_pattern':'^OK$','timeout':10}]}
   seed=a.prepared_home.resolve(strict=True)/'maven' if mode=='red_baseline' else empty
   g=BuildGraphRun(repo,base,root/'runs',definition,tool_roots=list(tools.values()),java_home=tools['JAVA_HOME'],host_capacity=1,toolchain=tools,cache_seeds={'maven':seed})
   try:
    state=g.run();node=state['nodes']['title']
    assert state['status']=='INCOMPLETE' and node['exit']!=0 and node['status']!='SUCCEEDED'
    assert state['nodes']['integration']['status']=='BLOCKED' and 'title' not in g.results
    assert node['tree_stopped'] and git(repo,'rev-parse','HEAD').stdout.strip()==base
    row={'status':'EXPECTED_FAILURE','exit':node['exit'],'candidate_promoted':False,'dependent':'BLOCKED','tree_stopped':True,'source_head_unchanged':True}
    reports=list((g.resources['title']/'sandbox/tmp/maven-output/surefire-reports').glob('TEST-*.xml'))
    if mode=='red_baseline':
     attrs=ET.parse(reports[0]).getroot().attrib;row['junit']={k:int(attrs.get(k,0)) for k in ['tests','failures','errors','skipped']}
     assert row['junit']=={'tests':3,'failures':2,'errors':0,'skipped':0}
    else:
     assert not reports
     log=(g.resources['title']/'sandbox/command.log').read_text()
     assert 'offline' in log.lower() and ('Non-resolvable parent POM' in log or 'not been downloaded' in log)
     row['offline_dependency_failure']=True
    results[mode]=row
   finally:g.close()
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'synthetic':True,'status':'PASSED','controls':results},indent=2)+'\n')
 print('PASS: real red tests and missing offline dependency rejected; descendants blocked, no promotion')
if __name__=='__main__':main()
