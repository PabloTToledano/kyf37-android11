#!/usr/bin/env bash
# Incremental compile check only; does not package, sign, install or reboot.
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
python3 "$PROJECT/device-inspection/fix-android11-walker-uart.py"
python3 "$PROJECT/flip_walker/tests/test-kernel-uart.py"
export PATH=/home/pablo/kyf37-host-tools/python2/bin:$PATH
make -C "$PROJECT/native/kyf37-android11/kernel/kyocera/kyf37" \
  O=/home/pablo/kyf37-android11-kernel-build ARCH=arm \
  CROSS_COMPILE=/home/pablo/kyf37-lineage/prebuilts/gcc/linux-x86/arm/arm-eabi-4.8/bin/arm-eabi- \
  HOSTCC="gcc -std=gnu99 -fcommon" -j2 drivers/felica/kfelica.o
