#!/usr/bin/env python3
"""Physical keypad/IR-access checks under the exclusive lock; no PIN/screenshots."""
from pathlib import Path
import subprocess,time,json,datetime,xml.etree.ElementTree as E
r=Path(__file__).resolve().parents[1];root=r.parent;adb=['/usr/bin/adb','-s','YOUR_ADB_SERIAL'];checks=[]
def read(c):return subprocess.check_output(adb+['shell',c],text=True,timeout=35).strip()
def lock():
 record=json.loads((root/'.phone.lock').read_text());assert record['owner']=='gps-walker-read'
 assert datetime.datetime.fromisoformat(record['expires'])>datetime.datetime.now().astimezone()
def guard():
 lock();state=read('dumpsys window');assert 'showing=false' in state and 'showing=true' not in state,'Native lock screen must be left to owner'
 read('input keyevent 224');state=read('dumpsys window')
 assert 'org.kyf37.walker/' in next(x for x in state.splitlines() if 'mCurrentFocus=' in x)
def key(k):guard();read('input keyevent '+str(k));time.sleep(.6)
def desc():
 guard();read('uiautomator dump --compressed /data/local/tmp/reader-phone-ui.xml');s=read('cat /data/local/tmp/reader-phone-ui.xml')
 return ' '.join(x.get('content-desc','') for x in E.fromstring(s).iter('node'))
def check(n,*parts):
 d=desc();assert all(x in d for x in parts),(n,d);checks.append({'check':n,'description':d});print('PASS',n,flush=True)
check('updated-menu','FLIP WALKER','Real save');key(15);check('reader-key-eight','REAL POKEWALKER','Read trainer & steps')
key(20);check('reader-backup-navigation','Back up all data');key(19);check('reader-info-navigation','Read trainer & steps')
key(133);check('export-does-not-fabricate-backup','Read a full backup first')
# Probe normal IR acquisition by selecting info only. No writes or firmware exploit.
key(132);time.sleep(2);check('reader-started','REAL POKEWALKER')
key(132);time.sleep(3);check('reader-cancel-keeps-page','REAL POKEWALKER')
key(134);check('back-to-existing-menu','FLIP WALKER');key(14);check('settings-retained','SETTINGS & HELP');key(134)
key(12);check('game-connection-retained','CONNECT TO GAME');key(134)
(r/'dist/hardware/reader-keypad.json').write_text(json.dumps({'screenshots':False,'real_device_exchange_verified':False,'checks':checks},indent=2));print('READER_PHONE_CHECKS='+str(len(checks)),flush=True)
