#!/usr/bin/env python3
"""Explicit locked keypad checks; no screenshots, PIN input or game exchange."""
from pathlib import Path
import subprocess,json,datetime,time,xml.etree.ElementTree as ET,argparse
root=Path(__file__).resolve().parents[1];project=root.parent
p=argparse.ArgumentParser();p.add_argument('--corners',action='store_true');args=p.parse_args()
checks=[]
def lock():
    record=json.loads((project/'.phone.lock').read_text())
    assert record['owner']=='flip-walker-ir'
    assert datetime.datetime.fromisoformat(record['expires'])>datetime.datetime.now(datetime.timezone.utc)
def adb(*args):
    return subprocess.check_output(['/usr/bin/adb','-s','YOUR_ADB_SERIAL',*args],timeout=45).decode()
def guard():
    lock();w=adb('shell','dumpsys','window')
    assert 'showing=false' in w and 'showing=true' not in w,'Native lock screen; no keys will be entered'
    focus=next(line for line in w.splitlines() if 'mCurrentFocus=' in line)
    assert 'org.kyf37.walker/' in focus,'Walker is not focused; no keys will be entered'
def key(code):guard();adb('shell','input','keyevent',str(code));time.sleep(.4)
def check(name,*needles):
    guard();adb('shell','uiautomator','dump','--compressed','/sdcard/flip-walker-check.xml')
    xml=ET.fromstring(adb('shell','cat','/sdcard/flip-walker-check.xml'))
    text=' '.join(n.attrib.get('content-desc','') for n in xml.iter())
    assert all(n in text for n in needles),(name,text)
    checks.append({'check':name,'pass':True,'description':text});print('PASS',name,flush=True)
check('main-menu','FLIP WALKER','Real save')
key(20);check('dpad-next','Poké Radar');key(19);check('dpad-previous','Walk')
key(8);check('number-walk','WALK','0 steps');key(4);check('clear-menu','FLIP WALKER')
key(11);check('number-inventory','POKÉMON & ITEMS');key(4)
key(14);check('number-settings','SETTINGS & HELP');key(4)
key(12);check('number-connect','CONNECT TO GAME');key(4)
if args.corners:
    key(133);check('F3-settings','SETTINGS & HELP')
    key(134);check('F4-back','FLIP WALKER')
    key(8);key(131);check('F1-menu','FLIP WALKER')
    key(132);check('F2-connect','CONNECT TO GAME');key(134)
dest=root/'dist/hardware';dest.mkdir(parents=True,exist_ok=True)
(dest/('phone-corners.json' if args.corners else 'phone-keypad.json')).write_text(json.dumps({'serial':'YOUR_ADB_SERIAL','screenshots':False,'game_exchange':False,'checks':checks},indent=2))
print('PHONE_KEYPAD_CHECKS='+str(len(checks)))
