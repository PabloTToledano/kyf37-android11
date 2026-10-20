#!/usr/bin/env bash
# Official patch must have run on the locked physical phone first. No flash here.
set -euo pipefail
P=$(cd "$(dirname "$0")/../.." && pwd)
NAME=${1:-walker-ir-v3}
O="$P/kyf37-rom/android11-$NAME"
"$P/native/host-runtime/signing-venv/bin/python" "$P/device-inspection/sign-rom-boot.py" "$O/boot-magisk-unsigned.img" "$O/boot-magisk-owner-signed.img"
bash "$P/device-inspection/run-native-build-host.sh" "/home/pablo/kyf37-build-logs/r-$NAME-magisk-validate.log" --script "$P/flip_walker/tools/validate-magisk-images.sh" "$NAME"
grep -q MAGISK_VALIDATE_OK "$P/native/kyf37-build-logs/r-$NAME-magisk-validate.log"
debugfs -R "dump /app/FlipWalker/FlipWalker.apk $P/flip_walker/dist/magisk-image-FlipWalker.apk" "$O/system-magisk.raw.img"
cmp "$P/flip_walker/dist/FlipWalker.apk" "$P/flip_walker/dist/magisk-image-FlipWalker.apk"
"$P/native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin/java" -jar "$P/flip_pokedex/cache/build-tools/android-11/lib/apksigner.jar" verify "$P/flip_walker/dist/magisk-image-FlipWalker.apk"
python3 "$P/device-inspection/build-twrp-android11-installer.py" --boot "$O/boot-magisk-owner-signed.img" --system "$O/system-magisk.raw.img" --audit-dir "$O/magisk-audit" --vendor-audit "$O/vendor-audit.json" --installer-tests "$P/kyf37-rom/android11-no-new-backups-installer-tests.json" --output "$P/kyf37-rom/kyf37-android11-go-$NAME-magisk-20261016-twrp.zip"
echo MAGISK_CANDIDATE_OK
