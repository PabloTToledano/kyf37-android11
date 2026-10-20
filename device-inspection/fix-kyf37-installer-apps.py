#!/usr/bin/env python3
"""Stage public APKs and rerunnable installer/packager changes; no phone or key access."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'kyf37-installer'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b''): h.update(chunk)
    return h.hexdigest()

# Only these two public distribution APKs may be staged. No workspace traversal.
apps = []
for directory, filename, package, name in (
    ('flip_pokedex', 'FlipPokedex', 'org.kyf37.pokedex', 'Flip Pokédex'),
    ('flip_walker', 'FlipWalker', 'org.kyf37.walker', 'Flip Walker'),
):
    source = ROOT / directory / 'dist' / (filename + '.apk')
    expected = source.with_suffix('.apk.sha256').read_text().split()[0]
    if digest(source) != expected: raise RuntimeError('APK checksum mismatch: ' + filename)
    info = source.with_suffix('.apk-info.txt').read_text()
    match = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", info)
    sdk = re.search(r"sdkVersion:'(\d+)'", info)
    if not match or not sdk or match[1] != package: raise RuntimeError('APK metadata mismatch: ' + filename)
    destination = SOURCE / 'apps' / source.name
    destination.parent.mkdir(exist_ok=True)
    if not destination.exists() or digest(destination) != expected:
        shutil.copyfile(source, destination)
    apps.append({'name': name, 'package': package, 'file': source.name,
                 'versionCode': int(match[2]), 'versionName': match[3], 'minSdk': int(sdk[1]),
                 'bytes': source.stat().st_size, 'sha256': expected})
(SOURCE / 'apps/apps.json').write_text(json.dumps({'format': 1, 'apps': apps}, indent=2, ensure_ascii=False) + '\n')

(SOURCE / 'kyf37_apps.py').write_text('"""Install the bundled Pokédex and Walker APKs after Android boots.\n\nUses ordinary ADB package installation. No root, data clearing, app launch,\npermission grants, partition writes, bootloader operations or hardware actions.\n"""\nimport json\nfrom pathlib import Path\nimport re\nimport shlex\nimport subprocess\nimport time\n\nfrom kyf37_resources import sha256\n\nPACKAGES = {\'org.kyf37.pokedex\', \'org.kyf37.walker\'}\n\n\ndef load_apps(directory):\n    directory = Path(directory).resolve()\n    manifest = json.loads((directory / \'apps.json\').read_text())\n    apps = manifest[\'apps\']\n    if len(apps) != 2 or {a[\'package\'] for a in apps} != PACKAGES:\n        raise ValueError(\'Expected exactly the bundled Pokédex and Flip Walker apps\')\n    result = []\n    for app in apps:\n        path = directory / app[\'file\']\n        digest = app[\'sha256\']\n        if not re.fullmatch(r\'[0-9a-f]{64}\', digest):\n            raise ValueError(\'Invalid app checksum\')\n        if not path.resolve().is_relative_to(directory) or path.is_symlink() or not path.is_file():\n            raise ValueError(\'Missing or unsafe bundled APK: \' + app[\'package\'])\n        if app[\'versionCode\'] < 1 or app[\'minSdk\'] < 1:\n            raise ValueError(\'Invalid app version metadata\')\n        if path.stat().st_size != app[\'bytes\'] or sha256(path) != digest:\n            raise ValueError(\'Bundled APK checksum mismatch: \' + app[\'package\'])\n        result.append((app, path))\n    return result\n\n\ndef wait_for_android(adb, getprop, say, timeout=600):\n    deadline = time.monotonic() + timeout\n    say(\'Waiting for Android to finish booting (up to 10 minutes)...\')\n    while time.monotonic() < deadline:\n        try:\n            if adb(\'get-state\', check=False, timeout=15).strip() == \'device\' and getprop(\'sys.boot_completed\') == \'1\':\n                return True\n        except (RuntimeError, TimeoutError, subprocess.TimeoutExpired):\n            pass  # USB can disconnect briefly during the first boot.\n        time.sleep(3)\n    say(\'Android did not finish booting. App installation remains pending; resume with --stage apps after boot.\')\n    return False\n\n\ndef installed_version(shell, package):\n    output = shell(f\'dumpsys package {package}\', check=False)\n    match = re.search(r\'\\bversionCode=(\\d+)\\b\', output)\n    if match:\n        return int(match.group(1))\n    # A transport/package-manager error must not be mistaken for an absent app.\n    if shell(f\'pm path {package}\', check=False).strip().startswith(\'package:\'):\n        raise RuntimeError(\'Cannot determine installed version of \' + package)\n    return None\n\n\ndef installed_hash(shell, package):\n    output = shell(f\'pm path {package}\')\n    paths = [line.removeprefix(\'package:\') for line in output.splitlines() if line.startswith(\'package:\')]\n    if len(paths) != 1 or not paths[0].startswith(\'/\') or \'\\n\' in paths[0]:\n        return None\n    output = shell(\'sha256sum \' + shlex.quote(paths[0]), check=False, timeout=120)\n    words = output.split()\n    return words[0] if words and re.fullmatch(r\'[0-9a-f]{64}\', words[0]) else None\n\n\ndef install(directory, *, dry, adb, shell, getprop, say, confirm, checkpoint):\n    # Validate both local APKs before considering any phone mutation.\n    apps = load_apps(directory)\n    if dry:\n        say(\'[dry-run] After Android finishes booting, verify/install:\')\n        for app, _ in apps:\n            say(f"  {app[\'name\']} {app[\'versionName\']} (preserve data; skip matching/newer installs)")\n        return True\n    if not wait_for_android(adb, getprop, say):\n        return False\n    if getprop(\'ro.product.model\') != \'KYF37\':\n        raise RuntimeError(\'App installer is only for KYF37\')\n    sdk = getprop(\'ro.build.version.sdk\')\n    if not sdk.isdigit() or int(sdk) < max(app[\'minSdk\'] for app, _ in apps):\n        raise RuntimeError(\'Android version is too old for the bundled apps; install the custom ROM first\')\n    abis = getprop(\'ro.product.cpu.abilist\').split(\',\')\n    if \'armeabi-v7a\' not in abis:\n        raise RuntimeError(\'Expected an ARMv7-compatible Android system\')\n    approved = False\n    for app, path in apps:\n        package = app[\'package\']\n        version = installed_version(shell, package)\n        if version is not None and version > app[\'versionCode\']:\n            say(f"  {app[\'name\']}: newer version {version} already installed; keeping it")\n            checkpoint(package, {\'versionCode\': version, \'status\': \'kept-newer\'})\n            continue\n        if version == app[\'versionCode\'] and installed_hash(shell, package) == app[\'sha256\']:\n            say(f"  {app[\'name\']}: exact APK already installed; skipping")\n            checkpoint(package, {\'versionCode\': version, \'sha256\': app[\'sha256\'], \'status\': \'verified\'})\n            continue\n        if not approved:\n            if not confirm(\'install/update bundled Pokédex and Flip Walker apps while retaining their existing data\'):\n                return False\n            approved = True\n        say(f"  Installing {app[\'name\']} {app[\'versionName\']}...")\n        # No -d, uninstall, pm clear, root, launch or automatic permission grants.\n        output = adb(\'install\', \'-r\', str(path), write=True, timeout=600)\n        if not re.search(r\'^Success\\s*$\', output, re.M):\n            raise RuntimeError(f"Installation of {app[\'name\']} did not report success: {output}")\n        if installed_version(shell, package) != app[\'versionCode\'] or installed_hash(shell, package) != app[\'sha256\']:\n            raise RuntimeError(\'Installed APK verification failed: \' + package)\n        checkpoint(package, {\'versionCode\': app[\'versionCode\'], \'sha256\': app[\'sha256\'], \'status\': \'verified\'})\n        say(\'  Installed APK verified\')\n    say(\'Pokédex and Flip Walker are installed. Open them from the launcher when ready.\')\n    return True\n')

p = SOURCE / 'kyf37_installer.py'
s = p.read_text()
marker = '# Bundled apps stage v1'
if marker not in s:
    insertion = '''def stage_apps():
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


'''
    s = s.replace("STAGES = [('check',", insertion + "STAGES = [('check',", 1)
    old = "('rom', 'Build your ZIP and flash the ROM', None)]"
    new = "('rom', 'Build your ZIP and flash the ROM', None),\n          ('apps', 'Install Pokédex and Flip Walker', stage_apps)]"
    if old not in s: raise RuntimeError('Stage table changed')
    s = s.replace(old, new)
    # Recheck app contents even if a previous release already completed this stage.
    s = s.replace("if s[0] not in STATE.get('done', {})]", "if s[0] == 'apps' or s[0] not in STATE.get('done', {})]")
    p.write_text(s + '\n' + marker + '\n')

p = ROOT / 'device-inspection/package-stock-installer.py'
s = p.read_text()
marker = '# Bundled app packaging v1'
if marker not in s:
    s = s.replace("'kyf37_crypto.py', 'kyf37_diag.py',", "'kyf37_crypto.py', 'kyf37_apps.py', 'kyf37_diag.py',")
    s = s.replace("ROOT / 'releases/kyf37-stock-installer-20261019-experimental'", "ROOT / 'releases/kyf37-stock-installer-20261019-apps-experimental'")
    old = "        copy_public(SOURCE / 'README.md', stage / 'docs/INSTALLER.md')"
    new = '''        from kyf37_apps import load_apps
        applications = load_apps(SOURCE / 'apps')
        copy_public(SOURCE / 'apps/apps.json', stage / 'apps/apps.json')
        for app, path in applications:
            copy_public(path, stage / 'apps' / app['file'])
        for directory, name in (('flip_pokedex', 'POKEDEX'), ('flip_walker', 'WALKER')):
            copy_public(ROOT / directory / 'README.md', stage / 'docs/apps' / (name + '.md'))
            copy_public(ROOT / directory / 'THIRD_PARTY.md', stage / 'docs/apps' / (name + '-THIRD-PARTY.md'))
        copy_public(SOURCE / 'README.md', stage / 'docs/INSTALLER.md')'''
    if old not in s: raise RuntimeError('Packaging source changed')
    s = s.replace(old, new)
    s = s.replace("'stock_to_custom_verified': False,", "'apps': [a for a, _ in applications],\n                    'stock_to_custom_verified': False,")
    s = s.replace('The installer selects the included ROM automatically.', 'The installer selects the included ROM automatically.\nFlip Pokédex and Flip Walker APKs are also included and installed as the final stage after Android boots.')
    s = s.replace('   `.\\\\install.cmd --live` when ready. Every write stage asks for typed confirmation.', '   `.\\\\install.cmd --live` when ready. Every write stage asks for typed confirmation.\n6. Keep USB connected through the first Android boot. Stage 9 waits for boot completion and installs both apps.\n   To resume only app installation: `./install.sh --live --stage apps` or `.\\\\install.cmd --live --stage apps`.\n   Matching APKs are skipped, newer versions retained and existing app data preserved. Apps are not launched automatically.')
    s = s.replace('- `rom/`: matching Android 11 Go boot/system installer template; personalized before sideload.', '- `rom/`: matching Android 11 Go boot/system installer template; personalized before sideload.\n- `apps/`: Flip Pokédex and Flip Walker APKs plus package/version/checksum metadata.\n- `docs/apps/`: app usage and third-party notices. The Pokédex includes offline artwork/classifier assets;\n  Flip Walker IR features require compatible ROM support and user-approved permissions/root access.')
    p.write_text(s + '\n' + marker + '\n')

p = SOURCE / 'README.md'
s = p.read_text().replace('eight stages:', 'nine stages:')
if '| 9 | Apps |' not in s:
    s = s.replace('| 8 | ROM | rebuilds the ROM ZIP for *your* phone and key, sideloads it in TWRP | yes |', '| 8 | ROM | rebuilds the ROM ZIP for *your* phone and key, sideloads it in TWRP | yes |\n| 9 | Apps | waits for Android boot, verifies/installs bundled Pokédex and Flip Walker APKs | yes (ordinary app updates; existing data retained) |')
if '## Pokédex and Flip Walker installation' not in s:
    s += '''
## Pokédex and Flip Walker installation

The release includes both apps in `apps/`. Stage 9 follows ROM installation and waits up to ten minutes for
Android to finish booting. It verifies the bundled APK checksums and device compatibility before installation.
Matching installed APKs are skipped, newer versions are kept, and older/mismatched APKs receive an ordinary
`adb install -r` update. Existing app data is retained; a signature conflict stops without uninstalling the app.
Installed version and APK hash must match before each app is checkpointed. A rerun rechecks both apps even if
the stage previously completed. The installer does not launch apps, grant permissions, format storage or start IR.

After an interrupted first boot, resume only this stage with `./install.sh --live --stage apps` on Linux or
`.\\install.cmd --live --stage apps` on Windows. A dry run only describes the app stage and does not wait or install.
The APKs support ARMv7: Pokédex needs API 23+, Flip Walker API 26+. Both work with the bundled Android 11 ROM.
On first use, grant the permissions you choose in Android; Walker's IR functions require compatible ROM
support and user-approved root/companion access. The installer does not change native authentication or dialer.
'''
p.write_text(s)

# Version the app-inclusive distribution separately from the earlier release.
p = ROOT / 'device-inspection/package-stock-installer.py'
s = p.read_text().replace('20261019-apps-experimental', '20261020-apps-experimental')
anchor = "        copy_public(SOURCE / 'README.md', stage / 'docs/INSTALLER.md')"
license_line = "        copy_public(ROOT / 'flip_walker/LICENSE', stage / 'docs/apps/WALKER-LICENSE.txt')"
if license_line not in s:
    if anchor not in s: raise RuntimeError('Package documentation source changed')
    s = s.replace(anchor, license_line + '\n' + anchor)
p.write_text(s)

# Do not silently reuse a prior release after the selected app payloads change.
p = ROOT / 'device-inspection/package-stock-installer.py'
s = p.read_text()
anchor = "        print('Existing release verified; preserved:', destination)"
guard = """        from kyf37_apps import load_apps
        selected_apps = [a for a, _ in load_apps(SOURCE / 'apps')]
        if metadata.get('apps') != selected_apps:
            raise ValueError('Existing release uses other app APKs; choose a new destination')
"""
if 'selected_apps =' not in s:
    if anchor not in s: raise RuntimeError('Release reuse check changed')
    s = s.replace(anchor, guard + anchor)
p.write_text(s)
