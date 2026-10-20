#!/usr/bin/env bash
# Final matching image set; never installs or reboots a phone.
set -euo pipefail
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
NAME=walker-ir-v3
STAMP=20261015
LOGS="$PROJECT/native/kyf37-build-logs"
OUT="$PROJECT/kyf37-rom/android11-$NAME"
bash "$PROJECT/device-inspection/build-locked.sh" "$PROJECT/flip_walker/final-app-build.log" --script "$PROJECT/flip_walker/tools/prepare-rom.sh"
python3 "$PROJECT/flip_walker/tools/test-emulator.py" > "$PROJECT/flip_walker/final-emulator-tests.log" 2>&1
bash "$PROJECT/device-inspection/run-native-build-host.sh" "/home/pablo/kyf37-build-logs/r-$NAME.log" --script "$PROJECT/flip_walker/tools/build-rom-incremental.sh"
grep -q 'BUILD_EXIT=0' "$LOGS/r-$NAME.log"
SYSTEM_APK="$PROJECT/native/kyf37-android11/out/target/product/kyf37/system/app/FlipWalker/FlipWalker.apk"
cmp "$PROJECT/flip_walker/dist/FlipWalker.apk" "$SYSTEM_APK"
"$PROJECT/native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin/java" -jar "$PROJECT/flip_pokedex/cache/build-tools/android-11/lib/apksigner.jar" verify "$SYSTEM_APK"
bash "$PROJECT/device-inspection/run-native-build-host.sh" "/home/pablo/kyf37-build-logs/r-$NAME-package.log" --script "$PROJECT/device-inspection/package-android11-release.sh" "$NAME"
grep -q PACKAGE_STAGE_OK "$LOGS/r-$NAME-package.log"
"$PROJECT/native/host-runtime/signing-venv/bin/python" "$PROJECT/device-inspection/sign-rom-boot.py" "$OUT/boot-unsigned.img" "$OUT/boot-owner-signed.img"
bash "$PROJECT/device-inspection/run-native-build-host.sh" "/home/pablo/kyf37-build-logs/r-$NAME-validate.log" --script "$PROJECT/device-inspection/validate-android11-signed.sh" "$NAME"
grep -q VALIDATE_OK "$LOGS/r-$NAME-validate.log"
debugfs -R "dump /app/FlipWalker/FlipWalker.apk $PROJECT/flip_walker/dist/image-FlipWalker.apk" "$OUT/system.raw.img"
cmp "$PROJECT/flip_walker/dist/FlipWalker.apk" "$PROJECT/flip_walker/dist/image-FlipWalker.apk"
"$PROJECT/native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin/java" -jar "$PROJECT/flip_pokedex/cache/build-tools/android-11/lib/apksigner.jar" verify "$PROJECT/flip_walker/dist/image-FlipWalker.apk"
python3 "$PROJECT/device-inspection/build-twrp-android11-installer.py" --boot "$OUT/boot-owner-signed.img" --system "$OUT/system.raw.img" --audit-dir "$OUT/audit" --vendor-audit "$OUT/vendor-audit.json" --installer-tests "$PROJECT/kyf37-rom/android11-no-new-backups-installer-tests.json" --output "$PROJECT/kyf37-rom/kyf37-android11-go-$NAME-$STAMP-twrp.zip"
echo FINAL_CANDIDATE_OK
