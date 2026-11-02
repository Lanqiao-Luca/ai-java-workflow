"""Explicit local Docker backend; no Seatbelt or bare-process fallback."""
from pathlib import Path
import argparse,json,signal,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.execution.catalog import load_definition
from tools.execution.runtime import Rejected,token
from tools.execution.docker_io import DockerCLI
from tools.execution.docker_runtime import DockerGraphRun

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['definition','repo','runtime-root','docker','client-config']:p.add_argument('--'+name,required=True,type=Path)
 for name in ['base','run-id','socket','image']:p.add_argument('--'+name,required=True)
 p.add_argument('--cleanup',action='store_true');a=p.parse_args();g=None
 try:
  if a.client_config.resolve().is_relative_to(a.repo.resolve()) or a.client_config.resolve().is_relative_to(ROOT):raise Rejected('private Docker config must be outside repositories')
  definition,catalog=load_definition(a.definition,ROOT);definition['graph_id']=token(a.run_id)
  client=DockerCLI(a.docker,a.socket,a.client_config)
  g=DockerGraphRun(a.repo,a.base,a.runtime_root,definition,client,a.image)
  for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:g.cancel.set())
  state=g.run();state['catalog_id']=catalog['catalog_id'];g._save()
  if a.cleanup:g.cleanup()
  print(json.dumps(state,indent=2));return 0 if state['status']=='SUCCEEDED' else 1
 except (Rejected,OSError,ValueError):print('REJECTED: Docker admission or execution unconfirmed; original state/resources retained');return 2
 finally:
  if g:g.close()
if __name__=='__main__':raise SystemExit(main())
