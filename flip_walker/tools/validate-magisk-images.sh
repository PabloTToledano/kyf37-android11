#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || exit 1
P=$(cd "$(dirname "$0")/../.." && pwd)
O="$P/kyf37-rom/android11-${1:-walker-ir-v3}"
python3 "$P/device-inspection/validate-android11-images.py" \
  --boot "$O/boot-magisk-owner-signed.img" --raw-output "$O/system-magisk.raw.img" \
  --report-dir "$O/magisk-audit" --vendor-audit "$O/vendor-audit.json" \
  --magisk-apk "$P/flip_walker/cache/magisk-v30.7/Magisk-v30.7.apk" \
  --magisk-base-boot "$O/boot-unsigned.img"
echo MAGISK_VALIDATE_OK
