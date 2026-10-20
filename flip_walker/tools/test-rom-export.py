#!/usr/bin/env python3
"""Synthetic ROM capture persistence and exact export on emulator only."""
from pathlib import Path
import subprocess,time,xml.etree.ElementTree as E,re,json
r=Path(__file__).resolve().parents[1];serial='emulator-5582';out=r/'dist/qa-ds-tools';out.mkdir(exist_ok=True)
def adb(*a,raw=False):
 b=subprocess.check_output(['/usr/bin/adb','-s',serial,*map(str,a)],timeout=45);return b if raw else b.decode().strip()
assert adb('shell','getprop','ro.kernel.qemu')=='1';adb('root');adb('wait-for-device')
def key(k):adb('shell','input','keyevent',k);time.sleep(.5)
def xml():adb('shell','uiautomator','dump','--compressed','/sdcard/rom-export.xml');return E.fromstring(adb('shell','cat','/sdcard/rom-export.xml'))
def desc():return ' '.join(n.get('content-desc','') for n in xml().iter())
base='/data/user/0/org.kyf37.walker/files';folder=base+'/real-pokewalker';fixture=bytes(i%251 for i in range(49152));(out/'rom-fixture.bin').write_bytes(fixture)
before=adb('shell','sha256sum',base+'/walker.eeprom');uid=adb('shell','stat','-c','%u','/data/user/0/org.kyf37.walker');adb('shell','am','force-stop','org.kyf37.walker')
adb('push',out/'rom-fixture.bin',folder+'/rom-9999999999999-fixture.bin');adb('shell','chown',uid+':'+uid,folder+'/rom-9999999999999-fixture.bin');adb('shell','restorecon',folder+'/rom-9999999999999-fixture.bin')
adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1);key(15)
for i in range(5):key(20)
assert 'Dump ROM' in desc();adb('shell','rm','-f','/sdcard/Download/pokewalker-rom.bin');key(133)
save=[n for n in xml().iter() if n.get('text','').lower()=='save' and n.get('enabled')=='true'];assert save
x1,y1,x2,y2=map(int,re.findall(r'\d+',save[-1].get('bounds')));adb('shell','input','tap',(x1+x2)//2,(y1+y2)//2);time.sleep(2)
assert '48 KiB ROM exported' in desc();actual=adb('exec-out','cat','/sdcard/Download/pokewalker-rom.bin',raw=True);assert actual==fixture
assert before==adb('shell','sha256sum',base+'/walker.eeprom')
assert adb('shell','wc','-c',folder+'/pokewalker-9999999999999-fixture.bin').startswith('65536')
(out/'rom-export.json').write_text(json.dumps({'synthetic':True,'real_peer':False,'checks':['ROM survives relaunch','F3 exports selected ROM rather than EEPROM','49152-byte export matches fixture','EEPROM capture retained','virtual save unchanged']},indent=2));print('ROM_EXPORT_CHECKS=5',flush=True)
