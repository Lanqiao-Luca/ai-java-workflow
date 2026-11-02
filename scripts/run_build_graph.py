"""Explicit trusted build mode. Prepare public caches separately; execution is offline."""
from pathlib import Path
import argparse,json,signal,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.execution.build_runtime import BuildGraphRun
from tools.execution.catalog import load_definition
from tools.execution.runtime import Rejected,token

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['definition','repo','runtime-root','java-home','maven-home','gradle-home','prepared-home']:p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--base',required=True);p.add_argument('--run-id',required=True);p.add_argument('--host-capacity',type=int,default=2);p.add_argument('--cleanup',action='store_true')
 p.add_argument('--allow-observed-daemon',action='store_true',help='Opt in to tracked sandbox-inherited single-use daemons; must drain within 3 seconds')
 a=p.parse_args();g=None
 try:
  definition,catalog=load_definition(a.definition,ROOT);definition['graph_id']=token(a.run_id)
  toolchain={n.upper().replace('-','_'):getattr(a,n.replace('-','_')).resolve(strict=True) for n in ['java-home','maven-home','gradle-home']}
  g=BuildGraphRun(a.repo,a.base,a.runtime_root,definition,tool_roots=list(toolchain.values()),java_home=a.java_home,host_capacity=a.host_capacity,toolchain=toolchain,cache_seeds={t:a.prepared_home/t for t in ['maven','gradle']},allow_observed_daemon=a.allow_observed_daemon)
  for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:g.cancel.set())
  state=g.run();state['catalog_id']=catalog['catalog_id'];g._save()
  if a.cleanup:g.cleanup()
  print(json.dumps(state,indent=2));return 0 if state['status']=='SUCCEEDED' else 1
 except (Rejected,OSError,ValueError):print('REJECTED: build admission or execution failed; no bare-process fallback');return 2
 finally:
  if g:g.close()
if __name__=='__main__':raise SystemExit(main())
