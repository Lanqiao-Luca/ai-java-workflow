"""Explicit online public-dependency preparation in a new isolated HOME; no tools installed."""
from pathlib import Path
import argparse
import json
import os
import runpy
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.execution.build_cache import seal,verify,MARKER
from tools.execution.build_fixture import run_preparation

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['java-home','maven-home','gradle-home','output']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--reuse-public-home',type=Path,help='Explicit previously sealed public caches only; never discover personal caches')
    a=p.parse_args();out=a.output.resolve()
    if out.exists():p.error('output must be a new dedicated directory')
    out.mkdir(parents=True);app=out/'app';shutil.copytree(Path(__file__).parent/'seed',app)
    home=out/'home';tmp=out/'tmp';home.mkdir();tmp.mkdir()
    env={'PATH':'/usr/bin:/bin','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1','HOME':str(home),'TMPDIR':str(tmp),
         'GRADLE_USER_HOME':str(home/'gradle'),'JAVA_HOME':str(a.java_home.resolve(strict=True)),
         'MAVEN_HOME':str(a.maven_home.resolve(strict=True)),'GRADLE_HOME':str(a.gradle_home.resolve(strict=True))}
    if a.reuse_public_home:
        for tool in ['maven','gradle']:
            source=a.reuse_public_home.resolve(strict=True)/tool;verify(source,tool);shutil.copytree(source,home/tool);(home/tool/MARKER).unlink()
    helper="import runpy,sys,json; n=runpy.run_path(sys.argv[1]); n['implement']('both'); print(json.dumps(n['build'](sys.argv[2],'integration',False)))"
    for tool in ['maven','gradle']:
        result=run_preparation([sys.executable,'-I','-B','-c',helper,str(app/'build_task.py'),tool],app,env,
                               out/(tool+'-prepare.log'),out/(tool+'-process.json'),timeout=600)
        if result['exit'] or result['reason'] or not result['tree_stopped']:
            raise SystemExit('public dependency preparation failed: '+tool+'; original output and process state retained, cache not sealed')
    # A running Gradle daemon must not be exported/reused as cache state.
    cache=home/'gradle'
    for name in ['daemon','workers','notifications']:
        if (cache/name).exists():shutil.rmtree(cache/name)
    for lock in list(cache.rglob('*.lock')):lock.unlink()
    records=[seal(home/tool,tool) for tool in ['maven','gradle']]
    (out/'prepared.json').write_text(json.dumps({'synthetic':True,'caches':records},indent=2)+'\n')
    print('PREPARED: public Maven/Gradle dependencies in isolated caches; Graph execution remains offline')

if __name__=='__main__':main()
