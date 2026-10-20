#!/usr/bin/env python3
"""Restore the Spanish preference used before the initial footer check."""
from pathlib import Path
import subprocess,json,datetime,time,xml.etree.ElementTree as E
r=Path(__file__).resolve().parents[2]
def run(c):
 lock=json.loads((r.parent/'.phone.lock').read_text());assert lock['owner']=='gps-walker-read' and datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now().astimezone()
 return subprocess.check_output(['/usr/bin/adb','-s','YOUR_ADB_SERIAL','shell',c],text=True,timeout=40).strip()
w=run('dumpsys window');assert 'showing=false' in w and 'showing=true' not in w;assert 'org.kyf37.walker/' in next(x for x in w.splitlines() if 'mCurrentFocus=' in x)
run('input keyevent 133');time.sleep(1);run('uiautomator dump --compressed /data/local/tmp/footer-language.xml')
d=' '.join(n.get('content-desc','') for n in E.fromstring(run('cat /data/local/tmp/footer-language.xml')).iter())
if 'Language: English' in d:run('input keyevent 132');time.sleep(1)
run('uiautomator dump --compressed /data/local/tmp/footer-language.xml');assert 'Idioma: Español (España)' in run('cat /data/local/tmp/footer-language.xml');run('input keyevent 134');print('SPANISH_PREFERENCE_RESTORED')
