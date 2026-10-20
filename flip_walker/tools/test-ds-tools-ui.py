#!/usr/bin/env python3
"""Exercise six-operation menu/editors/review cancellation; never start a write."""
from pathlib import Path
import subprocess,time,json,xml.etree.ElementTree as E
r=Path(__file__).resolve().parents[1];physical='--phone' in __import__('sys').argv
serial='YOUR_ADB_SERIAL' if physical else 'emulator-5582';checks=[];started=False
def adb(*args):return subprocess.check_output(['/usr/bin/adb','-s',serial,*map(str,args)],timeout=45).decode().strip()
def guard():
 if physical:
  import datetime
  lock=json.loads((r.parent/'.phone.lock').read_text());assert lock['owner']=='gps-walker-read' and datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now().astimezone()
  w=adb('shell','dumpsys','window');assert 'showing=false' in w and 'showing=true' not in w
  if started:assert 'org.kyf37.walker/' in next(x for x in w.splitlines() if 'mCurrentFocus=' in x), 'Focus left Walker; stop sending keys'
 else:assert adb('shell','getprop','ro.kernel.qemu')=='1'
def key(k):guard();adb('shell','input','keyevent',224 if physical else k);(adb('shell','input','keyevent',k) if physical else None);time.sleep(.4)
def desc():
 guard();adb('shell','uiautomator','dump','--compressed','/data/local/tmp/ds-tools-ui.xml')
 return ' '.join(n.get('content-desc','') for n in E.fromstring(adb('shell','cat','/data/local/tmp/ds-tools-ui.xml')).iter())
def check(name,*parts):
 d=desc();assert all(x in d for x in parts),(name,d);checks.append(name);print('PASS',name,flush=True)
guard();adb('shell','am','force-stop','org.kyf37.walker');adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1);started=True
key(15);check('new-device-menu','REAL POKEWALKER','Read trainer & steps')
for label in ['Back up all data','Add watts & steps','Gift Pokemon','Gift item','Dump ROM']:
 key(20);check('operation-'+label,label)
key(23);check('rom-review-before-any-link','Confirm ROM dump','Temporary RAM payload');key(134);check('rom-review-cancelled','Dump ROM')
key(10);check('watts-editor','WATTS & STEPS','Watts to add: 100','Today steps (0=keep): 0','Max total steps: No')
key(23);key(9);key(7);key(7);check('keypad-watts-entry','Watts to add: 200')
key(20);key(23);key(12);key(7);check('keypad-today-entry','Today steps (0=keep): 50')
key(20);key(22);check('max-step-toggle','Max total steps: Yes');key(20);key(23);check('watts-review','Confirm changes','Watts to add: 200','Today steps (0=keep): 50');key(134);key(134)
key(11);check('pokemon-editor-complete-fields','POKEMON GIFT','Pokemon: 25 Pikachu','Move 4: 0 None','Gender: Male','Ability: 9 Static')
key(23);key(11);key(16);key(10);check('pokemon-catalog-numeric-selection','Pokemon: 493 Arceus')
for i in range(10):key(20)
key(23);check('pokemon-review-all-values','Confirm changes','Pokemon: 493 Arceus','Level: 50','Shiny: No')
key(134);key(134);key(12);check('item-editor','ITEM GIFT','Item: 4 Poke Ball');key(23);key(12);key(7);check('item-numeric-id','Item: 50 Rare Candy');key(20);key(23);check('item-review','Confirm changes','Item: 50 Rare Candy');key(134);key(134)
key(134);check('all-existing-main-functions-retained','FLIP WALKER');key(12);check('existing-game-connection','CONNECT TO GAME');key(134);key(14);check('existing-settings','SETTINGS & HELP');key(134)
folder=r/'dist'/('hardware' if physical else 'qa-ds-tools');folder.mkdir(exist_ok=True)
(folder/'ds-tools-ui.json').write_text(json.dumps({'checks':checks,'phone':physical,'write_operations_started':False,'real_peer_verified':False},indent=2));print('DS_TOOLS_UI_CHECKS='+str(len(checks)),flush=True)
