#!/usr/bin/env python3
"""Focused visual/keypress QA for the footer; isolated emulator only."""
from pathlib import Path
import subprocess,time,xml.etree.ElementTree as E,json
r=Path(__file__).resolve().parents[2];out=r/'dist/qa-button-icons';out.mkdir(exist_ok=True);adb=['/usr/bin/adb','-s','emulator-5582'];checks=[]
def run(*args,raw=False):
 b=subprocess.check_output(adb+list(map(str,args)),timeout=45);return b if raw else b.decode().strip()
assert run('shell','getprop','ro.kernel.qemu')=='1'
def key(k):run('shell','input','keyevent',k);time.sleep(.5)
def desc():run('shell','uiautomator','dump','--compressed','/sdcard/button-icons.xml');return ' '.join(n.get('content-desc','') for n in E.fromstring(run('shell','cat','/sdcard/button-icons.xml')).iter())
def check(n,*parts):
 d=desc();assert all(p.casefold() in d.casefold() for p in parts),(n,d);checks.append(n);print('PASS',n,flush=True)
def shot(n):(out/(n+'.png')).write_bytes(run('exec-out','screencap','-p',raw=True))
run('install','-r',r/'dist/FlipWalker-emulator.apk');run('shell','am','force-stop','org.kyf37.walker');run('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1)
key(14)
if 'Idioma: Español (España)' in desc():key(132)
check('camera-key-keeps-language-control','Language: English');shot('01-english-settings');key(134);shot('02-english-main')
key(132);check('camera-key-keeps-game-link','CONNECT TO GAME');key(134);key(133);check('mail-key-keeps-settings','SETTINGS & HELP');key(132);check('camera-icon-switches-to-spanish','Idioma: Español (España)');shot('03-spanish-settings')
key(131);check('contacts-key-keeps-main-menu','FLIP WALKER');shot('04-spanish-main');key(15);check('device-menu','Pokéwalker real');shot('05-spanish-reader')
key(11)
for i in range(10):key(20)
key(23);check('review-retains-apply-action','Confirma los cambios');shot('06-spanish-review');key(134);check('browser-key-cancels-review','REGALO POKÉMON');key(134);key(134)
key(14);key(132);check('english-can-be-restored','Language: English');key(134)
(out/'checks.json').write_text(json.dumps({'checks':checks,'phone_accessed':False,'screenshots_are_emulator':True,'write_operations_started':False},indent=2));print('FOOTER_UI_CHECKS='+str(len(checks)),flush=True)
