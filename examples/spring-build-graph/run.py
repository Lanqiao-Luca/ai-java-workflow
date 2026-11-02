"""Offline Spring Boot Graph: Maven and Gradle features, then dual-tool merged tests."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
CASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.execution.build_runtime import BuildGraphRun
from tools.execution.build_cache import verify
from tools.execution.catalog import load_definition
from tools.execution.runtime import git,identity

def sources(catalog):
    names=['tools/execution/runtime.py','tools/execution/catalog.py','tools/execution/build_runtime.py',
           'tools/execution/build_cache.py','scripts/run_build_graph.py','examples/spring-build-graph/run.py',
           'examples/spring-build-graph/prepare.py','examples/spring-build-graph/negative.py','tests/test_build_execution.py','standards/java-build-sandbox.md']+list(catalog['source_sha256'])
    names += [p.relative_to(ROOT).as_posix() for p in sorted((CASE/'seed').rglob('*')) if p.is_file()]
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(set(names))}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['java-home','maven-home','gradle-home','prepared-home']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.output and (a.output.exists() or a.output.resolve().is_relative_to(CASE)):p.error('output must be a new file outside case')
    toolchain={name.upper().replace('-','_'):getattr(a,name.replace('-','_')).resolve(strict=True) for name in ['java-home','maven-home','gradle-home']}
    seeds={t:a.prepared_home.resolve(strict=True)/t for t in ['maven','gradle']}
    cache_ids={t:verify(path,t) for t,path in seeds.items()}
    definition,catalog=load_definition(ROOT/'graphs/spring-build.json',ROOT)
    hashes=sources(catalog)
    with tempfile.TemporaryDirectory(prefix='synthetic-spring-graph-') as directory:
        root=Path(directory).resolve();repo=root/'repo';shutil.copytree(CASE/'seed',repo)
        git(repo,'init','-b','main');git(repo,'add','.');git(repo,'commit','-m','Independent synthetic Spring seed')
        base=git(repo,'rev-parse','HEAD').stdout.strip()
        g=BuildGraphRun(repo,base,root/'runs',definition,tool_roots=list(toolchain.values()),java_home=toolchain['JAVA_HOME'],host_capacity=2,toolchain=toolchain,cache_seeds=seeds,allow_observed_daemon=True)
        try:
            state=g.run()
            if state['status']!='SUCCEEDED':
                # Preserve failed fixture for local diagnosis, never publish raw logs.
                failure=Path(tempfile.mkdtemp(prefix='failed-synthetic-spring-'))/'fixture'
                shutil.copytree(root,failure)
                print('Local synthetic failure fixture:',failure)
                raise RuntimeError('Graph failed; synthetic fixture retained outside case if available')
            n=state['nodes'];overlap=max(n['title']['started_at'],n['tags']['started_at'])<min(n['title']['ended_at'],n['tags']['ended_at'])
            waited=n['integration']['started_at']>=max(n['title']['ended_at'],n['tags']['ended_at'])
            merged=all(git(g.resources['integration']/'worktree','merge-base','--is-ancestor',n[x]['commit'],n['integration']['input_commit'],check=False).returncode==0 for x in ['title','tags'])
            receipts={}
            for name,tools in [('title',['maven']),('tags',['gradle']),('integration',['maven','gradle'])]:
                receipts[name]={}
                for tool in tools:
                    receipt=json.loads((g.resources[name]/'sandbox/tmp'/(tool+'-receipt.json')).read_text())
                    receipt['distinct_test_jvm']=bool(receipt.pop('test_jvm_pids'))
                    receipt.pop('launcher_pid');receipts[name][tool]=receipt
                assert n[name]['child_seen'] and n[name]['tree_stopped']
            unchanged=git(repo,'rev-parse','HEAD').stdout.strip()==base
            assert overlap and waited and merged and unchanged
            retained=g.cleanup();assert not retained
            clean=all(not (r/'worktree').exists() and not (r/'sandbox/home').exists() and not (r/'sandbox/tmp').exists() for r in g.resources.values())
            assert clean
            report={'kind':'spring_build_graph_receipt','synthetic':True,'status':'PASSED','platform':'Darwin',
                'mode':'trusted_macos_build_tree','source_id':identity(hashes),'source_sha256':hashes,'catalog':catalog,
                'cache_ids':cache_ids,'base_commit':base,'instance_count':4,'max_parallel':2,'host_capacity':2,
                'peak_parallel':state['peak_parallel'],'independent_workflows_overlap':overlap,'integration_waited':waited,
                'merged_both_commits':merged,'source_head_unchanged':unchanged,'resources_removed':clean,
                'graph_probe':state['graph_resource']['probe'],'builds':receipts,'nodes':{}}
            for name,v in n.items():report['nodes'][name]={k:x for k,x in v.items() if k not in {'process_pid','started_at','ended_at','seconds'}}
        finally:g.close()
    text=json.dumps(report,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    else:print(text,end='')
    print('PASS: Spring Graph; concurrent Maven/Gradle features, merged dual-tool 8-test suites, separate test JVMs, clean resources')

if __name__=='__main__':main()
