#!/usr/bin/env python3
"""Focused release check after the empty-search wording-only revision."""
import subprocess,time,json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[1];qa=r/'dist/qa';serial='emulator-5580';apk=r/'dist/FlipPokedex.apk'
def adb(*args):return subprocess.check_output(['adb','-s',serial,*args],timeout=90)
def key(*codes):adb('shell','input','keyevent',*[str(c) for c in codes]);time.sleep(.2)
def desc():
    adb('shell','uiautomator','dump','--compressed','/sdcard/flip-pokedex-test.xml')
    return adb('shell','cat','/sdcard/flip-pokedex-test.xml').decode()
assert adb('shell','getprop','ro.kernel.qemu').strip()==b'1'
adb('install','-r',str(apk));adb('shell','am','force-stop','org.kyf37.pokedex')
adb('shell','am','start','-W','-n','org.kyf37.pokedex/.PokedexActivity');time.sleep(1)
key(7,16,16,16);assert 'No matching Pok' in desc()
(qa/'14-empty-search.png').write_bytes(adb('exec-out','screencap','-p'))
key(4,4,4,4);assert 'LIST' in desc()
# Existing test preferences: National and animations on; select Victini and check motion.
key(7,11,16,11,23);time.sleep(.8);assert 'Victini' in desc()
frames=[]
for n in range(8):frames.append(adb('exec-out','screencap','-p'));time.sleep(.3)
assert len(set(frames))>1,'Sprite did not animate'
(qa/'15-animation-frame.png').write_bytes(frames[0])
(qa/'animation-check.json').write_text(json.dumps({'apkSha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'frames':len(frames),'distinctFrames':len(set(frames)),'sha256':[hashlib.sha256(f).hexdigest() for f in frames]},indent=2))
(qa/'release-focused.json').write_text(json.dumps({'apkSha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'tests':['empty-search-render','clear-return-to-list','victini-entry','animated-frames-change'],'passed':True},indent=2))
print('RELEASE_FOCUSED_OK: empty-search render, Clear return, entry, animation; distinct frames:',len(set(frames)))
