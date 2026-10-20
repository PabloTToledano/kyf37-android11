#!/usr/bin/env python3
"""Fetch official Android emulator test dependencies, without using a physical phone."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,zipfile,os,hashlib
r=Path(__file__).resolve().parents[1]/'cache/android-sdk'
def fetch(args):
 url,name,dest=args; archive=r/name
 if not archive.exists():
  with urllib.request.urlopen(url,timeout=120) as src, archive.with_suffix('.tmp').open('wb') as out:
   while data:=src.read(1024*1024):out.write(data)
  archive.with_suffix('.tmp').replace(archive)
 if name=='emulator35.zip':
  assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2fe2b56fe93ce75e1d478a40162131381d911c355efeaedb54dd1e0d0897a5cf'
 dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   z.extract(info,dest)
   mode=(info.external_attr>>16)&0o777
   if mode:os.chmod(dest/info.filename,mode)
 print('READY',name,flush=True)
with ThreadPoolExecutor(max_workers=2) as ex:
 list(ex.map(fetch,[('https://dl.google.com/android/repository/emulator-linux_x64-13610412.zip','emulator35.zip',r),('https://dl.google.com/android/repository/sys-img/android/x86_64-30_r11.zip','system.zip',r/'system-images/android-30/default')]))
