#!/usr/bin/env python3
"""English/es-ES switching, restart persistence and reviews; no physical screenshots or writes."""
from pathlib import Path
import subprocess,time,json,xml.etree.ElementTree as E,datetime,sys
r=Path(__file__).resolve().parents[1];physical='--phone' in sys.argv;serial='YOUR_ADB_SERIAL' if physical else 'emulator-5582';checks=[];started=False
folder=r/'dist'/('hardware' if physical else 'qa-languages');folder.mkdir(exist_ok=True)
def adb(*a,raw=False):
 b=subprocess.check_output(['/usr/bin/adb','-s',serial,*map(str,a)],timeout=45);return b if raw else b.decode().strip()
def guard():
 if physical:
  lock=json.loads((r.parent/'.phone.lock').read_text());assert lock['owner']=='gps-walker-read' and datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now().astimezone()
  w=adb('shell','dumpsys','window');assert 'showing=false' in w and 'showing=true' not in w
  if started:assert 'org.kyf37.walker/' in next(x for x in w.splitlines() if 'mCurrentFocus=' in x)
 else:assert adb('shell','getprop','ro.kernel.qemu')=='1'
def key(k):
 guard()
 if physical:adb('shell','input','keyevent',224)
 adb('shell','input','keyevent',k);time.sleep(.4)
def desc():
 guard();adb('shell','uiautomator','dump','--compressed','/data/local/tmp/walker-languages.xml')
 return ' '.join(n.get('content-desc','') for n in E.fromstring(adb('shell','cat','/data/local/tmp/walker-languages.xml')).iter())
def check(n,*parts):
 d=desc();assert all(x.casefold() in d.casefold() for x in parts),(n,d);checks.append(n);print('PASS',n,flush=True)
def shot(n):
 if not physical:(folder/(n+'.png')).write_bytes(adb('exec-out','screencap','-p',raw=True))
def launch():
 global started
 started=False;guard();adb('shell','am','force-stop','org.kyf37.walker');adb('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity');time.sleep(1);started=True
launch();key(14)
if 'Idioma: Español (España)' in desc():key(132)
check('english-settings','SETTINGS & HELP','Language: English');key(132);check('spanish-settings','Ajustes y ayuda','Idioma: Español (España)');shot('01-spanish-settings')
launch();key(14);check('spanish-choice-survives-restart','Idioma: Español (España)');key(134);key(20);key(20);check('spanish-main','Pasear','Datos reales');shot('02-spanish-main')
key(15);check('spanish-real-device-menu','Pokéwalker real','Leer datos y pasos');shot('03-spanish-device-options')
for label in ['Copia de los datos','Añadir vatios y pasos','Regalar Pokémon','Regalar objeto','Extraer ROM']:
 key(20);check('spanish-operation-'+label,label)
key(23);check('spanish-rom-review','Confirma la extracción de ROM','Atrás cancela');key(134)
key(11);check('spanish-pokemon-editor','REGALO POKÉMON','Movimiento 1','Sexo: Macho','Variocolor: No','Habilidad: 9 Electricidad Estática');shot('04-spanish-pokemon-editor')
for i in range(10):key(20)
key(23);check('spanish-gift-review','Confirma los cambios','OK aplica','Atrás cancela');shot('05-spanish-review');key(134);check('review-back-to-editor','REGALO POKÉMON');key(134);check('editor-back-to-real-menu','Regalar Pokémon')
key(12);check('spanish-item-editor-open','REGALO DE OBJETO');key(23);key(12);key(7);check('spanish-item-catalog','Objeto: 50 Caramelo Raro');key(134);key(134);key(14);key(132);check('english-restored','SETTINGS & HELP','Language: English');key(134);check('english-main-restored','FLIP WALKER','Real save')
if physical:key(14);key(132);key(134);check('left-in-spanish','FLIP WALKER','Datos reales')
(folder/'languages.json').write_text(json.dumps({'checks':checks,'phone':physical,'screenshots':not physical,'real_peer_verified':False,'physical_write_operations_started':False},indent=2));print('LANGUAGE_UI_CHECKS='+str(len(checks)),flush=True)
