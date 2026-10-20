#!/usr/bin/env python3
from pathlib import Path
import urllib.request,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[2]
PINS={'litert':'9b02cdf9db0a698b341b59e75c54ab8221d6304577cc43830d01024caf1fca74','litert-api':'66c2ba8086bd5cbf89bec2bd81c3de6c1a852312829cd55bc30c9dd26ffa357c'}
for artifact,digest in PINS.items():
 p=ROOT/'cache/classifier-planning'/f'{artifact}-1.4.2.aar';p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://dl.google.com/dl/android/maven2/com/google/ai/edge/litert/{artifact}/1.4.2/{artifact}-1.4.2.aar',timeout=60).read())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 with zipfile.ZipFile(p) as z:
  license_dir=ROOT/'app/assets/ml/licenses';license_dir.mkdir(parents=True,exist_ok=True);(license_dir/(artifact+'-LICENSE.txt')).write_bytes(z.read('LICENSE'))
  dest=ROOT/'app/libs';dest.mkdir(parents=True,exist_ok=True);(dest/(artifact+'.jar')).write_bytes(z.read('classes.jar'))
  for abi in ['armeabi-v7a','x86_64']:
   name=f'jni/{abi}/libtensorflowlite_jni.so'
   if name in z.namelist():
    lib=dest/abi/'libtensorflowlite_jni.so';lib.parent.mkdir(parents=True,exist_ok=True);lib.write_bytes(z.read(name))
print('RUNTIME_READY: pinned LiteRT 1.4.2, ARMv7 and emulator x86_64')
