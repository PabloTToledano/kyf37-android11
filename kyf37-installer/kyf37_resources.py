"""Download public tools and release assets; never handles signing keys."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import tempfile
import urllib.request
import zipfile

RELEASE_API = 'https://api.github.com/repos/PabloTToledano/kyf37-customizer/releases/tags/v2026.10.20-experimental'


def download(url, destination, expected=None):
    if not url.startswith('https://'):
        raise ValueError('Downloads require HTTPS')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if expected and destination.is_file() and sha256(destination) == expected:
        return destination
    temporary = destination.with_name(destination.name + '.download')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'kyf37-installer'})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as out:
            if not response.url.startswith('https://'):
                raise ValueError('Insecure download redirect')
            shutil.copyfileobj(response, out, 8 << 20)
        if expected and sha256(temporary) != expected:
            raise ValueError('Downloaded file failed SHA-256 verification')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def platform_tools(directory, system=None):
    system = system or platform.system()
    if system not in ('Linux', 'Windows'):
        raise RuntimeError('Automatic platform-tools download supports Linux and Windows')
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Automatic platform-tools requires x86-64; supply a compatible ADB on PATH')
    directory = Path(directory)
    target = directory / 'platform-tools'
    executable = target / ('adb.exe' if system == 'Windows' else 'adb')
    if executable.is_file():
        return str(executable)
    archive = download('https://dl.google.com/android/repository/platform-tools-latest-' +
                       ('windows' if system == 'Windows' else 'linux') + '.zip', directory / 'platform-tools.zip')
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                path = stage / info.filename
                if not path.resolve().is_relative_to(stage.resolve()):
                    raise ValueError('Unsafe platform-tools archive path')
                z.extract(info, stage)
        staged = stage / 'platform-tools'
        adb = staged / executable.name
        if not adb.is_file():
            raise ValueError('Downloaded platform-tools has no adb')
        if system == 'Linux':
            for name in ('adb', 'fastboot'):
                file = staged / name
                if file.exists():
                    file.chmod(file.stat().st_mode | stat.S_IXUSR)
        # Only a complete extracted directory becomes available to later runs.
        if target.exists():
            raise RuntimeError('Incomplete platform-tools directory; preserve or move it before retrying')
        staged.replace(target)
    return str(executable)


def release_rom(directory, url=None, digest=None):
    if url:
        if not digest or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('--rom-url requires --rom-sha256 with the published SHA-256 digest')
        return download(url, Path(directory) / ('rom-' + digest + '.zip'), digest)
    request = urllib.request.Request(RELEASE_API, headers={'User-Agent': 'kyf37-installer'})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.load(response)
    candidates = [a for a in release.get('assets', [])
                  if a['name'].endswith('.zip') and 'twrp' in a['name'] and 'android11' in a['name']]
    if len(candidates) != 1:
        raise RuntimeError('Latest release has no unique Android 11 TWRP ROM. Use --rom FILE or --rom-url URL --rom-sha256 HASH; no other Android version will be substituted.')
    asset = candidates[0]
    digest = asset.get('digest', '')
    if not digest or not digest.startswith('sha256:'):
        raise RuntimeError('Release asset lacks a SHA-256 digest; supply --rom-url and --rom-sha256')
    return release_rom(directory, asset['browser_download_url'], digest.split(':', 1)[1])


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
