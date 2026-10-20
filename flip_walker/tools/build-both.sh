#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/tools/modern-ds/generate.py"
python3 "$ROOT/tools/modern-ds/extend-reader.py"
python3 "$ROOT/tools/modern-ds/integrate.py"
python3 "$ROOT/tools/modern-ds/info-panel.py"
python3 "$ROOT/tools/modern-ds/editor-hints.py"
python3 "$ROOT/tools/modern-ds/color-cards.py"
python3 "$ROOT/tools/localization/generate.py"
python3 "$ROOT/tools/localization/integrate.py"
python3 "$ROOT/tools/modern-ds/generate.py"
python3 "$ROOT/tools/bottom-bar/integrate.py"
bash "$ROOT/tools/test-host.sh"
bash "$ROOT/tools/build.sh"
bash "$ROOT/tools/build.sh" --emulator
python3 "$ROOT/tools/collect-notices.py"
