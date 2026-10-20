#!/usr/bin/env bash
# Optional future ROM source integration. Never deploys or accesses a device.
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/tools/prepare_rom_key_patch.py" --apply "$@"
