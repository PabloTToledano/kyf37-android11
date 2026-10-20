#!/usr/bin/env bash
# Only invoke through device-inspection/build-locked.sh LOG --script THIS_FILE.
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT=$(cd "$ROOT/.." && pwd)
TREE="$PROJECT/native/kyf37-android11"
SDK="$TREE/prebuilts/sdk/30/public/android.jar"
export JAVA_HOME="$TREE/prebuilts/jdk/jdk11/linux-x86"
BUILD_TOOLS=$(python3 "$PROJECT/flip_pokedex/tools/prepare_sdk.py")
export PATH="$JAVA_HOME/bin:$BUILD_TOOLS:$PATH"
export WALKER_EMULATOR=0
APK_NAME=FlipWalker.apk
if [ "${1:-}" = "--emulator" ]; then export WALKER_EMULATOR=1; APK_NAME=FlipWalker-emulator.apk; fi
export APK_NAME
python3 "$ROOT/tools/stage.py"
mkdir -p "$ROOT/build/classes" "$ROOT/build/dex" "$ROOT/dist" "$ROOT/app/libs/armeabi-v7a"
python3 "$ROOT/tools/build_native.py"
python3 "$ROOT/tools/stage_pwcore.py"
python3 "$ROOT/tools/build_pwcore.py"  # full-emulation core
find "$ROOT/build/classes" -name '*.class' -delete
rm -rf "$ROOT/build/gen"
mkdir -p "$ROOT/build/gen"
aapt2 compile --dir "$ROOT/app/res" -o "$ROOT/build/resources.zip"
aapt2 link -o "$ROOT/build/resources.apk" -I "$SDK" --manifest "$ROOT/app/AndroidManifest.xml" --java "$ROOT/build/gen" "$ROOT/build/resources.zip"
find "$ROOT/app/src" "$ROOT/build/gen" -name '*.java' -print > "$ROOT/build/sources.txt"
javac -encoding UTF-8 -source 8 -target 8 -bootclasspath "$BUILD_TOOLS/core-lambda-stubs.jar:$SDK" -d "$ROOT/build/classes" @"$ROOT/build/sources.txt"
jar cf "$ROOT/build/classes.jar" -C "$ROOT/build/classes" .
java -cp "$BUILD_TOOLS/lib/d8.jar" com.android.tools.r8.D8 --lib "$SDK" --min-api 23 --output "$ROOT/build/dex" "$ROOT/build/classes.jar"
aapt2 link -o "$ROOT/build/unsigned.apk" -I "$SDK" --manifest "$ROOT/app/AndroidManifest.xml" -A "$ROOT/app/assets" "$ROOT/build/resources.zip"
python3 - "$ROOT" <<'PY'
import sys,zipfile,os
from pathlib import Path
r=Path(sys.argv[1])
with zipfile.ZipFile(r/'build/unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
    z.write(r/'build/dex/classes.dex','classes.dex')
    z.write(r/'app/libs/armeabi-v7a/libwalker_ir.so','lib/armeabi-v7a/libwalker_ir.so')
    z.write(r/'app/libs/armeabi-v7a/libpwcore.so','lib/armeabi-v7a/libpwcore.so')  # full-emulation
    if os.environ['WALKER_EMULATOR']=='1': z.write(r/'app/libs/x86_64/libwalker_ir.so','lib/x86_64/libwalker_ir.so')
PY
zipalign -f 4 "$ROOT/build/unsigned.apk" "$ROOT/build/aligned.apk"
# Public AOSP test credentials only. Never accesses the owner's signing key.
java -jar "$BUILD_TOOLS/lib/apksigner.jar" sign --v4-signing-enabled false --key "$TREE/build/target/product/security/testkey.pk8" --cert "$TREE/build/target/product/security/testkey.x509.pem" --out "$ROOT/dist/$APK_NAME" "$ROOT/build/aligned.apk"
java -jar "$BUILD_TOOLS/lib/apksigner.jar" verify --verbose "$ROOT/dist/$APK_NAME"
aapt2 dump badging "$ROOT/dist/$APK_NAME" > "$ROOT/dist/$APK_NAME-info.txt"
sha256sum "$ROOT/dist/$APK_NAME" > "$ROOT/dist/$APK_NAME.sha256"
echo "APK_READY=$ROOT/dist/$APK_NAME"
