#!/usr/bin/env python3
"""Offline emulator UI tests. Hardcoded emulator serial, never enumerates phones."""
from pathlib import Path
import subprocess,time,xml.etree.ElementTree as ET,json,re
root=Path(__file__).resolve().parents[1]
adb_binary=root.parent/'flip_pokedex/cache/android-sdk/platform-tools/adb'
serial='emulator-5582';out=root/'dist/qa';out.mkdir(parents=True,exist_ok=True);results=[]
def adb(*args,raw=False):
    assert serial=='emulator-5582'
    p=subprocess.run([str(adb_binary),'-s',serial,*map(str,args)],check=True,capture_output=True,timeout=60)
    return p.stdout if raw else p.stdout.decode().strip()
def key(code):adb('shell','input','keyevent',code);time.sleep(.5)
def description():
    adb('shell','uiautomator','dump','--compressed','/sdcard/flip-walker-ui.xml')
    tree=ET.fromstring(adb('shell','cat','/sdcard/flip-walker-ui.xml'))
    return ' '.join(n.attrib.get('content-desc','') for n in tree.iter())
def check(name,*needles):
    desc=description();assert all(n in desc for n in needles),(name,desc,needles)
    results.append({'test':name,'pass':True,'description':desc});print('PASS',name,flush=True)
def shot(name):(out/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
assert adb('shell','getprop','ro.kernel.qemu')=='1','Not an emulator'
assert adb('shell','getprop','sys.boot_completed')=='1','Emulator not booted'
adb('install','-r',root/'dist/FlipWalker-emulator.apk')
package=adb('shell','dumpsys','package','org.kyf37.walker')
library=re.search(r'legacyNativeLibraryDir=(\S+)',package).group(1)+'/x86_64/libwalker_ir.so'
assert 'PWIR1' in adb('shell',library,'--self-test'),'Native helper cannot execute'
results.append({'test':'packaged-native-helper-self-test','pass':True})
adb('shell','am','force-stop','org.kyf37.walker')
adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(2)
check('main-menu','FLIP WALKER','Real save','Walk');shot('01-menu')
key(20);check('dpad-next','Poké Radar');key(19);check('dpad-previous','Walk')
key(23);check('open-walk','WALK','0 steps');shot('02-unpaired-walk')
key(4);check('clear-returns-menu','FLIP WALKER')
key(133);check('F3-settings','SETTINGS & HELP')
key(133);check('F3-demo-mode','Demo')
key(17);check('offline-game-transfer','Demo game transfer complete','2000 steps','100 watts')
key(131);check('F1-menu','FLIP WALKER')
key(8);check('number-shortcut-walk','WALK','Demo','2000 steps');shot('03-demo-walk')
key(23);check('demo-step-button','2020 steps','101 watts')
key(134);check('F4-back','FLIP WALKER')
key(9);check('radar-entry-and-cost','POKÉ RADAR','91 watts');shot('06-radar')
key(22);check('radar-dpad','POKÉ RADAR');key(23);check('radar-action','POKÉ RADAR')
key(134);key(10);check('dowsing-entry-and-cost','DOWSING','88 watts');shot('07-dowsing')
key(22);key(23);check('dowsing-action','DOWSING');key(134)
key(11);check('inventory-shortcut','POKÉMON & ITEMS')
key(4);key(12);check('connection-shortcut','CONNECT TO GAME');shot('04-connect')
key(23);check('simulated-connection','Demo game transfer complete')
key(133);key(133);check('real-save-isolation','Real save','0 steps','0 watts')
key(134);key(132);time.sleep(3)
check('IR-unavailable-is-visible','CONNECT TO GAME','Infrared unavailable')
shot('05-real-ir-status')
adb('shell','am','force-stop','org.kyf37.walker');adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1)
check('real-save-after-relaunch','FLIP WALKER','Real save','0 steps')
logs=adb('logcat','-d','-t','500')
(out/'logcat.txt').write_text(logs)
assert 'FATAL EXCEPTION' not in '\n'.join(line for line in logs.splitlines() if 'org.kyf37.walker' in line)
(out/'results.json').write_text(json.dumps({'emulator':serial,'physical_phone_accessed':False,'checks':results},indent=2))
print('EMULATOR_CHECKS='+str(len(results)))
