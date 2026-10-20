#!/usr/bin/env python3
"""Isolated emulator reader UI/storage checks. Never uses physical phone serial."""
from pathlib import Path
import subprocess,time,json,xml.etree.ElementTree as E,hashlib,re
r=Path(__file__).resolve().parents[1];serial='emulator-5582';binary='/usr/bin/adb';out=r/'dist/qa-reader';out.mkdir(parents=True,exist_ok=True);checks=[]
def adb(*args,raw=False):
 assert serial=='emulator-5582'
 b=subprocess.check_output([binary,'-s',serial,*map(str,args)],timeout=60)
 return b if raw else b.decode().strip()
assert adb('shell','getprop','ro.kernel.qemu')=='1'
assert adb('shell','getprop','sys.boot_completed')=='1'
def shell(c):return adb('shell',c)
def key(k):adb('shell','input','keyevent',str(k));time.sleep(.6)
def xml():
 adb('shell','uiautomator','dump','--compressed','/sdcard/reader-test-ui.xml')
 return E.fromstring(adb('shell','cat','/sdcard/reader-test-ui.xml'))
def desc():return ' '.join(n.get('content-desc','') for n in xml().iter())
def check(name,*text):
 d=desc();assert all(x in d for x in text),(name,d);checks.append(name);print('PASS',name,flush=True)
def launch():adb('shell','am','force-stop','org.kyf37.walker');adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1)
# Remove only synthetic capture fixtures owned by this emulator test from a prior run.
adb('root');adb('wait-for-device')
assert shell('id').startswith('uid=0')
fixtureFolder='/data/user/0/org.kyf37.walker/files/real-pokewalker'
adb('shell','am','force-stop','org.kyf37.walker')
adb('shell','rm','-f',fixtureFolder+'/pokewalker-9999999999999-fixture.bin',fixtureFolder+'/pokewalker-99999999999999-bad.bin',fixtureFolder+'/last-identity.bin')
launch();key(15);check('number-eight-opens-reader','REAL POKEWALKER','Read trainer & steps','No capture','No backup')
key(20);check('reader-dpad-backup-choice','Back up all data')
key(133);check('export-requires-full-backup','Read a full backup first')
key(132);time.sleep(3);check('reader-unavailable-is-visible','Infrared unavailable','No backup')
key(134);check('reader-back-keeps-existing-menu','FLIP WALKER','0 steps')
key(12);check('game-connection-still-available','CONNECT TO GAME');key(134)
# Test capture loading/export only with synthetic data injected into emulator files.
adb('root');adb('wait-for-device');assert shell('id').startswith('uid=0')
uid=re.search(r'userId=(\d+)',shell('dumpsys package org.kyf37.walker')).group(1)
base='/data/user/0/org.kyf37.walker/files';folder=base+'/real-pokewalker'
# Use an actual 64 KiB virtual save, not merely an absent-file sentinel.
if shell('test -f '+base+'/walker.eeprom && echo present || echo absent')=='absent':
 virtual=bytearray(65536);virtual[:8]=b'nintendo';virtual[0x7000:0x7008]=b'KEEPTHIS'
 (out/'virtual-existing.eeprom').write_bytes(virtual)
 adb('push',out/'virtual-existing.eeprom',base+'/walker.eeprom')
 adb('shell','chown',uid+':'+uid,base+'/walker.eeprom');adb('shell','restorecon',base+'/walker.eeprom')
assert shell('wc -c < '+base+'/walker.eeprom')=='65536'
before=shell('sha256sum '+base+'/walker.eeprom 2>/dev/null || echo absent')
identity=bytearray(104);identity[12:14]=(24680).to_bytes(2,'little');identity[72:80]=bytes([0xb0,0,0xb1,0,255,255,0,0]);identity[91]=3;identity[100:104]=(321).to_bytes(4,'big')
data=bytearray(65536);data[0xed:0xed+104]=identity;data[0x156:0x15a]=(123456).to_bytes(4,'big');data[0x15a:0x15e]=(321).to_bytes(4,'big');data[0x164:0x166]=(789).to_bytes(2,'big')
(out/'fixture.bin').write_bytes(data);(out/'identity.bin').write_bytes(identity)
adb('shell','am','force-stop','org.kyf37.walker');adb('shell','mkdir','-p',folder)
adb('push',out/'fixture.bin',folder+'/pokewalker-9999999999999-fixture.bin');adb('push',out/'identity.bin',folder+'/last-identity.bin');adb('shell','chown','-R',uid+':'+uid,folder);adb('shell','restorecon','-RF',folder)
launch();key(15);check('capture-persists-on-relaunch','Trainer ID: 24680','Steps today: 321','64 KiB backup available')
# Partial captures must never be presented as completed backups.
adb('shell','sh','-c',"'printf bad > "+folder+"/pokewalker-99999999999999-bad.bin'")
adb('shell','chown',uid+':'+uid,folder+'/pokewalker-99999999999999-bad.bin');adb('shell','restorecon',folder+'/pokewalker-99999999999999-bad.bin')
launch();key(15);check('bad-capture-preserved-and-not-exportable','Previous readback could not be loaded','No backup')
assert shell('wc -c < '+folder+'/pokewalker-99999999999999-bad.bin')=='3'
adb('shell','rm',folder+'/pokewalker-99999999999999-bad.bin');launch();key(15)
adb('shell','rm','-f','/sdcard/Download/pokewalker-eeprom.bin')
key(133);tree=xml();save=[n for n in tree.iter() if (n.get('text','').lower()=='save' or n.get('content-desc','').lower()=='save') and n.get('enabled')=='true']
assert save,'Create Document picker has no save action'
checks.append('export-opens-native-document-picker')
a,b,c,d=map(int,re.findall(r'\d+',save[-1].get('bounds')));adb('shell','input','tap',str((a+c)//2),str((b+d)//2));time.sleep(2)
check('export-completes','64 KiB backup exported')
exported=adb('exec-out','cat','/sdcard/Download/pokewalker-eeprom.bin',raw=True)
assert exported==bytes(data),'Export differs from raw device snapshot';checks.append('export-raw-65536-bytes-match')
after=shell('sha256sum '+base+'/walker.eeprom 2>/dev/null || echo absent');assert before==after,'Reader changed app save';checks.append('virtual-save-remains-byte-identical')
key(134);check('old-walk-still-unpaired-and-zero','FLIP WALKER','0 steps');key(8);check('old-walk-screen-retained','WALK','0 steps')
(out/'results.json').write_text(json.dumps({'emulator':serial,'physical_phone_accessed':False,'checks':checks},indent=2));print('READER_UI_CHECKS='+str(len(checks)),flush=True)
