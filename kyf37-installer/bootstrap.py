#!/usr/bin/env python3
"""Repair or create a local Python environment, then run the installer."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kyf37_resources import download


def main():
    if sys.version_info < (3, 9):
        raise SystemExit('Python 3.9 or newer is required')
    environment = HERE / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        result = subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(environment)])
        if result.returncode:
            virtualenv = download('https://bootstrap.pypa.io/virtualenv.pyz', HERE / '.downloads/virtualenv.pyz')
            subprocess.run([sys.executable, str(virtualenv), str(environment)], check=True)
    if subprocess.run([str(python), '-m', 'pip', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        getpip = download('https://bootstrap.pypa.io/get-pip.py', HERE / '.downloads/get-pip.py')
        subprocess.run([str(python), str(getpip)], check=True)
    requirements = HERE / 'requirements.txt'
    fingerprint = hashlib.sha256(requirements.read_bytes() + sys.version.encode()).hexdigest()
    stamp = environment / 'requirements.sha256'
    ready = subprocess.run([str(python), '-c', 'import cryptography, usb, libusb_package'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not ready or not stamp.exists() or stamp.read_text() != fingerprint:
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(requirements)], check=True)
        stamp.write_text(fingerprint)
    return subprocess.call([str(python), str(HERE / 'kyf37_installer.py'), *sys.argv[1:]])


if __name__ == '__main__':
    sys.exit(main())
