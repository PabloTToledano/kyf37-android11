#!/usr/bin/env python3
"""Cache official Android build-tools 30.0.3 (SDK repository's SHA-1 verified)."""
from pathlib import Path
import urllib.request,hashlib,zipfile,os,fcntl
root=Path(__file__).resolve().parents[1]/'cache';archive=root/'build-tools_r30.0.3-linux.zip';root.mkdir(exist_ok=True)
sdk_lock=(root/'sdk-prepare.lock').open('w');fcntl.flock(sdk_lock,fcntl.LOCK_EX)
if not archive.exists():
    with urllib.request.urlopen('https://dl.google.com/android/repository/build-tools_r30.0.3-linux.zip',timeout=90) as src,archive.with_suffix('.tmp').open('wb') as out:
        while data:=src.read(1024*1024):out.write(data)
    archive.with_suffix('.tmp').replace(archive)
assert hashlib.sha1(archive.read_bytes()).hexdigest()=='2076ea81b5a2fc298ef7bf85d666f496b928c7f1'
dest=root/'build-tools'
if not (dest/'android-11/aapt2').exists():
    with zipfile.ZipFile(archive) as z:
        for f in z.infolist():
            z.extract(f,dest);mode=f.external_attr>>16&0o777
            if mode:os.chmod(dest/f.filename,mode)
print(dest/'android-11')
