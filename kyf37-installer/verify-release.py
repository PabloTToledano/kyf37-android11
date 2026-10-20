#!/usr/bin/env python3
"""Verify an extracted release without importing phone or signing tools."""
import hashlib
import json
from pathlib import Path
import sys


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'release.json').read_text())
    for name, record in manifest['files'].items():
        path = root / name
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError('Missing or unsafe release file: ' + name)
        if path.stat().st_size != record['bytes']:
            raise ValueError('Size mismatch: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 << 20), b''):
                digest.update(block)
        if digest.hexdigest() != record['sha256']:
            raise ValueError('Checksum mismatch: ' + name)
    return len(manifest['files'])


if __name__ == '__main__':
    try:
        count = verify(Path(__file__).resolve().parent)
        print(f'Verified {count} release files. Phone not accessed.')
    except (OSError, ValueError, KeyError) as exc:
        print('Release verification failed: ' + str(exc), file=sys.stderr)
        sys.exit(1)
