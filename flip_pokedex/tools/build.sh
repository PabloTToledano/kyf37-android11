#!/usr/bin/env bash
# Invoke only via device-inspection/build-locked.sh LOG --script this-file.
set -euo pipefail
flock -n 9 || { echo 'The mandatory build-locked.sh lock is missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROJECT=$(cd "$ROOT/.." && pwd)
TREE=${FLIP_POKEDEX_ANDROID_TREE:-$PROJECT/native/kyf37-android11}
SDK="$TREE/prebuilts/sdk"
export JAVA_HOME="$TREE/prebuilts/jdk/jdk11/linux-x86"
BUILD_TOOLS=$(python3 "$ROOT/tools/prepare_sdk.py")
export PATH="$JAVA_HOME/bin:$BUILD_TOOLS:$PATH"
python3 "$ROOT/tools/stage.py"
python3 "$ROOT/tools/verify_data.py"
python3 "$ROOT/tools/ml/prepare_runtime.py"
python3 "$ROOT/tools/ml/verify_model.py"
APK_NAME=FlipPokedex.apk
ABI_LIST=armeabi-v7a
if [ "${1:-}" = "--emulator" ]; then APK_NAME=FlipPokedex-emulator.apk; ABI_LIST="armeabi-v7a x86_64"; fi
export APK_NAME ABI_LIST
mkdir -p "$ROOT/build/classes" "$ROOT/build/dex" "$ROOT/dist"
find "$ROOT/build/classes" -name '*.class' -delete
# Generate R.java from the app resources (R.raw sounds, R.drawable icon) before compiling Java.
rm -rf "$ROOT/build/gen" && mkdir -p "$ROOT/build/gen"
aapt2 compile --dir "$ROOT/app/res" -o "$ROOT/build/gen-resources.zip"
aapt2 link -o "$ROOT/build/gen-only.apk" -I "$SDK/30/public/android.jar" --manifest "$ROOT/app/AndroidManifest.xml" --min-sdk-version 23 --target-sdk-version 29 --java "$ROOT/build/gen" "$ROOT/build/gen-resources.zip"
find "$ROOT/app/src" -name '*.java' -print > "$ROOT/build/sources.txt"
find "$ROOT/build/gen" -name 'R.java' -print >> "$ROOT/build/sources.txt"
javac -classpath "$ROOT/app/libs/litert.jar:$ROOT/app/libs/litert-api.jar" -encoding UTF-8 -source 8 -target 8 -bootclasspath "$BUILD_TOOLS/core-lambda-stubs.jar:$SDK/30/public/android.jar" -d "$ROOT/build/classes" @"$ROOT/build/sources.txt"
jar cf "$ROOT/build/classes.jar" -C "$ROOT/build/classes" .
java -Xmx512m -cp "$BUILD_TOOLS/lib/d8.jar" com.android.tools.r8.D8 --lib "$SDK/30/public/android.jar" --min-api 23 --output "$ROOT/build/dex" "$ROOT/build/classes.jar" "$ROOT/app/libs/litert.jar" "$ROOT/app/libs/litert-api.jar"
aapt2 compile --dir "$ROOT/app/res" -o "$ROOT/build/resources.zip"
aapt2 link -o "$ROOT/build/unsigned.apk" -I "$SDK/30/public/android.jar" --manifest "$ROOT/app/AndroidManifest.xml" --min-sdk-version 23 --target-sdk-version 29 -0 ogg -0 tflite -A "$ROOT/app/assets" "$ROOT/build/resources.zip"
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys, zipfile, os
root=Path(sys.argv[1])
with zipfile.ZipFile(root/'build/unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:
    for f in sorted((root/'build/dex').glob('*.dex')): z.write(f,f.name)
    for abi in os.environ['ABI_LIST'].split():
        z.write(root/'app/libs'/abi/'libtensorflowlite_jni.so','lib/'+abi+'/libtensorflowlite_jni.so')
PY
zipalign -f 4 "$ROOT/build/unsigned.apk" "$ROOT/build/aligned.apk"
rm -f "$ROOT/dist/$APK_NAME.idsig"
# Public AOSP test credentials only. The owner's recovery signing key is never accessed.
java -jar "$BUILD_TOOLS/lib/apksigner.jar" sign --v4-signing-enabled false --key "$TREE/build/target/product/security/testkey.pk8" --cert "$TREE/build/target/product/security/testkey.x509.pem" --out "$ROOT/dist/$APK_NAME" "$ROOT/build/aligned.apk"
java -jar "$BUILD_TOOLS/lib/apksigner.jar" verify --verbose "$ROOT/dist/$APK_NAME"
aapt2 dump badging "$ROOT/dist/$APK_NAME" > "$ROOT/dist/$APK_NAME-info.txt"
sha256sum "$ROOT/dist/$APK_NAME" > "$ROOT/dist/$APK_NAME.sha256"
echo "APK_READY=$ROOT/dist/$APK_NAME"
