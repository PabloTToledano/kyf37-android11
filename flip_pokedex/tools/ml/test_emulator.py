#!/usr/bin/env python3
"""Actual packaged JNI inference through the standard image picker, emulator only."""
import subprocess,time,json,xml.etree.ElementTree as ET,re,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ.get('FLIP_CLASSIFIER_QA_DIR',str(ROOT/'dist/qa-classifier')));SERIAL='emulator-5580';PKG='org.kyf37.pokedex';checks=[];memory=[]
def adb(*args,raw=False):
 r=subprocess.run(['adb','-s',SERIAL,*map(str,args)],check=True,capture_output=True,timeout=60)
 return r.stdout if raw else r.stdout.decode(errors='replace')
def key(*codes):adb('shell','input','keyevent',*codes);time.sleep(.25)
def tree():
 adb('shell','uiautomator','dump','--compressed','/sdcard/identify-test.xml')
 return ET.fromstring(adb('shell','cat','/sdcard/identify-test.xml'))
def text():return ' '.join(n.get('content-desc','')+' '+n.get('text','') for n in tree().iter())
def check(name,*needles):
 t=text();assert all(n in t for n in needles),(name,t);checks.append({'test':name,'passed':True});print('PASS',name,flush=True);return t
def wait(needle,seconds=40):
 until=time.monotonic()+seconds
 while time.monotonic()<until:
  t=text()
  if needle in t:return t
  time.sleep(.3)
 raise AssertionError((needle,t))
def mem(stage):
 raw=adb('shell','dumpsys','meminfo',PKG);(OUT/(stage+'-meminfo.txt')).write_text(raw);m=re.search(r'TOTAL PSS:\s*(\d+)',raw) or re.search(r'\n\s*TOTAL\s+(\d+)',raw);memory.append({'stage':stage,'totalPssKiB':int(m.group(1)) if m else None})
def shot(name):(OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
def launch():
 adb('shell','am','force-stop','com.android.documentsui');adb('shell','am','force-stop',PKG);adb('shell','am','start','-W','-n',PKG+'/.PokedexActivity');time.sleep(.6);key(16);check('identify shortcut','Identify. SOURCE')
def choose(file,expected="Identify. CROP"):
 adb('push',file,'/sdcard/Download/'+file.name)
 key(9);time.sleep(.7)
 # The system document picker is outside this app. Select only a visibly observed filename.
 for _ in range(5):
  nodes=list(tree().iter());list_button=next((n for n in nodes if n.get('content-desc')=='List view'),None)
  if list_button is not None:
   b=list(map(int,re.findall(r'\d+',list_button.get('bounds'))));adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2);time.sleep(.4);continue
  matches=[n for n in nodes if (n.get('text')==file.name and n.get('class')=='android.widget.TextView') or n.get('content-desc','').startswith(file.name+',')]
  if matches:
   for step in range(24):
    tr=tree();ns=list(tr.iter());parents={c:p for p in ns for c in p};target=next(n for n in ns if (n.get('text')==file.name and n.get('class')=='android.widget.TextView') or n.get('content-desc','').startswith(file.name+','))
    while target.get('focusable')!='true' and target in parents:target=parents[target]
    focused=next((n for n in ns if n.get('focused')=='true'),None)
    if focused is target or (focused is not None and focused.get('bounds')==target.get('bounds')):key(23);break
    if focused is not None and int(re.findall(r'\d+',focused.get('bounds'))[1])>=244:
     a=list(map(int,re.findall(r'\d+',focused.get('bounds'))));b=list(map(int,re.findall(r'\d+',target.get('bounds'))));dx=b[0]-a[0];dy=b[1]-a[1];key((20 if dy>0 else 19) if abs(dy)>30 else (22 if dx>0 else 21))
    else:key(20)
   else:raise AssertionError('Cannot focus requested image with keypad')
   break
  search=next((n for n in nodes if n.get('content-desc')=='Search'),None)
  if search is not None and any(n.get('text')=='Downloads' for n in nodes):
   b=list(map(int,re.findall(r'\d+',search.get('bounds'))));adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2);adb('shell','input','text',file.name);key(66);time.sleep(.4);continue
  downloads=[n for n in nodes if n.get('text') in ['Downloads','Download']]
  if downloads:
   b=list(map(int,re.findall(r'\d+',downloads[0].get('bounds',''))));adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2)
  else:
   drawer=[n for n in nodes if n.get('content-desc')=='Show roots']
   assert drawer,'Cannot find system picker roots';b=list(map(int,re.findall(r'\d+',drawer[0].get('bounds',''))));adb('shell','input','tap',(b[0]+b[2])//2,(b[1]+b[3])//2)
  time.sleep(.5)
 else:raise AssertionError('Image absent in picker')
 wait(expected)
assert adb('shell','getprop','ro.kernel.qemu').strip()=='1'
assert adb('shell','getprop','sys.boot_completed').strip()=='1'
adb('logcat','-c');golden=json.loads((OUT/'golden.json').read_text());latencies=[]
for case in [c for c in golden if c['national'] in [1,25,133,494,649,0]]:
 launch();choose(OUT/case['file']);check('import '+case['file'],'Identify. CROP');mem('before-inference-'+str(case['national']))
 key(9);check('zoom in','Size 0.80');key(22);check('pan crop','Center 0.54');key(12);check('reset crop','Size 1.00','Center 0.50 0.50');shot('crop')
 key(23);result=wait('Identify. RESULTS');assert 'Identification unavailable' not in result,result;mem('after-inference-'+str(case['national']))
 if case['expectedTop1Id']==0:check('unknown image','Cannot identify')
 else:
  check('actual model candidate '+case['file'],'No. %03d'%case['expectedTop1Id']);shot('result-'+str(case['national']));key(23);check('candidate opens entry','ENTRY',str(case['expectedTop1Id']))
 m=re.search(r'Inference (\d+) ms',result)
 if m:latencies.append(int(m.group(1)))
# Uniform image must abstain; generated locally, no external content.
from PIL import Image
blank=OUT/'blank.png';Image.new('RGB',(160,160),'white').save(blank)
launch();choose(blank);key(23);wait('Identify. RESULTS');check('blank abstains','Cannot identify');key(4);check('back to crop','Identify. CROP');key(4);check('back to source','Identify. SOURCE')
bad=OUT/'invalid-image.png';bad.write_bytes(b'This is not an image');choose(bad,'Identify. ERROR');check('malformed image handled','Image unavailable');key(4);check('error back to crop','Identify. CROP');key(4);check('error back to source','Identify. SOURCE')
choose(OUT/golden[0]['file']);key(23,4);time.sleep(1);check('cancel or back suppresses stale results','Identify. CROP');key(4);check('cancel back to source','Identify. SOURCE')
key(9);time.sleep(.5);key(4);check('picker cancellation','Identify. SOURCE');key(4);check('exit classifier','LIST')
log=adb('logcat','-d');(OUT/'logcat.txt').write_text(log);assert 'FATAL EXCEPTION' not in log;assert 'Offline inference failed' not in log
report={'emulatorOnly':True,'hardwareVerified':False,'apkSha256':hashlib.sha256((ROOT/'dist/FlipPokedex-emulator.apk').read_bytes()).hexdigest(),'checks':checks,'inferenceMs':latencies,'density':adb('shell','wm','density').strip(),'appMemory':memory,'modelSha256':hashlib.sha256((ROOT/'app/assets/ml/pokemon-int8.tflite').read_bytes()).hexdigest()}
(OUT/'emulator-validation.json').write_text(json.dumps(report,indent=2));print('CLASSIFIER_EMULATOR_OK',len(checks),latencies)
