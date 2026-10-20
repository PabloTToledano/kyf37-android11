#!/usr/bin/env bash
# Runs only while the PowerShell phone lock is owned by flip-walker-ir.
# Uses fixed app-owned paths. No reboot, partition writes, resets or SIM input.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT=$(cd "$ROOT/.." && pwd)
python3 - "$PROJECT/.phone.lock" <<'PY'
import json,sys,datetime
p=json.load(open(sys.argv[1]))
assert p['owner']=='flip-walker-ir','Phone lock belongs to someone else'
assert datetime.datetime.fromisoformat(p['expires'])>datetime.datetime.now(datetime.timezone.utc),'Phone lock expired'
PY
SERIAL=YOUR_ADB_SERIAL
ADB="$PROJECT/flip_pokedex/cache/android-sdk/platform-tools/adb"
"$ADB" -s "$SERIAL" shell id
"$ADB" -s "$SERIAL" shell getprop sys.boot_completed
"$ADB" -s "$SERIAL" shell /data/local/tmp/flipwalker-ir --self-test
"$ADB" -s "$SERIAL" shell /data/local/tmp/flipwalker-ir --probe
