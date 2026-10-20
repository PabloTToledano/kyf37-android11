#!/usr/bin/env python3
"""Assemble a public-asset allowlist into a stock-phone installer release.

No Android compilation, signing-key access, ADB invocation or phone access.
Never copies workspaces, backups, device logs, .venv or arbitrary directories.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'kyf37-installer'
sys.path.insert(0, str(SOURCE))
from kyf37_resources import download, platform_tools, sha256

DEFAULT_ROM = ROOT / 'kyf37-rom/kyf37-android11-go-walker-ir-v9f-ui2-magisk-20261016-twrp.zip'
SCRIPTS = ('install.sh', 'install.ps1', 'bootstrap.py', 'requirements.txt', 'kyf37_installer.py',
           'kyf37_crypto.py', 'kyf37_apps.py', 'kyf37_diag.py', 'kyf37_zip.py', 'kyf37_resources.py', 'verify-release.py')
PAYLOAD = ('SHA256SUMS', 'busybox', 'magisk', 'Magisk-v23.0.apk', 'enable-app-root.sh',
           'clear-system-temp-wp', 'clear-recovery-boot-temp-wp', 'kyf37-twrp-candidate.img')
UB = 'META-INF/com/google/android/update-binary'


def validate_rom(path):
    with zipfile.ZipFile(path) as z:
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError('ROM has duplicate archive entries')
        manifest = json.loads(z.read('manifest.json'))
        if manifest.get('android') != '11':
            raise ValueError('This stock installer release requires an Android 11 package')
        installer = z.read(UB)
        if hashlib.sha256(installer).hexdigest() != manifest['installer_sha256']:
            raise ValueError('ROM installer checksum mismatch')
        for name, expected in manifest['images'].items():
            if name not in ('boot.img', 'system.raw.img'):
                raise ValueError('Unexpected ROM image: ' + name)
            h = hashlib.sha256()
            with z.open(name) as stream:
                for block in iter(lambda: stream.read(8 << 20), b''):
                    h.update(block)
            if h.hexdigest() != expected:
                raise ValueError('ROM image checksum mismatch: ' + name)
        if set(manifest['images']) != {'boot.img', 'system.raw.img'}:
            raise ValueError('Incomplete matching ROM image set')
        # Ensure per-phone rebinding recognizes this installer before distributing it.
        import kyf37_zip as builder
        text = installer.decode()
        for field in ('BOOT_HASH', 'RECOVERY_HASH', 'KEYSTORE_HASH'):
            builder._sub(text, rf'^{field}=[0-9a-f]{{64}}$', field + '=' + '0' * 64)
        builder._sub(text, r'\[ "\$\(getprop ro\.serialno\)" = [0-9A-Za-z]+ \] \|\| die [^\n]*',
                     '[ "$(getprop ro.serialno)" = TEST1234 ] || exit 1')
        return manifest


def copy_public(src, destination):
    if src.is_symlink() or not src.is_file():
        raise ValueError('Public source missing or symlink: ' + str(src))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, destination)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom', type=Path, default=DEFAULT_ROM)
    ap.add_argument('--dest', type=Path, default=ROOT / 'releases/kyf37-stock-installer-20261020-apps-experimental')
    args = ap.parse_args()
    destination = args.dest.resolve()
    if destination.exists():
        # Preserve existing release outputs; validate rather than overwrite.
        spec = importlib.util.spec_from_file_location('verify_release', SOURCE / 'verify-release.py')
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        metadata = json.loads((destination / 'release.json').read_text())
        verifier.verify(destination)
        if metadata['rom']['sha256'] != sha256(args.rom):
            raise ValueError('Existing release uses another ROM; choose a new destination')
        from kyf37_apps import load_apps
        selected_apps = [a for a, _ in load_apps(SOURCE / 'apps')]
        if metadata.get('apps') != selected_apps:
            raise ValueError('Existing release uses other app APKs; choose a new destination')
        print('Existing release verified; preserved:', destination)
        return
    print('Validating ROM image hashes and installer compatibility...', flush=True)
    rom_manifest = validate_rom(args.rom)
    # Verify only the seven explicitly public payloads; never inspect any key path.
    for line in (SOURCE / 'payload/SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        if name not in PAYLOAD or sha256(SOURCE / 'payload' / name) != digest:
            raise ValueError('Bundled payload checksum mismatch: ' + name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.installer-package-', dir=destination.parent) as temporary:
        stage = Path(temporary) / destination.name
        stage.mkdir()
        for name in SCRIPTS:
            copy_public(SOURCE / name, stage / name)
        for name in PAYLOAD:
            copy_public(SOURCE / 'payload' / name, stage / 'payload' / name)
        from kyf37_apps import load_apps
        applications = load_apps(SOURCE / 'apps')
        copy_public(SOURCE / 'apps/apps.json', stage / 'apps/apps.json')
        for app, path in applications:
            copy_public(path, stage / 'apps' / app['file'])
        for directory, name in (('flip_pokedex', 'POKEDEX'), ('flip_walker', 'WALKER')):
            copy_public(ROOT / directory / 'README.md', stage / 'docs/apps' / (name + '.md'))
            copy_public(ROOT / directory / 'THIRD_PARTY.md', stage / 'docs/apps' / (name + '-THIRD-PARTY.md'))
        copy_public(ROOT / 'flip_walker/LICENSE', stage / 'docs/apps/WALKER-LICENSE.txt')
        copy_public(SOURCE / 'README.md', stage / 'docs/INSTALLER.md')
        for name in ('LICENSE', 'NOTICE'):
            copy_public(ROOT / name, stage / name)
        rom_path = stage / 'rom' / args.rom.name
        copy_public(args.rom, rom_path)
        for system in ('Linux', 'Windows'):
            print('Obtaining bundled ' + system + ' platform-tools...', flush=True)
            directory = stage / 'tools' / system.lower()
            platform_tools(directory, system=system)
            (directory / 'platform-tools.zip').unlink()
        print('Obtaining Windows diagnostic driver utility...', flush=True)
        download('https://github.com/pbatard/libwdi/releases/download/v1.5.1/zadig-2.9.exe', stage / 'tools/windows/zadig-2.9.exe')
        (stage / 'docs/recovery').mkdir()
        (stage / 'docs/recovery/USB-RECOVERY.md').write_text(RECOVERY)
        (stage / 'START-HERE.md').write_text(START_HERE)
        (stage / 'README.md').write_text(START_HERE)
        (stage / 'docs/CONTENTS.md').write_text(CONTENTS)
        (stage / 'install.cmd').write_bytes(b'@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*\r\nexit /b %errorlevel%\r\n')
        (stage / 'install.sh').chmod(0o755)
        files = {p.relative_to(stage).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha256(p)}
                 for p in sorted(stage.rglob('*')) if p.is_file()}
        metadata = {'format': 1, 'name': destination.name, 'experimental': True,
                    'apps': [a for a, _ in applications],
                    'stock_to_custom_verified': False, 'windows_execution_verified': False,
                    'rom': {'path': rom_path.relative_to(stage).as_posix(), 'sha256': sha256(rom_path),
                            'manifest': rom_manifest}, 'files': files}
        (stage / 'release.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (stage / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {name}\n" for name, r in files.items()) +
                                        sha256(stage / 'release.json') + '  release.json\n')
        # Cross-platform ZIP: preserve Linux executable bits and store existing compressed assets.
        archive = destination.with_suffix('.zip')
        if archive.exists(): raise ValueError('Archive already exists; refusing overwrite')
        temporary_archive = Path(temporary) / archive.name
        print('Writing distributable ZIP...', flush=True)
        with zipfile.ZipFile(temporary_archive, 'w', allowZip64=True) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():
                    z.write(p, destination.name + '/' + p.relative_to(stage).as_posix(),
                            compress_type=zipfile.ZIP_STORED if p.suffix in ('.zip', '.apk') else zipfile.ZIP_DEFLATED)
        stage.replace(destination)
        temporary_archive.replace(archive)
        archive.with_suffix('.zip.sha256').write_text(sha256(archive) + '  ' + archive.name + '\n')
    print('Release folder:', destination)
    print('Release ZIP:', archive)


START_HERE = '''# KYF37 stock-to-custom installer — experimental release

Extract the entire ZIP to a writable folder. Keep all files together.
This package includes the Android 11 Go ROM template, custom keypad TWRP recovery, rooting tools,
ADB for x86-64 Linux and Windows, and the Windows Zadig driver utility. The installer selects the included ROM automatically.
Flip Pokédex and Flip Walker APKs are also included and installed as the final stage after Android boots.
The ROM template must be personalized by the installer; do not flash it or the recovery image directly.

1. Charge a stock KYF37 on Android 5.1 to at least 50%. Enable USB debugging and authorize your computer.
2. Insert a FAT32 microSD with at least 3 GB free. Allow at least 8 GB free on the computer.
3. Linux: run `./install.sh`. Windows: double-click `install.cmd`, or run `.\\install.ps1` in PowerShell.
4. The first launch downloads missing Python and Python packages. ADB, recovery and ROM are already included.
5. Start with the default dry run. Read `docs/INSTALLER.md`, then use `./install.sh --live` or
   `.\\install.cmd --live` when ready. Every write stage asks for typed confirmation.
6. Keep USB connected through the first Android boot. Stage 9 waits for boot completion and installs both apps.
   To resume only app installation: `./install.sh --live --stage apps` or `.\\install.cmd --live --stage apps`.
   Matching APKs are skipped, newer versions retained and existing app data preserved. Apps are not launched automatically.

Windows diagnostic rooting needs WinUSB on interface 0 of 05c6:9091. Use the included
`tools/windows/zadig-2.9.exe`; select only interface 0 and keep interface 3 as ADB.
Linux may need the USB permissions rule printed by the installer. Internet is needed for first-time Python
setup. These administrator/driver steps remain manual.

To check the extracted files without accessing a phone: `python3 verify-release.py` on Linux or
`py -3 verify-release.py` on Windows. `SHA256SUMS` lists all packaged file checksums.

Keep the per-phone workspace and original backups. Never share your generated private signing key.
Do not wipe userdata or flash the stock ROM. Do not enter a SIM PIN through automation.

This is a distribution-ready experimental bundle, not a hardware-certified stock-phone conversion.
The included ROM manifest reports hardware_verified=false. Stock-to-custom conversion and native Windows
execution remain unverified. No phone was changed while preparing this package.
'''
CONTENTS = '''# Package contents

- `install.sh`, `install.ps1`, `install.cmd`: Linux/Windows entry points; dry run by default.
- `bootstrap.py`, `requirements.txt`: automatically downloaded Python dependencies.
- `payload/kyf37-twrp-candidate.img`: custom keypad TWRP source image; signed for each recipient during setup.
- `payload/`: BusyBox, Magisk 23 APK/binary, root helper and temporary write-protection helpers.
- `rom/`: matching Android 11 Go boot/system installer template; personalized before sideload.
- `apps/`: Flip Pokédex and Flip Walker APKs plus package/version/checksum metadata.
- `docs/apps/`: app usage and third-party notices. The Pokédex includes offline artwork/classifier assets;
  Flip Walker IR features require compatible ROM support and user-approved permissions/root access.
- `tools/linux/platform-tools/`, `tools/windows/platform-tools/`: Google ADB and companion libraries/notices.
- `tools/windows/zadig-2.9.exe`: diagnostic USB driver tool from the official libwdi release; manual interface selection.
- `release.json`, `SHA256SUMS`, `verify-release.py`: inventory, hashes and offline integrity verification.
- `docs/INSTALLER.md`: detailed stages, backup/resume behavior and recovery guidance.
- `LICENSE`, `NOTICE`: project licensing; bundled upstream software retains its original licenses.

BusyBox is GPL-2.0 (https://busybox.net/); Magisk is GPL-3.0 (https://github.com/topjohnwu/Magisk);
TWRP has GPL/Apache components (https://github.com/TeamWin). Google platform-tools retain their bundled
NOTICE and distribution terms. The ROM includes AOSP/LineageOS and device-specific proprietary components;
the project Apache license does not relicense those components. See NOTICE.

Zadig/libwdi: https://github.com/pbatard/libwdi (GPL-3.0).

No signing private keys, phone backups, host virtual environment, device logs or per-phone workspace are included.
'''

RECOVERY = """# Before starting and if installation stops

