"""Explicit online local image preparation from a manifest whitelist; no image push."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.execution.docker_io import DockerCLI
from tools.execution.runtime import identity,atomic,relative

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['docker','maven-archive','gradle-archive','output']:p.add_argument('--'+name,required=True,type=Path)
 for name in ['socket','base-image']:p.add_argument('--'+name,required=True)
 a=p.parse_args()
 if not re.fullmatch(r'(?:docker.io/library/)?eclipse-temurin@sha256:[0-9a-f]{64}',a.base_image):p.error('explicit official Temurin base digest required; pull separately')
 out=a.output.resolve()
 if out.exists() or out.is_relative_to(ROOT):p.error('new output directory outside repository required')
 out.mkdir(parents=True);context=out/'context';context.mkdir();client=DockerCLI(a.docker,a.socket,out/'client')
 # Only the previously published case-manifest entries are admitted, not a folder copy.
 old=ROOT/'examples/spring-build-graph';entries=json.loads((old/'artifact-manifest.json').read_text())['files'];seed_entries=[r for r in entries if r['path'].startswith('seed/')]
 if not seed_entries:raise RuntimeError('public seed manifest missing')
 for row in seed_entries:
  name=relative(row['path']);source=old/name
  if source.is_symlink() or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('public seed byte drift')
  target=context/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 for name in ['Dockerfile','worker.py','prewarm.py']:shutil.copyfile(ROOT/'tools/docker'/name,context/name)
 tools=json.loads((old/'evidence/toolchain.json').read_text())['tools']
 for path,name,tool in [(a.maven_archive,'maven.tar.gz','Apache Maven'),(a.gradle_archive,'gradle.zip','Gradle')]:
  record=next(t for t in tools if t['name']==tool);algo=record['algorithm'].lower()
  if hashlib.new(algo,path.read_bytes()).hexdigest()!=record['digest']:raise RuntimeError('public tool archive checksum mismatch')
  shutil.copyfile(path,context/name)
 hashes={p.relative_to(context).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(context.rglob('*')) if p.is_file()}
 context_id=identity(hashes);atomic(out/'build-state.json',{'status':'RUNNING','context_id':context_id})
 args=['build','--pull=false','--build-arg','BASE_IMAGE='+a.base_image,'--build-arg','CONTEXT_ID='+context_id,
       '--build-arg','WORKER_SHA256='+hashes['worker.py'],'--iidfile',str(out/'image-id.txt'),str(context)]
 client.env['DOCKER_BUILDKIT']='0'  # Official static CLI: use Engine's supported classic builder, no plugin install.
 try:
  code,stdout,stderr=client.call(args,timeout=1800,limit=8*1024*1024,check=False)
 except BaseException:
  atomic(out/'build-state.json',{'status':'UNKNOWN','context_id':context_id});raise
 (out/'build.log').write_bytes(stdout+stderr)
 if code:atomic(out/'build-state.json',{'status':'FAILED','exit':code});raise RuntimeError('image build failed; original context/log retained')
 image=(out/'image-id.txt').read_text().strip()
 if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise RuntimeError('build did not produce immutable image ID')
 value=client.json(['image','inspect',image,'--format','{{json .}}']);labels=value['Config']['Labels']
 assert labels['io.ai-java-workflow.context']==context_id and labels['io.ai-java-workflow.worker-sha256']==hashes['worker.py']
 receipt={'synthetic':True,'status':'PASSED','image_id':image,'base_image':a.base_image,'context_id':context_id,'context_sha256':hashes,
          'container_os':value['Os'],'image_arch':value['Architecture'],'java_version':labels['io.ai-java-workflow.java'],
          'maven':'3.9.11','gradle':'8.14.3','spring_boot':'3.5.16','dependency_preparation':'online_public_central',
          'image_pushed':False,'notes':'Official tool checksums checked; base digest pinned. Image remains local; raw build log is outside the repository.'}
 atomic(out/'image-receipt.json',receipt);atomic(out/'build-state.json',{'status':'SUCCEEDED','image_id':image})
 print('PASS: explicit public build context, online cache preparation, immutable local image; no registry push')
if __name__=='__main__':main()
