#!/usr/bin/env python3
"""End-to-end keypad smoke tests. Hard-coded emulator serial; refuses real devices."""
import json,subprocess,time,sys,hashlib,os,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/qa';OUT.mkdir(parents=True,exist_ok=True)
TEST_APK=Path(os.environ.get('FLIP_POKEDEX_TEST_APK',str(ROOT/'dist/FlipPokedex.apk')))
SERIAL='emulator-5580'; PACKAGE='org.kyf37.pokedex'; results=[]
def adb(*args,raw=False):
    assert SERIAL.startswith('emulator-')
    r=subprocess.run(['adb','-s',SERIAL,*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
    return r.stdout if raw else r.stdout.decode(errors='replace').strip()
def key(*codes):
    adb('shell','input','keyevent',*[str(c) for c in codes]);time.sleep(.25)
def desc():
    adb('shell','uiautomator','dump','--compressed','/sdcard/flip-pokedex-test.xml')
    raw=adb('shell','cat','/sdcard/flip-pokedex-test.xml');root=ET.fromstring(raw)
    return ' '.join(n.attrib.get('content-desc','') for n in root.iter())
def check(label,*needles):
    d=desc()
    assert all(x in d for x in needles),(label,needles,d)
    results.append({'test':label,'passed':True,'description':d});print('PASS',label,flush=True)
def shot(name): (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
assert adb('shell','getprop','ro.kernel.qemu')=='1','Not an emulator'
assert adb('shell','getprop','sys.boot_completed')=='1','Emulator not booted'
# Never clear data: reset only this test app's public UI state by navigating options.
adb('install','-r',str(TEST_APK))
adb('shell','am','force-stop',PACKAGE)
adb('shell','am','start','-W','-n',PACKAGE+'/.PokedexActivity');time.sleep(2)
if '--edges-only' not in sys.argv:
    # Normalize persisted preferences through the app UI; never wipe app/emulator data.
    d=desc();key(17)
    if ' National.' in d:key(22)
    key(20,20,20,20)
    for _ in range(3):
     if 'Theme 0.' in desc():break
     key(22)
    key(20)
    if 'Animation on.' in desc():key(22)
    key(20,20);key(23);key(4)
    check('launch','LIST');shot('01-list')
    # Initial clean emulator starts in Unova; tests use explicit dex selection as needed.
    key(0+7) # 0: number search
    check('number-search-screen','SEARCH NUMBER')
    key(7,7,7) # Victini #000
    check('victini-000','Victini','1 results')
    key(23);check('entry-open','ENTRY','Victini');shot('02-entry')
    key(22);check('stats-tab','STATS');shot('03-stats')
    key(22);check('moves-tab','MOVES');shot('04-moves')
    key(23);check('move-record','MOVE RECORD');shot('05-move-record')
    key(22);check('next-move-record','MOVE RECORD')
    key(4);check('move-back','MOVES')
    key(22);check('area-tab','AREA');shot('06-area')
    key(22);check('evolution-tab','EVOLVE');shot('07-evolution')
    key(4);check('entry-back-to-list','LIST')
    key(22);check('list-page-right','Pignite')
    key(21);check('list-page-left','Victini')
    key(19);check('list-wrap-up','Genesect')
    key(20);check('list-wrap-down','Victini')
    key(7);key(17) # star: name mode
    check('t9-mode','SEARCH T9')
    key(14,10,11) # 7 3 4 = 'sei' → Seismitoad
    check('t9-prefix','Seismitoad')
    key(18);check('search-erase','SEARCH T9') # pound
    key(4,4,4);check('search-back','LIST')
    # Pick Oshawott by its Unova #007.
    key(7,7,7,14);check('oshawott-search','Oshawott','1 results')
    key(23);check('oshawott-entry','ENTRY','Oshawott')
    if 'Favorite.' in desc():key(8)
    key(8);check('favorite-mark','Favorite.') # 1
    if 'Caught.' in desc():key(12)
    key(12);check('caught-mark','Caught.') # 5
    key(18);time.sleep(.7);shot('08-shiny')
    key(14);time.sleep(.7);shot('09-back') # 7 sprite back
    key(13);time.sleep(1) # 6 legacy cry; emulator audio may be disabled
    key(4);key(17);check('options','JOURNAL OPTIONS');shot('10-options')
    # Menu starts at Dex: switch to National, then choose Platinum.
    key(22);check('national-dex','National','649 results')
    key(20,20,20,20);key(22);check('platinum-theme','Theme 1.');shot('11-platinum')
    key(22);check('white-theme','Theme 2.');shot('12-white')
    key(20);key(22);check('animations-on','Animation on.')
    key(22);check('animations-off','Animation off.')
    key(4);key(7,9,12);check('national-pikachu','Pikachu','1 results') # 25 in National
    key(23);check('pikachu-entry','ENTRY','Pikachu')
    key(4,4);time.sleep(.5)
    adb('shell','am','force-stop',PACKAGE)
    adb('shell','am','start','-W','-n',PACKAGE+'/.PokedexActivity');time.sleep(1)
    check('preferences-survive-relaunch','Theme 2.','Animation off.','National')
    # Re-enter Oshawott in National to confirm caught/favorite persistence.
    key(7,12,7,8);check('national-oshawott','Oshawott') # National 501, Oshawott
    key(23);check('marks-survive-relaunch','Caught.','Favorite.')
else:
    key(23) # Begin edge checks in an entry, with persisted National/White settings.
# Test alternate-form return, raw corner keys, empty results and held-key suppression.
key(4);key(131);key(13,11,13);check('kyurem-search','Kyurem','1 results')
key(23);key(10);time.sleep(.5);check('kyurem-alternate-form','Black');shot('13-black-kyurem')
key(4);check('form-return-keeps-species','LIST','Kyurem')
key(134);check('raw-f4-dex','Unova')
key(134);check('raw-f4-national','National')
key(131);key(16,16,16);check('empty-number-search','No matching Pokémon','0 results');shot('14-empty-search')
key(4,4,4,4);check('empty-search-return','LIST')
key(132);check('raw-f2-options','JOURNAL OPTIONS')
key(20,22);check('favorites-filter','Collection 1.','Oshawott')
key(22);check('caught-filter','Collection 2.','Oshawott')
key(22,20,22);check('type-filter','Type filter Normal.')
adb('shell','input','keyevent','--longpress','23');time.sleep(.3)
check('held-ok-toggles-once','Type filter Fighting.')
key(20,20,20,20,20);key(23);key(4);check('reset-filters','Type filter All types.','649 results')
# Render several frames with animations on; then verify the sprite is actually changing.
key(17);key(20,20,20,20,20);key(22);key(4)
check('animations-reenabled','Animation on.')
key(7,11,16,11);key(23);time.sleep(.7) # National 494 Victini's distinct animation frames.
frames=[]
for n in range(8):
 frames.append(adb('exec-out','screencap','-p',raw=True));time.sleep(.3)
assert len(set(frames))>1,'Animated frames were identical'
results.append({'test':'animation-frames-change','passed':True})
(OUT/'15-animation-frame.png').write_bytes(frames[0])
key(22,22,23);check('animated-move-modal','MOVE RECORD')
key(4,21,21);time.sleep(.5)
resumed=[]
for n in range(6):
 resumed.append(adb('exec-out','screencap','-p',raw=True));time.sleep(.3)
assert len(set(resumed))>1,'Animation stopped after move modal'
results.append({'test':'animation-resumes-after-move-modal','passed':True})
before='Caught.' in desc()
adb('shell','input','keyevent','--longpress','133');time.sleep(.3)
assert ('Caught.' in desc()) != before,'Held raw F3 toggled more than once'
results.append({'test':'raw-f3-held-toggles-once','passed':True})
key(133) # Restore the previous journal mark.
# Audio playback decoding runs with host output disabled; record Android errors separately.
key(13);time.sleep(1)
(OUT/'runtime-errors.txt').write_text(adb('logcat','-d','-s','AndroidRuntime:E','MediaPlayer:E'))
(OUT/'meminfo.txt').write_text(adb('shell','dumpsys','meminfo',PACKAGE))
(OUT/('results-edges.json' if '--edges-only' in sys.argv else 'results.json')).write_text(json.dumps({'apkSha256':hashlib.sha256(TEST_APK.read_bytes()).hexdigest(),'serial':SERIAL,'android':adb('shell','getprop','ro.build.version.release'),'resolution':adb('shell','wm','size'),'tests':results},indent=2))
print('EMULATOR_OK',len(results),'checks',flush=True)
