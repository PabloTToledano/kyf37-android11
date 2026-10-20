"""Install the bundled Pokédex and Walker APKs after Android boots.

Uses ordinary ADB package installation. No root, data clearing, app launch,
permission grants, partition writes, bootloader operations or hardware actions.
"""
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

from kyf37_resources import sha256

PACKAGES = {'org.kyf37.pokedex', 'org.kyf37.walker'}


def load_apps(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'apps.json').read_text())
    apps = manifest['apps']
    if len(apps) != 2 or {a['package'] for a in apps} != PACKAGES:
        raise ValueError('Expected exactly the bundled Pokédex and Flip Walker apps')
    result = []
    for app in apps:
        path = directory / app['file']
        digest = app['sha256']
        if not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Invalid app checksum')
        if not path.resolve().is_relative_to(directory) or path.is_symlink() or not path.is_file():
            raise ValueError('Missing or unsafe bundled APK: ' + app['package'])
        if app['versionCode'] < 1 or app['minSdk'] < 1:
            raise ValueError('Invalid app version metadata')
        if path.stat().st_size != app['bytes'] or sha256(path) != digest:
            raise ValueError('Bundled APK checksum mismatch: ' + app['package'])
        result.append((app, path))
    return result


def wait_for_android(adb, getprop, say, timeout=600):
    deadline = time.monotonic() + timeout
    say('Waiting for Android to finish booting (up to 10 minutes)...')
    while time.monotonic() < deadline:
        try:
            if adb('get-state', check=False, timeout=15).strip() == 'device' and getprop('sys.boot_completed') == '1':
                return True
        except (RuntimeError, TimeoutError, subprocess.TimeoutExpired):
            pass  # USB can disconnect briefly during the first boot.
        time.sleep(3)
    say('Android did not finish booting. App installation remains pending; resume with --stage apps after boot.')
    return False


def installed_version(shell, package):
    output = shell(f'dumpsys package {package}', check=False)
    match = re.search(r'\bversionCode=(\d+)\b', output)
    if match:
        return int(match.group(1))
    # A transport/package-manager error must not be mistaken for an absent app.
    if shell(f'pm path {package}', check=False).strip().startswith('package:'):
        raise RuntimeError('Cannot determine installed version of ' + package)
    return None


def installed_hash(shell, package):
    output = shell(f'pm path {package}')
    paths = [line.removeprefix('package:') for line in output.splitlines() if line.startswith('package:')]
    if len(paths) != 1 or not paths[0].startswith('/') or '\n' in paths[0]:
        return None
    output = shell('sha256sum ' + shlex.quote(paths[0]), check=False, timeout=120)
    words = output.split()
    return words[0] if words and re.fullmatch(r'[0-9a-f]{64}', words[0]) else None


def install(directory, *, dry, adb, shell, getprop, say, confirm, checkpoint):
    # Validate both local APKs before considering any phone mutation.
    apps = load_apps(directory)
    if dry:
        say('[dry-run] After Android finishes booting, verify/install:')
        for app, _ in apps:
            say(f"  {app['name']} {app['versionName']} (preserve data; skip matching/newer installs)")
        return True
    if not wait_for_android(adb, getprop, say):
        return False
    if getprop('ro.product.model') != 'KYF37':
        raise RuntimeError('App installer is only for KYF37')
    sdk = getprop('ro.build.version.sdk')
    if not sdk.isdigit() or int(sdk) < max(app['minSdk'] for app, _ in apps):
        raise RuntimeError('Android version is too old for the bundled apps; install the custom ROM first')
    abis = getprop('ro.product.cpu.abilist').split(',')
    if 'armeabi-v7a' not in abis:
        raise RuntimeError('Expected an ARMv7-compatible Android system')
    approved = False
    for app, path in apps:
        package = app['package']
        version = installed_version(shell, package)
        if version is not None and version > app['versionCode']:
            say(f"  {app['name']}: newer version {version} already installed; keeping it")
            checkpoint(package, {'versionCode': version, 'status': 'kept-newer'})
            continue
        if version == app['versionCode'] and installed_hash(shell, package) == app['sha256']:
            say(f"  {app['name']}: exact APK already installed; skipping")
            checkpoint(package, {'versionCode': version, 'sha256': app['sha256'], 'status': 'verified'})
            continue
        if not approved:
            if not confirm('install/update bundled Pokédex and Flip Walker apps while retaining their existing data'):
                return False
            approved = True
        say(f"  Installing {app['name']} {app['versionName']}...")
        # No -d, uninstall, pm clear, root, launch or automatic permission grants.
        output = adb('install', '-r', str(path), write=True, timeout=600)
        if not re.search(r'^Success\s*$', output, re.M):
            raise RuntimeError(f"Installation of {app['name']} did not report success: {output}")
        if installed_version(shell, package) != app['versionCode'] or installed_hash(shell, package) != app['sha256']:
            raise RuntimeError('Installed APK verification failed: ' + package)
        checkpoint(package, {'versionCode': app['versionCode'], 'sha256': app['sha256'], 'status': 'verified'})
        say('  Installed APK verified')
    say('Pokédex and Flip Walker are installed. Open them from the launcher when ready.')
    return True
