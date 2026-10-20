#!/usr/bin/env python3
"""Retained walk/game pages and read-only IR start/cancel in es-ES; no screenshots/PIN."""
from pathlib import Path
import subprocess,time,json,datetime,xml.etree.ElementTree as E
r=Path(__file__).resolve().parents[1];checks=[];started=False
adb=['/usr/bin/adb','-s','YOUR_ADB_SERIAL']
def read(c):return subprocess.check_output(adb+['shell',c],text=True,timeout=40).strip()
def guard():
 lock=json.loads((r.parent/'.phone.lock').read_text());assert lock['owner']=='gps-walker-read' and datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now().astimezone()
 w=read('dumpsys window');assert 'showing=false' in w and 'showing=true' not in w
 if started:assert 'org.kyf37.walker/' in next(x for x in w.splitlines() if 'mCurrentFocus=' in x)
def key(k):guard();read('input keyevent 224');read('input keyevent '+str(k));time.sleep(.5)
def desc():guard();read('uiautomator dump --compressed /data/local/tmp/walker-spanish.xml');return ' '.join(n.get('content-desc','') for n in E.fromstring(read('cat /data/local/tmp/walker-spanish.xml')).iter())
def check(n,*parts):
 d=desc();assert all(x.casefold() in d.casefold() for x in parts),(n,d);checks.append(n);print('PASS',n,flush=True)
guard();read('am force-stop org.kyf37.walker');read('am start -W -n org.kyf37.walker/.WalkerActivity');started=True;time.sleep(1)
check('spanish-default-preserved','Datos reales');key(8);check('retained-walk','Pasear','0 pasos');key(134);key(12);check('retained-game-link','Conectar con juego');key(134)
key(15);check('real-device-reader','Pokéwalker real','Leer datos y pasos');key(132);time.sleep(2);check('read-only-ir-start','Pokéwalker real');key(132);time.sleep(2);check('read-only-ir-cancel','Lectura cancelada','copias anteriores');key(134);check('real-save-still-unpaired-zero','FLIP WALKER','0 pasos')
(r/'dist/hardware/spanish-phone.json').write_text(json.dumps({'checks':checks,'screenshots':False,'real_peer_verified':False,'physical_write_operations_started':False},indent=2));print('SPANISH_PHONE_CHECKS='+str(len(checks)),flush=True)
