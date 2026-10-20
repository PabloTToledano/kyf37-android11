#!/usr/bin/env python3
"""Download and verify the complete pinned installer; does not access the phone."""
import hashlib
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile
NAME = 'kyf37-customizer-20261020'
URL = 'https://github.com/PabloTToledano/kyf37-customizer/releases/download/v2026.10.20-experimental/' + NAME + '.zip'
EXPECTED = '1beaa025f7f6f783ff758addd188e195e09ffcbd3f8b0d92d608598237f8d1b1'

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''): result.update(block)
    return result.hexdigest()

root = Path.cwd()
archive = root / (NAME + '.zip')
if not archive.is_file() or digest(archive) != EXPECTED:
    temporary = archive.with_suffix('.zip.download')
    try:
        print('Downloading complete installer (about 852 MiB)...', flush=True)
        with urllib.request.urlopen(URL, timeout=120) as response, temporary.open('wb') as out:
            shutil.copyfileobj(response, out, 8 << 20)
        if digest(temporary) != EXPECTED: raise SystemExit('SHA-256 mismatch; nothing extracted')
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
if (root / NAME).exists():
    raise SystemExit('Release folder already exists; keep it and follow its START-HERE.md')
with zipfile.ZipFile(archive) as z:
    for info in z.infolist():
        target = root / info.filename
        if not target.resolve().is_relative_to(root.resolve()) or (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise SystemExit('Unsafe archive entry')
    z.extractall(root)
(root / NAME / 'install.sh').chmod(0o755)
print('Verified and extracted: ' + str(root / NAME))
print('Read START-HERE.md; Linux: ./install.sh; Windows: install.cmd. Dry run is the default.')
