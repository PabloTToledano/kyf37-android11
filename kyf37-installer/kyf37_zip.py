"""Rebuild the ROM installer ZIP around THIS phone and THIS owner's key.

The published ZIP is bound to one phone: its update-binary checks the serial number, the installed recovery and
keystore hashes, and ships a boot image signed with the maintainer's key (which a stock bootloader would reject).
Here the system image is streamed through unchanged, boot.img is re-signed with the user's key, and the checks in
update-binary are rewritten to the user's own serial and hashes. Nothing else in the installer is touched."""
import hashlib, json, re, zipfile
from pathlib import Path

import kyf37_crypto as K

UB = 'META-INF/com/google/android/update-binary'


def _sub(text, pattern, repl):
    new, n = re.subn(pattern, lambda m: repl, text, flags=re.M)
    if n != 1:
        raise K.SigningError(f'update-binary changed shape: {pattern!r} matched {n} times (expected 1)')
    return new


def build(rom_zip, out_zip, private, stock_boot, serial, recovery_sha, keystore_sha, log=print):
    rom_zip, out_zip = Path(rom_zip), Path(out_zip)
    with zipfile.ZipFile(rom_zip) as zin:
        names = set(zin.namelist())
        need = {UB, 'boot.img', 'system.raw.img', 'manifest.json', 'tools/clear-system-temp-wp', 'tools/clear-recovery-boot-temp-wp'}
        if not need <= names:
            raise K.SigningError(f'not a KYF37 ROM installer ZIP, missing {sorted(need - names)}')
        manifest = json.loads(zin.read('manifest.json'))
        boot = K.sign_image(zin.read('boot.img'), stock_boot, b'/boot', private)
        boot_sha = K.sha256(boot)
        ub = zin.read(UB).decode()
        ub = _sub(ub, r'^BOOT_HASH=[0-9a-f]{64}$', f'BOOT_HASH={boot_sha}')
        ub = _sub(ub, r'^RECOVERY_HASH=[0-9a-f]{64}$', f'RECOVERY_HASH={recovery_sha}')
        ub = _sub(ub, r'^KEYSTORE_HASH=[0-9a-f]{64}$', f'KEYSTORE_HASH={keystore_sha}')
        ub = _sub(ub, r'\[ "\$\(getprop ro\.serialno\)" = [0-9A-Za-z]+ \] \|\| die [^\n]*',
                  f'[ "$(getprop ro.serialno)" = {serial} ] || die \'This ZIP was built for serial {serial}.\'')
        manifest['images']['boot.img'] = boot_sha
        manifest['installer_sha256'] = hashlib.sha256(ub.encode()).hexdigest()
        manifest['built_for_serial'] = serial
        log(f'  re-signed boot.img with your key: {boot_sha}')
        with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_STORED, allowZip64=True) as zout:
            for info in zin.infolist():
                if info.filename == 'boot.img':
                    zout.writestr('boot.img', boot)
                elif info.filename == UB:
                    zout.writestr(UB, ub)
                elif info.filename == 'manifest.json':
                    zout.writestr('manifest.json', json.dumps(manifest, indent=2) + '\n')
                else:  # system.raw.img and the tools: copied byte for byte, streamed
                    with zin.open(info) as src, zout.open(info.filename, 'w', force_zip64=True) as dst:
                        while True:
                            chunk = src.read(8 << 20)
                            if not chunk:
                                break
                            dst.write(chunk)
    return boot_sha