The installer first backs up the stock partitions to the microSD and keeps the essential signing inputs in
its per-phone workspace. This backup excludes userdata; copy personal files separately before starting.
Keep the complete workspace, generated signing key and microSD backup private and intact.

The stock-phone installer includes a guided microSD rescue test. Complete it before any signing-partition
changes. It creates NOTPUSH, CHKCODE and FASTBOOT markers with DEVKEYDL content, asks the user to test the
0482:0a7f USB download entry, and removes its markers afterwards. If interrupted, check the card on a computer
and remove these three markers before a normal boot. Existing unknown markers are never overwritten.

After a failed write, remain in recovery. A software rollback may have been attempted, but it must be checked
against the recorded partition hashes. A power interruption or mixed signing state requires investigation;
do not keep retrying unknown partition writes. Preserve all original and custom rollback backups.

Do not factory-reset or wipe userdata. Do not flash the stock ROM, or use another device's keystore, radio,
modem, persist or calibration images. Rescue USB detection is not a complete unbrick procedure.

The ROM/recovery in this package are templates for per-phone signing. Never install the bundled ROM ZIP or
recovery image directly. Resume through the installer with the original workspace and key.

If you need help, share the stage name and error text after reviewing it for personal information.
Never share a private signing key, per-phone partition backup or calibration data.
"""

if __name__ == '__main__':
    main()

# Bundled app packaging v1
