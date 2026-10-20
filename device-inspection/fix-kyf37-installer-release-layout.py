#!/usr/bin/env python3
"""Rerunnable source changes for an installer with bundled release assets."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'kyf37-installer/kyf37_resources.py'
s = p.read_text()
if 'def bundled_rom(' not in s:
    s += '''

def bundled_rom(directory):
    """Select only the ROM explicitly recorded in the release manifest."""
    directory = Path(directory)
    release = directory / 'release.json'
    if not release.exists():
        return None
    metadata = json.loads(release.read_text())
    relative = metadata['rom']['path']
    path = directory / relative
    if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
        raise RuntimeError('Bundled ROM missing or outside release folder')
    if sha256(path) != metadata['rom']['sha256']:
        raise RuntimeError('Bundled ROM failed SHA-256 verification; extract a fresh release')
    return path
'''
s = s.replace('def platform_tools(directory):\n    system = platform.system()', 'def platform_tools(directory, system=None):\n    system = system or platform.system()')
p.write_text(s)
p = ROOT / 'kyf37-installer/kyf37_installer.py'
s = p.read_text()
marker = '# Bundled installer release layout v1'
if marker not in s:
    old = "str(HERE / 'platform-tools' / ('adb.exe' if os.name == 'nt' else 'adb')), shutil.which('adb')"
    new = "str(HERE / 'platform-tools' / ('adb.exe' if os.name == 'nt' else 'adb')), str(HERE / 'tools' / ('windows' if os.name == 'nt' else 'linux') / 'platform-tools' / ('adb.exe' if os.name == 'nt' else 'adb')), shutil.which('adb')"
    if old not in s: raise RuntimeError('ADB selection source changed')
    s = s.replace(old, new)
    old = "        from kyf37_resources import release_rom\n        say('Downloading the Android 11 ROM (verified downloads are cached)...')\n        rom = release_rom(HERE / '.downloads', args.rom_url, args.rom_sha256)"
    new = "        from kyf37_resources import release_rom, bundled_rom\n        rom = None if args.rom_url else bundled_rom(HERE)\n        if rom is None:\n            say('Downloading the Android 11 ROM (verified downloads are cached)...')\n            rom = release_rom(HERE / '.downloads', args.rom_url, args.rom_sha256)\n        else:\n            say(f'Using bundled ROM: {rom.name}')"
    if old not in s: raise RuntimeError('ROM selection source changed')
    s = s.replace(old, new)
    p.write_text(s + '\n' + marker + '\n')

# Public verifier source; no secrets or phone paths.
verifier_source = '#!/usr/bin/env python3\n"""Verify an extracted release without importing phone or signing tools."""\nimport hashlib\nimport json\nfrom pathlib import Path\nimport sys\n\n\ndef verify(root):\n    root = Path(root).resolve()\n    manifest = json.loads((root / \'release.json\').read_text())\n    for name, record in manifest[\'files\'].items():\n        path = root / name\n        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file():\n            raise ValueError(\'Missing or unsafe release file: \' + name)\n        if path.stat().st_size != record[\'bytes\']:\n            raise ValueError(\'Size mismatch: \' + name)\n        digest = hashlib.sha256()\n        with path.open(\'rb\') as stream:\n            for block in iter(lambda: stream.read(8 << 20), b\'\'):\n                digest.update(block)\n        if digest.hexdigest() != record[\'sha256\']:\n            raise ValueError(\'Checksum mismatch: \' + name)\n    return len(manifest[\'files\'])\n\n\nif __name__ == \'__main__\':\n    try:\n        count = verify(Path(__file__).resolve().parent)\n        print(f\'Verified {count} release files. Phone not accessed.\')\n    except (OSError, ValueError, KeyError) as exc:\n        print(\'Release verification failed: \' + str(exc), file=sys.stderr)\n        sys.exit(1)\n'
(ROOT / 'kyf37-installer/verify-release.py').write_text(verifier_source)
