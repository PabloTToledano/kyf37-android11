#!/usr/bin/env python3
"""KYF37 installer: stock Android 5.1 -> root -> backup -> custom TWRP -> custom Android 11 ROM.

Interactive, stage by stage. DRY RUN is the default: every step that would change the phone is printed instead of
run (read-only checks and offline work on this computer still run). Add --live to really write, and even then every
risky stage asks for a typed confirmation first.

UNTESTED ON STOCK HARDWARE. The author's phone is already converted, so this exact script has never been run end to
end on a stock KYF37. The individual pieces (diagnostic root route, signing, partition writes, TWRP install, ROM
install) are taken from procedures that worked on that phone; read README.md before using --live."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / 'payload'
sys.path.insert(0, str(HERE))
import kyf37_crypto as K

DRY = True
WORK = None            # per-phone workspace
STATE = {}
LOCK_PHRASE = 'I UNDERSTAND'


# ---------------------------------------------------------------------------------------------- output / helpers
def say(msg=''):
    print(msg, flush=True)


def head(title):
    say(); say('=' * 78); say(title); say('=' * 78)


def ask(prompt, default=None):
    try:
        v = input(prompt + (f' [{default}]' if default else '') + ': ').strip()
    except EOFError:
        raise SystemExit('\ninput closed')
    return v or (default or '')


def pause(msg='Press Enter to continue'):
    ask(msg)


def confirm_write(what):
    """Typed confirmation before anything that changes the phone."""
    say(f'\nABOUT TO CHANGE THE PHONE: {what}')
    if DRY:
        say('(dry run: nothing will be written; this shows what --live would do)')
        return True
    return ask(f'Type "{LOCK_PHRASE}" to continue, anything else cancels') == LOCK_PHRASE


def find_adb():
    for c in (os.environ.get('ADB'), str(HERE / 'platform-tools' / ('adb.exe' if os.name == 'nt' else 'adb')), str(HERE / 'tools' / ('windows' if os.name == 'nt' else 'linux') / 'platform-tools' / ('adb.exe' if os.name == 'nt' else 'adb')), shutil.which('adb')):
        if c and Path(c).exists():
            return c
    from kyf37_resources import platform_tools
    say('Downloading Android platform-tools from Google...')
    return platform_tools(HERE / '.downloads')


ADB = None
SERIAL = None


def adb(*args, check=True, timeout=120, write=False):
    """Run adb. write=True marks a command that changes the phone: it is only printed in a dry run."""
    cmd = [ADB, *(['-s', SERIAL] if SERIAL and args[0] != 'devices' else []), *args]
    if write and DRY:
        say(f'  [dry-run] would run: adb {" ".join(args)}'); return ''
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout + r.stderr).strip()
    if check and r.returncode != 0:
        raise RuntimeError(f'adb {" ".join(args)} failed: {out}')
    return out


def shell(cmd, **kw):
    return adb('shell', cmd, **kw)


def su(cmd, **kw):
    if "'" in cmd:
        raise ValueError('no single quotes in su commands')
    if getprop('ro.twrp.version'):
        return shell(cmd, **kw)
    return adb('shell', f"su -c '{cmd}'", **kw)


def getprop(name):
    return shell(f'getprop {name}', check=False).strip()


def have_su():
    return 'uid=0' in shell('id' if getprop('ro.twrp.version') else "su -c 'id'", check=False)


def wait_adb(state='device', seconds=240):
    end = time.time() + seconds
    while time.time() < end:
        out = adb('devices', check=False)
        if re.search(rf'^{re.escape(SERIAL)}\s+{state}$', out, re.M):
            return True
        time.sleep(3)
    return False


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_payload():
    for line in (PAYLOAD / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1)
        name = name.strip().lstrip('*')
        if sha_file(PAYLOAD / name) != digest:
            raise SystemExit(f'payload file {name} is damaged or modified; get a fresh copy of the installer')


def lock_workspace():
    """OS lock released automatically on exit, including crashes."""
    import atexit
    handle = open(WORK / '.installer.lock', 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            handle.write(b'0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise SystemExit('Another installer is using this phone workspace')
    atexit.register(handle.close)


def save_state():
    temporary = WORK / 'state.json.tmp'
    temporary.write_text(json.dumps(STATE, indent=2))
    temporary.replace(WORK / 'state.json')


def done(stage):
    if DRY:
        return
    STATE['schema'] = 2
    STATE.setdefault('done', {})[stage] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_state()


# ---------------------------------------------------------------------------------------------- stages
def stage_check():
    head('1. Check the phone and this computer')
    state = adb('get-state', check=False)
    if 'device' not in state:
        say('No phone found over adb. On the phone: Settings > Developer options > USB debugging, connect USB, accept the prompt.')
        return False
    model, rel, serial = getprop('ro.product.model'), getprop('ro.build.version.release'), getprop('ro.serialno')
    say(f'  model {model}   Android {rel}   serial {serial}')
    if model != 'KYF37':
        say('This installer is only for the KYF37.'); return False
    if not rel.startswith('5.1') and 'twrp' not in STATE.get('done', {}):
        say(f'Expected the stock Android 5.1 ROM, found {rel}. If this is already a custom ROM, do not run this installer.'); return False
    STATE.update(serial=serial, release=rel)
    batt = re.search(r'level: (\d+)', shell('dumpsys battery', check=False))
    level = int(batt.group(1)) if batt else 0
    say(f'  battery {level}%')
    if level < 50:
        say('Charge to at least 50% first (a power loss during a partition write can brick the phone).'); return False
    free = shutil.disk_usage(WORK).free / 1e9
    say(f'  free space on this computer: {free:.1f} GB (need about 8 GB)')
    if free < 8:
        return False
    try:
        import cryptography, usb  # noqa: F401
    except ImportError as e:
        say(f'Missing Python module: {e.name}. Use install.sh / install.ps1, which sets up a virtual environment.'); return False
    verify_payload()
    say('  bundled tools verified')
    say('  root (su): ' + ('already available' if have_su() else 'not yet'))
    done('check'); return True


def parcel_int(out):
    words = re.findall(r'[0-9a-f]{8}', out.split('(', 1)[-1])
    return int(words[1], 16) if len(words) > 1 else None


def stage_diag():
    head('2. Factory diagnostic USB mode')
    say('Stock Kyocera firmware has a hidden diagnostic USB mode (VID:PID 05c6:9091) that gives a root shell.')
    say('It is switched on through the "transfer" system service (the same step used on the author\'s phone).')
    cur = parcel_int(shell('service call transfer 1', check=False))
    say(f'  current rw_qfunc_mode: {cur}')
    if cur == 1:
        say('  already enabled'); done('diag'); return True
    if cur is None:
        say('The "transfer" service did not answer. This firmware may differ from the one this was written for. Stopping.')
        return False
    if not confirm_write('set rw_qfunc_mode=1 (diagnostic USB mode on next boot) and reboot the phone'):
        return False
    shell('service call transfer 3 i32 1', write=True)
    if not DRY and parcel_int(shell('service call transfer 1', check=False)) != 1:
        say('Readback did not confirm the new value; nothing else was changed. Stopping.'); return False
    adb('reboot', write=True)
    if not DRY:
        say('Waiting for the phone to restart...')
        if not wait_adb():
            return False
    say('\nWindows only, once: install the WinUSB driver for interface 0 of "05c6:9091" with Zadig')
    say('(Options > List all devices; pick the entry whose interface is 0; driver WinUSB; Replace Driver).')
    say('Do NOT replace the driver of interface 3 (that is ADB).')
    say('Linux: either run this script with sudo, or add a udev rule:')
    say('  echo \'SUBSYSTEM=="usb", ATTR{idVendor}=="05c6", ATTR{idProduct}=="9091", MODE="0666"\' | sudo tee /etc/udev/rules.d/99-kyf37-diag.rules')
    say('  sudo udevadm control --reload-rules && sudo udevadm trigger')
    done('diag'); return True


def open_diag():
    from kyf37_diag import Diag
    return Diag()


def stage_root():
    head('3. Root the phone (su)')
    if have_su():
        say('  su already works'); done('root'); return True
    say('Pushes BusyBox + Magisk 23 to /data/local/tmp, switches SELinux to permissive through the factory flags, then')
    say('starts the Magisk daemon through the diagnostic root shell. Root lasts until the next reboot; the later stages')
    say('re-run this automatically when needed.')
    if not confirm_write('push tools, set factory flag 4 (permissive), start Magisk, install the Magisk app'):
        return False
    verify_payload()
    for name, dst in (('busybox', 'busybox'), ('magisk', 'magisk'), ('enable-app-root.sh', 'enable-app-root.sh'),
                      ('clear-system-temp-wp', 'clear-system-temp-wp'), ('clear-recovery-boot-temp-wp', 'clear-recovery-boot-temp-wp')):
        adb('push', str(PAYLOAD / name), f'/data/local/tmp/{dst}', write=True)
    if DRY:
        say('  [dry-run] would then: chmod tools; diag shell -> factory flags 4 -> reboot -> start magisk daemon -> install Magisk app -> check su')
        return True
    d = open_diag()
    try:
        say('  diagnostic shell: ' + d.shell('id').strip())
        d.shell('chmod 755 /data/local/tmp/busybox /data/local/tmp/magisk /data/local/tmp/clear-system-temp-wp /data/local/tmp/clear-recovery-boot-temp-wp')
        status = d.factory_status()
        say(f'  factory status: {status}')
        if getprop('ro.boot.selinux') != 'permissive' and 'permissive' not in shell('getenforce', check=False).lower():
            d.set_factory_flags(4)
            say('  factory flags set to 4; rebooting')
            adb('reboot', write=True); d.close(); time.sleep(15)
            if not wait_adb():
                return False
            time.sleep(10)
            d = open_diag()
        d.shell('/data/local/tmp/magisk --daemon; chmod 711 /data/local/tmp')
        d.shell('/data/local/tmp/magisk --sqlite "REPLACE INTO policies (uid,policy,until,logging,notification) VALUES (2000,2,0,1,1)"')
        d.shell('sh /data/local/tmp/enable-app-root.sh')
    finally:
        try:
            d.close()
        except Exception:
            pass
    adb('install', '-r', str(PAYLOAD / 'Magisk-v23.0.apk'), check=False)
    if not have_su():
        say('su still does not work. Look at the Magisk app on the phone, accept any superuser prompt, then run this stage again.')
        return False
    say('  root OK'); done('root'); return True


def ensure_root():
    if have_su():
        return True
    say('Root is not active (it resets on reboot); re-activating...')
    return stage_root() and (DRY or have_su())


def sd_path():
    for c in ('/storage/sdcard1', '/storage/extSdCard', '/storage/external_SD', '/storage/emulated/1'):
        if shell(f'ls {c}', check=False) and 'No such' not in shell(f'ls -d {c}', check=False):
            if 'vfat' in shell(f"mount | grep ' {c} '", check=False) or 'fuse' in shell(f"mount | grep {c}", check=False):
                return c
    guess = ask('Could not find the microSD automatically. Path of the card on the phone (e.g. /storage/sdcard1)')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', guess) or '..' in guess.split('/'):
        raise ValueError('Invalid microSD path')
    return guess


def by_name():
    names = shell('ls /dev/block/bootdevice/by-name', check=False).split()
    sizes = {}
    for n in names:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', n):
            raise ValueError('Invalid partition name')
        real = shell(f'readlink /dev/block/bootdevice/by-name/{n}', check=False).strip().split('/')[-1]
        sectors = shell(f'cat /sys/class/block/{real}/size', check=False).strip()
        sizes[n] = int(sectors) * 512 if sectors.isdigit() else 0
    return sizes


def stage_backup():
    head('4. Back up the original firmware to the microSD card')
    if not ensure_root():
        return False
    sd = sd_path()
    if not sd:
        return False
    parts = {n: s for n, s in by_name().items() if n not in ('userdata', 'cache') and s}
    if not {'aboot', 'boot', 'recovery', 'keystore', 'misc'} <= parts.keys():
        raise RuntimeError('Required partitions missing; refusing an incomplete backup')
    if not getprop('ro.build.version.release').startswith('5.1'):
        raise RuntimeError('Original firmware backup requires stock Android 5.1; refusing to back up a converted ROM as stock')
    total = sum(parts.values())
    rows = shell(f'df -k {sd}', check=False).splitlines()
    fields = rows[-1].split() if rows else []
    # Android toolbox: Filesystem Size Used Free Blksize; BusyBox: ... Available Use%.
    avail = int(fields[3]) * 1024 if len(fields) >= 4 and fields[3].isdigit() else 0
    # Existing verified backups do not need their space allocated a second time.
    progress = WORK / 'backup-progress.json'
    previous = json.loads(progress.read_text()) if progress.exists() else {}
    remaining = sum(size for n, size in parts.items() if n not in previous)
    if not avail:
        raise RuntimeError('Cannot determine free microSD space')
    if avail < remaining + (64 << 20):
        say(f'  the card has {avail / 1e9:.2f} GB free but {total / 1e9:.2f} GB is needed; use a bigger or emptier card'); return False
    say(f'  card: {sd}   partitions: {len(parts)}   data to copy: {total / 1e9:.2f} GB')
    say('  (userdata and cache are not copied: your apps and files are not part of this backup)')
    dst = f'{sd}/kyf37-stock-backup-{STATE["serial"]}'
    if not confirm_write(f'copy {len(parts)} partitions to {dst} on the microSD (read from the phone, written to the card only)'):
        return False
    shell(f'mkdir -p {dst}', write=True, check=False)
    manifest_path = WORK / 'backup-progress.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for n, size in sorted(parts.items()):
        say(f'  {n} ({size / 1e6:.1f} MB)')
        if DRY:
            continue
        exists = su(f'test -e {dst}/{n}.img && echo EXISTS', check=False) == 'EXISTS'
        if exists:
            # Never replace the original with a potentially modified live partition.
            entry = manifest.get(n)
            if not entry or entry['bytes'] != size:
                raise RuntimeError(f'Untracked existing backup {n}; preserve it and resolve manually')
            digest = su(f'/data/local/tmp/busybox md5sum {dst}/{n}.img').split()[0]
            if digest != entry['md5']:
                raise RuntimeError(f'Existing backup {n} failed verification; refusing overwrite')
            say('    verified existing backup; skipping copy')
            continue
        su(f'/data/local/tmp/busybox dd if=/dev/block/bootdevice/by-name/{n} of={dst}/{n}.img.partial bs=1048576')
        a = su(f'/data/local/tmp/busybox md5sum /dev/block/bootdevice/by-name/{n}').split()[0]
        b = su(f'/data/local/tmp/busybox md5sum {dst}/{n}.img.partial').split()[0]
        if a != b:
            say(f'    CHECKSUM MISMATCH on {n}: stopping. Do not continue.'); return False
        manifest[n] = {'bytes': size, 'md5': a}
        progress_tmp = manifest_path.with_suffix('.tmp')
        progress_tmp.write_text(json.dumps(manifest, indent=2))
        progress_tmp.replace(manifest_path)
        su(f'mv {dst}/{n}.img.partial {dst}/{n}.img')
    if DRY:
        say('  [dry-run] would also pull aboot, boot, recovery, keystore, misc to this computer for the signing stage')
        return True
    (WORK / 'stock').mkdir(exist_ok=True)
    for n in ('aboot', 'boot', 'recovery', 'keystore', 'misc'):
        adb('pull', f'{dst}/{n}.img', str(WORK / 'stock' / f'{n}.img'))
        if hashlib.md5((WORK / 'stock' / f'{n}.img').read_bytes()).hexdigest() != manifest[n]['md5']:
            say(f'  copy of {n} on this computer does not match; stopping'); return False
    su(f'echo backup-complete > {dst}/COMPLETE')
    (WORK / 'stock' / 'manifest.json').write_text(json.dumps({'sd_folder': dst, 'partitions': manifest}, indent=2))
    STATE['backup_dir'] = dst; save_state()
    say(f'\nOriginal firmware saved on the card in {dst} and key images on this computer in {WORK / "stock"}.')
    say('Keep both. Take a copy of that card folder to your computer before reusing the card.')
    done('backup'); return True


def stage_sdtest():
    head('5. Try the microSD recovery function (do this BEFORE flashing anything)')
    say('This phone has a built-in rescue entry that starts from the microSD card: three marker files on the card make the')
    say('bootloader enter a USB download mode (USB id 0482:0a7f). If something goes wrong later, that is how the phone')
    say('can still be reached. Prove it works now, while nothing has been changed.')
    if not ensure_root():
        return False
    sd = sd_path()
    if not sd:
        return False
    if not confirm_write(f'create three 8-byte marker files NOTPUSH, CHKCODE, FASTBOOT (content DEVKEYDL) in the root of {sd}'):
        return False
    if DRY:
        say('  [dry-run] would test rescue mode and remove only markers created by this run')
        return True
    for f in ('NOTPUSH', 'CHKCODE', 'FASTBOOT'):
        if su(f'test -e {sd}/{f} && echo EXISTS', check=False) == 'EXISTS':
            raise RuntimeError(f'Existing rescue marker {f}; refusing to overwrite it')
    for f in ('NOTPUSH', 'CHKCODE', 'FASTBOOT'):
        su(f'printf DEVKEYDL > {sd}/{f}', write=True)
    say('\nNow, on the phone:')
    say('  1. Power the phone off, take the battery out, make sure the microSD is in.')
    say('  2. Put the battery back, press power, and connect the USB cable. The screen may stay dark.')
    say('  3. This script looks for USB id 0482:0a7f.')
    pause('Do steps 1-2 now, then press Enter')
    import usb.core
    found = False
    for _ in range(20):
        if usb.core.find(idVendor=0x0482, idProduct=0x0a7f) is not None:
            found = True; break
        time.sleep(2)
    say('  RESULT: ' + ('download mode detected (0482:0a7f)' if found else 'NOT detected'))
    say('\nTo go back to normal: unplug USB, take the battery AND the microSD out, put the battery back, power on')
    say('without the card, wait for Android, then put the card back in.')
    pause('Press Enter when the phone is running Android again with the card inserted')
    if wait_adb(seconds=120) and ensure_root():
        for f in ('NOTPUSH', 'CHKCODE', 'FASTBOOT'):
            su(f'rm -f {sd}/{f}', write=True)
        say('  marker files removed (leaving them would force download mode on every start)')
    else:
        say('  Remove NOTPUSH, CHKCODE and FASTBOOT from the card root yourself before the next restart!')
        return False
    if not found:
        say('The test did not show the rescue mode. You can still continue, but you would have no tested way back; think twice.')
        if ask('Continue anyway? (yes/no)', 'no').lower() != 'yes':
            return False
    done('sdtest'); return True


def stage_keys():
    head('6. Create your own signing key and the signed images (offline, on this computer)')
    need = [WORK / 'stock' / f'{n}.img' for n in ('aboot', 'boot', 'recovery', 'keystore')]
    if not all(p.exists() for p in need):
        say('The stock images from the backup stage are missing. Run stage 4 first.'); return False
    verify_payload()
    inputs = {p.name: sha_file(p) for p in need}
    inputs['twrp'] = sha_file(PAYLOAD / 'kyf37-twrp-candidate.img')
    out = WORK / 'images'; out.mkdir(exist_ok=True)
    cached = out / 'manifest.json'
    if cached.exists():
        report = json.loads(cached.read_text())
        if report.get('inputs') == inputs and (WORK / 'owner-signing-key.pem').is_file():
            if all((out / name).is_file() and sha_file(out / name) == entry['sha256']
                   for name, entry in report.items() if name.endswith('.img')):
                say('  signed images already verified; reusing them')
                done('keys')
                return True
        raise RuntimeError('Signing artifacts changed or key missing; preserve this workspace and investigate')
    key_path = WORK / 'owner-signing-key.pem'
    new_key = not key_path.exists()
    private = K.load_or_create_key(key_path)
    aboot, boot, recovery, keystore = (p.read_bytes() for p in need)
    _, _, _, oem_pub = K.stock_oem_keystore(aboot)
    K.verify_stock_boot(boot, oem_pub)
    say('  stock boot image verifies against the phone\'s own OEM key: yes')
    files = {
        'keystore-user.img': K.build_keystore(aboot, keystore, private),
        'boot-user-signed.img': K.sign_image(boot, boot, b'/boot', private),
        'recovery-stock-user-signed.img': K.sign_image(recovery, recovery, b'/recovery', private),
        'twrp-user-signed.img': K.sign_image((PAYLOAD / 'kyf37-twrp-candidate.img').read_bytes(), recovery, b'/recovery', private),
    }
    report = {'inputs': inputs}
    for name, data in files.items():
        (out / name).write_bytes(data)
        report[name] = {'bytes': len(data), 'sha256': K.sha256(data), 'md5': K.md5(data)}
    report['stock'] = {n: {'md5': K.md5(p.read_bytes())} for n, p in zip(('aboot', 'boot', 'recovery', 'keystore'), need)}
    (out / 'manifest.json').write_text(json.dumps(report, indent=2))
    say(f'  signed images written to {out}')
    if new_key:
        say(f'\n  A NEW PRIVATE KEY was created: {key_path}')
        say('  Back it up somewhere safe and NEVER share it. After the install your phone only boots images signed with it,')
        say('  so without this file you cannot update the ROM or recovery again.')
    done('keys'); return True


def push_script(name, text):
    p = WORK / name
    with open(p, 'w', newline='\n') as f:   # LF endings even on Windows: the phone's sh needs them
        f.write(text)
    adb('push', str(p), f'/data/local/tmp/{name}', write=True)


def partition_script(steps, originals, final_label):
    """Generated on-phone script: backs up originals, writes in order, verifies each write, restores on any failure."""
    lines = ['#!/system/bin/sh', 'set -eu', 'BB=/data/local/tmp/busybox', 'DIR=/data/local/tmp', 'BLOCK=/dev/block/bootdevice/by-name',
             '[ "$($BB id -u)" = 0 ]', '[ "$(getprop ro.product.model)" = KYF37 ]',
             'check() { a=$($BB md5sum "$1"); a=${a%% *}; [ "$a" = "$2" ] || { echo "Hash mismatch: $1 expected=$2 actual=$a"; return 1; }; }']
    for part, md5 in originals.items():
        lines.append(f'check "$BLOCK/{part}" {md5}')
    for _, src, md5 in steps:
        lines.append(f'check "$DIR/{src}" {md5}')
    for part in originals:
        lines.append(f'$BB dd if="$BLOCK/{part}" of="$DIR/rollback-{part}.img" bs=4096')
    lines.append('"$DIR/clear-recovery-boot-temp-wp" --clear-boot-recovery-temporary')
    lines += ['rollback() {', '  r=$?; trap - EXIT INT TERM',
              '  if [ "$r" != 0 ]; then set +e; echo "Install failed; restoring the previous partitions."']
    for part, md5 in originals.items():
        lines.append(f'    $BB dd if="$DIR/rollback-{part}.img" of="$BLOCK/{part}" bs=4096')
    lines += ['    sync', '  fi', '  exit "$r"', '}', 'trap rollback EXIT', "trap 'exit 130' INT TERM"]
    for part, src, md5 in steps:
        lines += [f'$BB dd if="$DIR/{src}" of="$BLOCK/{part}" bs=4096', 'sync', f'check "$BLOCK/{part}" {md5}']
    lines += [f'echo {final_label}', 'trap - EXIT INT TERM']
    return '\n'.join(lines) + '\n'


def stage_twrp():
    head('7. Install your signing key and the custom TWRP recovery')
    if not (WORK / 'images' / 'manifest.json').exists():
        say('Run stage 6 first.'); return False
    if not {'backup', 'sdtest', 'keys'} <= STATE.get('done', {}).keys():
        raise RuntimeError('Verified backup, rescue test and signing stages are required before partition writes')
    if not ensure_root():
        return False
    m = json.loads((WORK / 'images' / 'manifest.json').read_text())
    stock = m['stock']
    say('Phase A writes (in this order, each verified, automatic rollback on any failure): recovery -> boot -> keystore.')
    say('The keystore is written LAST, only after both images that depend on your key are verified on the phone.')
    say('Phase B writes the TWRP recovery. Both phases keep a copy of the previous partitions in /data/local/tmp.')
    if not confirm_write('write recovery, boot, keystore (phase A) and recovery again (phase B) on the phone'):
        return False
    imgs = WORK / 'images'
    for name in ('keystore-user.img', 'boot-user-signed.img', 'recovery-stock-user-signed.img', 'twrp-user-signed.img'):
        adb('push', str(imgs / name), f'/data/local/tmp/{name}', write=True)
    a = partition_script(
        [('recovery', 'recovery-stock-user-signed.img', m['recovery-stock-user-signed.img']['md5']),
         ('boot', 'boot-user-signed.img', m['boot-user-signed.img']['md5']),
         ('keystore', 'keystore-user.img', m['keystore-user.img']['md5'])],
        {'recovery': stock['recovery']['md5'], 'boot': stock['boot']['md5'], 'keystore': stock['keystore']['md5']},
        'USER_SIGNING_INSTALL_READBACK_VERIFIED')
    b = partition_script(
        [('recovery', 'twrp-user-signed.img', m['twrp-user-signed.img']['md5'])],
        {'recovery': m['recovery-stock-user-signed.img']['md5']}, 'TWRP_FLASH_READBACK_VERIFIED')
    push_script('kyf37-phase-a.sh', a); push_script('kyf37-phase-b.sh', b)
    if DRY:
        say(f'  [dry-run] generated phase scripts are in {WORK}'); return True
    current = {n: su(f'/data/local/tmp/busybox md5sum /dev/block/bootdevice/by-name/{n}').split()[0]
               for n in ('boot', 'recovery', 'keystore')}
    phase_a = {'boot': m['boot-user-signed.img']['md5'],
               'recovery': m['recovery-stock-user-signed.img']['md5'],
               'keystore': m['keystore-user.img']['md5']}
    phase_b = dict(phase_a, recovery=m['twrp-user-signed.img']['md5'])
    if current == phase_b:
        say('TWRP and signing partitions already verified; skipping both write phases')
        if not getprop('ro.twrp.version'):
            adb('reboot', 'recovery', write=True)
            if not wait_adb('recovery', 240):
                return False
        done('twrp')
        return True
    if current not in (phase_a, {n: stock[n]['md5'] for n in ('boot', 'recovery', 'keystore')}):
        raise RuntimeError('Unexpected or partially converted partition set; preserve backups and investigate before writing')
    if current == phase_a:
        out = 'USER_SIGNING_INSTALL_READBACK_VERIFIED'
        say('Phase A already verified; resuming at its boot check')
    else:
        out = su('sh /data/local/tmp/kyf37-phase-a.sh', timeout=300)
    say(out[-400:])
    if 'USER_SIGNING_INSTALL_READBACK_VERIFIED' not in out:
        say('Phase A did not verify. Rollback may have been attempted; inspect the output and partition hashes before proceeding.'); return False
    say('Phase A verified. Rebooting once to prove the phone boots with the new key before touching recovery...')
    adb('reboot', write=True); time.sleep(20)
    if not wait_adb(seconds=300):
        say('The phone did not come back. Use the microSD rescue mode from stage 5 and the backup on the card.'); return False
    if not ask('Did Android start normally? (yes/no)', 'yes').lower().startswith('y'):
        return False
    if not ensure_root():
        return False
    out = su('sh /data/local/tmp/kyf37-phase-b.sh', timeout=300)
    say(out[-300:])
    if 'TWRP_FLASH_READBACK_VERIFIED' not in out:
        say('Phase B did not verify. Check rollback output and recovery readback before proceeding.'); return False
    say('TWRP installed. Rebooting into recovery...')
    adb('reboot', 'recovery', write=True)
    if not wait_adb('recovery', 240):
        say('The phone did not reach recovery. Try power + volume/side key combination, or the microSD rescue mode.'); return False
    say('  TWRP version: ' + adb('shell', 'getprop ro.twrp.version', check=False))
    done('twrp'); return True


def stage_rom(args):
    head('8. Build your installer ZIP and flash the ROM')
    import kyf37_zip
    if args.rom:
        rom = Path(args.rom).expanduser()
    else:
        from kyf37_resources import release_rom, bundled_rom
        rom = None if args.rom_url else bundled_rom(HERE)
        if rom is None:
            say('Downloading the Android 11 ROM (verified downloads are cached)...')
            rom = release_rom(HERE / '.downloads', args.rom_url, args.rom_sha256)
        else:
            say(f'Using bundled ROM: {rom.name}')
    if not rom.exists():
        say('ROM ZIP not found.'); return False
    m = json.loads((WORK / 'images' / 'manifest.json').read_text())
    if not (WORK / 'owner-signing-key.pem').is_file():
        raise RuntimeError('Signing key missing; refusing to generate a replacement for an installed phone')
    private = K.load_or_create_key(WORK / 'owner-signing-key.pem')
    boot = (WORK / 'stock' / 'boot.img').read_bytes()
    out = WORK / f'kyf37-rom-for-{STATE["serial"]}.zip'
    if rom.resolve() == out.resolve():
        raise RuntimeError('Input ROM must differ from output ZIP')
    cache = out.with_suffix('.json')
    fingerprint = {'source': sha_file(rom), 'serial': STATE['serial'],
                   'images': sha_file(WORK / 'images' / 'manifest.json')}
    previous = json.loads(cache.read_text()) if cache.exists() else {}
    if out.is_file() and previous.get('inputs') == fingerprint and previous.get('sha256') == sha_file(out):
        say('  reusing verified per-phone ZIP')
    else:
        say('  rebuilding the ZIP for your phone and key (about 1.6 GB, takes a few minutes)...')
        temporary = out.with_suffix('.partial')
        kyf37_zip.build(rom, temporary, private, boot, STATE['serial'], m['twrp-user-signed.img']['sha256'], K.sha256((WORK / 'images' / 'keystore-user.img').read_bytes()), log=say)
        temporary.replace(out)
        temporary_cache = cache.with_suffix('.tmp')
        temporary_cache.write_text(json.dumps({'inputs': fingerprint, 'sha256': sha_file(out)}))
        temporary_cache.replace(cache)
    if not DRY:
        import zipfile
        with zipfile.ZipFile(out) as z:
            expected = json.loads(z.read('manifest.json'))['images']
        runner = shell if getprop('ro.twrp.version') else su
        current = {}
        for part in ('boot', 'system'):
            result = runner(f'sha256sum /dev/block/bootdevice/by-name/{part}', check=False, timeout=600).split()
            current[part] = result[0] if result else ''
        if current == {'boot': expected['boot.img'], 'system': expected['system.raw.img']}:
            say('  installed boot and system already match this ROM; skipping sideload')
            done('rom')
            return True
    say(f'  built {out}')
    say('\nIMPORTANT: this ROM installer keeps your user data. Going from Android 5.1 straight to Android 11 with old app data')
    say('is untested and may not boot. Preserve userdata and seek help if boot fails; do not wipe it.')
    if not confirm_write('write the Android 11 system and boot images with TWRP (the update-binary re-checks every hash first)'):
        return False
    if not DRY:
        state = adb('get-state', check=False)
        if adb('get-state', check=False).strip() != 'recovery' or not getprop('ro.twrp.version'):
            say('The phone must be in TWRP (stage 7 leaves it there). Reboot to recovery and run this stage again.'); return False
        say('In TWRP: Mount > tick "Micro SDcard" (the installer insists on the card being mounted).')
        pause('Press Enter once the card is mounted')
    log_bytes = 0
    if not DRY:
        log_bytes = int(shell('wc -c < /tmp/recovery.log'))
    adb('shell', 'twrp sideload', write=True)
    if not DRY:
        time.sleep(6)
    adb('sideload', str(out), write=True, timeout=3600)
    if DRY:
        return True
    time.sleep(8)
    log = shell(f'tail -c +{log_bytes + 1} /tmp/recovery.log', check=False)
    say(log)
    if 'readback verified' not in log or re.search(r'\b(ERROR|FAIL)\b', log):
        say('No "readback verified" line: do NOT reboot. Read /tmp/recovery.log on the phone and ask for help.'); return False
    adb('shell', 'dd if=/dev/zero of=/dev/block/bootdevice/by-name/misc bs=1 count=80 conv=notrunc; sync', write=True)
    adb('reboot', write=True)
    say('\nRebooting into Android 11. The first boot takes several minutes. If it does not start, boot to recovery')
    say('(power off, then the recovery key combination) and use the backup on the microSD.')
    say('Install readback verified; Android first-boot and hardware checks remain pending.')
    done('rom'); return True


def stage_apps():
    head('9. Install Pokédex and Flip Walker')
    import kyf37_apps

    def checkpoint(package, record):
        STATE.setdefault('apps', {})[package] = record
        save_state()

    ok = kyf37_apps.install(HERE / 'apps', dry=DRY, adb=adb, shell=shell,
                            getprop=getprop, say=say, confirm=confirm_write, checkpoint=checkpoint)
    if ok:
        done('apps')
    return ok


STAGES = [('check', 'Check the phone and this computer', stage_check), ('diag', 'Factory diagnostic USB mode', stage_diag),
          ('root', 'Root with su', stage_root), ('backup', 'Back up the original firmware to the microSD', stage_backup),
          ('sdtest', 'Try the microSD recovery function', stage_sdtest), ('keys', 'Create your signing key and signed images', stage_keys),
          ('twrp', 'Install your key + custom TWRP', stage_twrp), ('rom', 'Build your ZIP and flash the ROM', None),
          ('apps', 'Install Pokédex and Flip Walker', stage_apps)]


def main():
    global DRY, ADB, WORK, SERIAL
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--live', action='store_true', help='really write to the phone (default is a dry run)')
    ap.add_argument('--workspace', default=str(Path.home() / 'kyf37-installer-work'))
    ap.add_argument('--rom', help='path to a local ROM installer ZIP (otherwise download)')
    ap.add_argument('--rom-url', help='HTTPS ROM download URL')
    ap.add_argument('--rom-sha256', help='published SHA-256 for --rom-url')
    ap.add_argument('--serial', help='ADB serial (required if more than one device is connected)')
    ap.add_argument('--stage', choices=[s[0] for s in STAGES], help='run one stage by name and exit')
    args = ap.parse_args()
    DRY = not args.live
    ADB = find_adb()
    head('KYF37 installer  -  ' + ('DRY RUN (nothing is written)' if DRY else 'LIVE: the phone WILL be changed'))
    say('Read README.md first. This has not been run end to end on a stock phone. Everything you may lose is yours to back up.')
    devices = [line.split()[0] for line in adb('devices').splitlines()[1:]
               if len(line.split()) == 2 and line.split()[1] in ('device', 'recovery')]
    if args.serial:
        if args.serial not in devices:
            raise SystemExit('Selected device is not connected or authorized')
        SERIAL = args.serial
    elif len(devices) == 1:
        SERIAL = devices[0]
    else:
        raise SystemExit('Connect one authorized phone or select it with --serial')
    root = Path(args.workspace); root.mkdir(parents=True, exist_ok=True)
    serial = SERIAL
    if not re.fullmatch(r'[A-Za-z0-9]{6,32}', serial):
        raise SystemExit('Unsupported device serial; refusing unsafe workspace path')
    WORK = root / serial; WORK.mkdir(exist_ok=True)
    lock_workspace()
    STATE.update(json.loads((WORK / 'state.json').read_text()) if (WORK / 'state.json').exists() else {})
    if STATE.get('serial', serial) != serial:
        raise SystemExit('Workspace belongs to another phone')
    if STATE.get('schema') != 2:
        # Older versions persisted dry-run completion as real completion.
        STATE.pop('done', None)
    STATE['serial'] = serial
    funcs = {k: (f if f else (lambda a=args: stage_rom(a))) for k, _, f in STAGES}
    if args.stage:
        return 0 if funcs[args.stage]() else 1
    while True:
        head('Stages')
        for i, (k, label, _) in enumerate(STAGES, 1):
            mark = 'done ' + STATE.get('done', {}).get(k, '') if k in STATE.get('done', {}) else ''
            say(f'  {i}. {label:50s} {mark}')
        c = ask('Number to run, "a" for all remaining in order, "q" to quit', 'a')
        if c.lower() == 'q':
            return
        try:
            todo = [s for s in STAGES if s[0] == 'apps' or s[0] not in STATE.get('done', {})] if c.lower() == 'a' else [STAGES[int(c) - 1]] if c.isdigit() and 1 <= int(c) <= len(STAGES) else []
        except (ValueError, IndexError):
            say('Please type a stage number, "a" or "q".'); continue
        for k, _, _ in todo:
            try:
                ok = funcs[k]() if k != 'rom' else stage_rom(args)
            except KeyboardInterrupt:
                say('\ninterrupted'); return
            except Exception as e:
                say(f'\nERROR in stage {k}: {e}'); ok = False
            if not ok:
                say(f'Stage {k} did not complete. Fix the problem above, then run it again.'); break


if __name__ == '__main__':
    sys.exit(main())

# Installer resume patch v2

# Installer safety guards v1

# Bundled installer release layout v1

# Bundled apps stage v1
