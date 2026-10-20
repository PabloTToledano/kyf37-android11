#!/usr/bin/env bash
# Invoked under build-locked.sh. Stages only; never flashes a device.
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
bash "$PROJECT/flip_walker/tools/build-both.sh"
python3 "$PROJECT/device-inspection/fix-android11-walker-uart.py"
python3 "$PROJECT/device-inspection/stage-android11-flip-walker.py"
