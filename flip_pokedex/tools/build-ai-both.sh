#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Run through build-locked.sh'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
bash "$ROOT/tools/build.sh" --emulator
python3 "$ROOT/tools/verify_apk.py" "$ROOT/dist/FlipPokedex-emulator.apk"
bash "$ROOT/tools/build.sh"
python3 "$ROOT/tools/verify_apk.py" "$ROOT/dist/FlipPokedex.apk"
python3 "$ROOT/tools/ml/write_model_card.py"
