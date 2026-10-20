#!/usr/bin/env bash
# Linux launcher: keep downloads and dependencies local to the installer.
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  if [[ ! -x .python/python/bin/python3 ]]; then
    echo 'Downloading a private Python runtime...'
    mkdir -p .downloads .python
    fetch() {
      if command -v curl >/dev/null; then curl --fail --location --proto '=https' --tlsv1.2 "$1" -o "$2";
      elif command -v wget >/dev/null; then wget --https-only "$1" -O "$2";
      else echo 'Install curl or wget to download Python.' >&2; return 1; fi
    }
    case "$(uname -m)" in
      x86_64) arch=x86_64;;
      aarch64) arch=aarch64;;
      *) echo 'Unsupported CPU; install Python 3.9+ manually.' >&2; exit 1;;
    esac
    fetch https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest .downloads/python-release.json
    url=$(sed -n 's/.*"browser_download_url": "\([^"]*\)".*/\1/p' .downloads/python-release.json | sed -n "/cpython-3\.12\..*${arch}-unknown-linux-gnu-install_only\.tar\.gz$/p" | head -n 1)
    [[ -n "$url" ]] || { echo 'No compatible Python download; install Python 3.9+ manually.' >&2; exit 1; }
    fetch "$url" .downloads/python.tar.gz.partial
    tar -xzf .downloads/python.tar.gz.partial -C .python
  fi
  exec .python/python/bin/python3 bootstrap.py "$@"
fi
exec python3 bootstrap.py "$@"
