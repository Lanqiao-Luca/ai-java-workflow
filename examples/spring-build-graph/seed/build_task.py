"""Deterministic fixture implementation and real offline build; synthetic data only."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
TITLE='''package example.graph;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
@RestController public class TitleApi {
 @GetMapping("/title") public String title(@RequestParam("value") String value) {
  String title=value.trim(); if(title.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST); return title;
 }
}
'''
TAGS='''package example.graph;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.util.LinkedHashSet;
@RestController public class TagsApi {
 @GetMapping("/tags") public String tags(@RequestParam("value") String value) {
  var tags=new LinkedHashSet<String>(); for(String raw:value.split(",",-1)) {
   String tag=raw.trim();if(tag.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST);tags.add(tag);
  } return String.join(",",tags);
 }
}
'''
def implement(mode):
 for name,text in [("title",TITLE),("tags",TAGS)]:
  if mode in {name,"both"}:(ROOT/("src/main/java/example/graph/"+name.capitalize()+"Api.java")).write_text(text)
def build(tool,mode,offline=True):
 java=Path(os.environ['JAVA_HOME'])/'bin/java';tmp=Path(os.environ['TMPDIR']);home=Path(os.environ['HOME'])
 javaargs=[str(java),'-Djava.io.tmpdir='+str(tmp),'-Duser.home='+str(home),'-XX:+DisableAttachMechanism','-Djava.net.preferIPv4Stack=true']
 if tool=='maven':
  mh=Path(os.environ['MAVEN_HOME']);classpath=str(mh/'boot/plexus-classworlds-2.9.0.jar')
  args=javaargs+['-Dmaven.home='+str(mh),'-Dmaven.multiModuleProjectDirectory='+str(ROOT),'-Dclassworlds.conf='+str(mh/'bin/m2.conf'),'-cp',classpath,'org.codehaus.plexus.classworlds.launcher.Launcher','-B','-q','-s',str(ROOT/'settings.xml'),'-gs',str(ROOT/'settings.xml'),'-Dmaven.repo.local='+str(home/'maven'),'-Dstyle.color=never']
  if offline:args+=['-o']
  if mode!='integration':args+=['-Dtest='+mode.capitalize()+'ApiTest']
  args+=['verify'];reports=tmp/'maven-output/surefire-reports'
 elif tool=='gradle':
  gh=Path(os.environ['GRADLE_HOME'])
  args=javaargs+['-Dorg.gradle.daemon=false','-Dorg.gradle.jvmargs=-Djava.net.preferIPv4Stack=true','-Dorg.gradle.native=false','-javaagent:'+str(gh/'lib/agents/gradle-instrumentation-agent-8.14.3.jar'),'-jar',str(gh/'lib/gradle-gradle-cli-main-8.14.3.jar'),'--no-daemon','--max-workers=1','--console=plain','--project-cache-dir',str(tmp/'gradle-project'),'-g',str(home/'gradle'),'--quiet']
  if offline:args+=['--offline']
  args+=['test']
  if mode!='integration':args+=['--tests','example.graph.'+mode.capitalize()+'ApiTest']
  args+=['build']
  reports=tmp/'gradle-output/test-results/test'
 else:raise ValueError('unknown build tool')
 env={k:v for k,v in os.environ.items() if k not in {'JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','MAVEN_OPTS','GRADLE_OPTS'}}
 # These fixed instance-owned options replace ambient injection. Force IPv4 for
 # inherited Gradle JVM loopback sockets; Java's dual-stack mapped bind is denied.
 env['JAVA_TOOL_OPTIONS']='-Djava.net.preferIPv4Stack=true -Duser.home='+json.dumps(str(home))+' -Djava.io.tmpdir='+json.dumps(str(tmp))+' -XX:+DisableAttachMechanism'
 run=subprocess.Popen(args,cwd=ROOT,env=env)
 run.wait()
 if run.returncode:raise SystemExit(run.returncode)
 result={'launcher_pid':run.pid,'test_jvm_pids':[],'tests':0,'failures':0,'errors':0,'skipped':0,'tool':tool,'suites':[]}
 for p in sorted(reports.glob('TEST-*.xml')):
  suite=ET.parse(p).getroot();result['suites'].append(suite.attrib['name'])
  import re
  result['test_jvm_pids']+= [int(x) for x in re.findall(r'BUILD_TEST_JVM=(\d+)', ''.join(suite.itertext()))]
  for key in ['tests','failures','errors','skipped']:result[key]+=int(suite.attrib.get(key,0))
 expected=8 if mode=='integration' else 3
 result['test_jvm_pids']=sorted(set(result['test_jvm_pids']))
 assert result['test_jvm_pids'] and run.pid not in result['test_jvm_pids'], 'test JVM was not distinct from launcher'
 assert result['tests']==expected and all(result[k]==0 for k in ['failures','errors','skipped']),result
 import zipfile,hashlib
 artifacts=[]
 for artifact in sorted((tmp/(tool+'-output')).rglob('*.jar')):
  with zipfile.ZipFile(artifact) as z:
   names=set(z.namelist())
   if 'BOOT-INF/classes/example/graph/App.class' not in names:continue
   manifest=z.read('META-INF/MANIFEST.MF').decode()
   assert 'org.springframework.boot.loader.launch.JarLauncher' in manifest
   assert 'BOOT-INF/classes/example/graph/TitleApi.class' in names and 'BOOT-INF/classes/example/graph/TagsApi.class' in names
  artifacts.append({'name':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'bytes':artifact.stat().st_size,'boot_jar':True})
 assert len(artifacts)==1,'expected one Spring Boot executable JAR'
 result['artifacts']=artifacts
 (tmp/(tool+'-receipt.json')).write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 mode,tool=sys.argv[1:];implement(mode)
 for selected in (['maven','gradle'] if tool=='both' else [tool]):build(selected,mode)
 print('SPRING_'+mode.upper()+'_OK')
