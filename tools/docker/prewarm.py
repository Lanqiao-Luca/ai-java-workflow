"""Online public-only image preparation; foreground Docker build step owns all PIDs."""
from pathlib import Path
import os,runpy,shutil,time,signal
signal.alarm(900)
for name in ['HOME','TMPDIR']:Path(os.environ[name]).mkdir(parents=True,exist_ok=True)
n=runpy.run_path('/tmp/warm/app/build_task.py');n['implement']('both')
for tool in ['maven','gradle']:n['build'](tool,'integration',False)
def others():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in {1,os.getpid()}:continue
  try:
   state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]
   if state!='Z':result.append(int(p.name))
  except FileNotFoundError:pass
 return result
end=time.monotonic()+5
while others() and time.monotonic()<end:time.sleep(.03)
assert not others(),'preparation descendants not stopped'
home=Path(os.environ['HOME']);cache=home/'gradle'
for name in ['daemon','workers','notifications']:
 if (cache/name).exists():shutil.rmtree(cache/name)
for p in list(cache.rglob('*.lock')):p.unlink()
Path('/opt/cache-seed').mkdir()
for tool in ['maven','gradle']:shutil.copytree(home/tool,'/opt/cache-seed/'+tool)
print('PUBLIC_IMAGE_CACHE_READY')
