#!/usr/bin/env python3
"""Retained corner-key behavior after icon-only footer update. No IR/write action."""
from pathlib import Path
import subprocess,json,time,datetime,xml.etree.ElementTree as E
r=Path(__file__).resolve().parents[2];started=False;checks=[]
def read(c):return subprocess.check_output(['/usr/bin/adb','-s','YOUR_ADB_SERIAL','shell',c],text=True,timeout=40).strip()
def guard():
 lock=json.loads((r.parent/'.phone.lock').read_text());assert lock['owner']=='gps-walker-read' and datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now().astimezone()
 w=read('dumpsys window');assert 'showing=false' in w and 'showing=true' not in w
 if started:assert 'org.kyf37.walker/' in next(x for x in w.splitlines() if 'mCurrentFocus=' in x)
def key(k):guard();read('input keyevent '+str(k));time.sleep(.6)
def desc():guard();read('uiautomator dump --compressed /data/local/tmp/button-icons.xml');return ' '.join(n.get('content-desc','') for n in E.fromstring(read('cat /data/local/tmp/button-icons.xml')).iter())
def check(n,*parts):
 d=desc();assert all(x.casefold() in d.casefold() for x in parts),(n,d);checks.append(n);print('PASS',n,flush=True)
guard();read('am force-stop org.kyf37.walker');read('am start -W -n org.kyf37.walker/.WalkerActivity');started=True;time.sleep(1)
was_spanish='Datos reales' in desc()
if not was_spanish:key(133);key(132);key(134)
check('spanish-main-preserved','Datos reales');key(131);check('contacts-key-walk','Pasear');key(134);check('browser-key-back','FLIP WALKER');key(133);check('mail-key-settings','Ajustes y ayuda');key(132);check('camera-key-english','Language: English');key(132);check('camera-key-spanish','Idioma: Español (España)');key(134);key(15);check('real-device-options-retained','Pokéwalker real');key(134);check('walking-data-still-visible','pasos')
if not was_spanish:key(133);key(132);key(134)
(r/'dist/hardware/button-icons-keypad.json').write_text(json.dumps({'checks':checks,'screenshots':False,'infrared_started':False,'language_preference_preserved':True,'physical_write_operations_started':False},indent=2));print('FOOTER_PHONE_CHECKS='+str(len(checks)),flush=True)
