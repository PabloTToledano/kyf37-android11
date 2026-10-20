#!/usr/bin/env bash
# Build and stage a matching kernel/module set; no phone access or flashing.
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
bash "$PROJECT/flip_walker/tools/build-kernel-ir.sh"
export PATH=/home/pablo/kyf37-host-tools/python2/bin:$PATH
kernel="$PROJECT/native/kyf37-android11/kernel/kyocera/kyf37"
output=/home/pablo/kyf37-android11-kernel-build
cross=/home/pablo/kyf37-lineage/prebuilts/gcc/linux-x86/arm/arm-eabi-4.8/bin/arm-eabi-
external="$PROJECT/native/kyf37-android11/kernel/kyocera/kyf37-external"
make -C "$kernel" O="$output" ARCH=arm CROSS_COMPILE="$cross" HOSTCC="gcc -std=gnu99 -fcommon" -j4 zImage modules
make -C "$kernel" O="$output" M="$external/wlan" ARCH=arm CROSS_COMPILE="$cross" HOSTCC="gcc -std=gnu99 -fcommon" MODNAME=wlan WLAN_ROOT="$external/wlan" CONFIG_PRONTO_WLAN=m BOARD_PLATFORM=msm8909 -j2 modules
make -C "$kernel" O="$output" M="$external/core_ctl" ARCH=arm CROSS_COMPILE="$cross" HOSTCC="gcc -std=gnu99 -fcommon" -j2 modules
mkdir -p "$output/staged-modules"
"${cross}strip" --strip-debug -o "$output/staged-modules/pronto_wlan.ko" "$external/wlan/wlan.ko"
"${cross}strip" --strip-debug -o "$output/staged-modules/core_ctl.ko" "$external/core_ctl/core_ctl.ko"
python3 "$PROJECT/device-inspection/verify-android11-kernel.py"
