#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Run through build-locked.sh'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TREE="$ROOT/../native/kyf37-android11"
export JAVA_HOME="$TREE/prebuilts/jdk/jdk11/linux-x86"
export PATH="$JAVA_HOME/bin:$PATH"
python3 "$ROOT/tools/stage.py"
mkdir -p "$ROOT/build/host-test"
python3 "$ROOT/tools/ml/prepare_runtime.py"
# Generate R.java from the app resources, as the APK build does, so the activities compile on the host.
BUILD_TOOLS=$(python3 "$ROOT/tools/prepare_sdk.py")
rm -rf "$ROOT/build/host-gen" && mkdir -p "$ROOT/build/host-gen"
"$BUILD_TOOLS/aapt2" compile --dir "$ROOT/app/res" -o "$ROOT/build/host-res.zip"
"$BUILD_TOOLS/aapt2" link -o "$ROOT/build/host-res.apk" -I "$TREE/prebuilts/sdk/30/public/android.jar" --manifest "$ROOT/app/AndroidManifest.xml" --java "$ROOT/build/host-gen" "$ROOT/build/host-res.zip"
javac -classpath "$ROOT/app/libs/litert.jar:$ROOT/app/libs/litert-api.jar" -encoding UTF-8 -source 8 -target 8 -bootclasspath "$TREE/prebuilts/sdk/tools/linux/bin/core-lambda-stubs.jar:$TREE/prebuilts/sdk/30/public/android.jar" -d "$ROOT/build/host-test" "$ROOT"/app/src/org/kyf37/pokedex/*.java "$ROOT"/build/host-gen/org/kyf37/pokedex/R.java
javac -encoding UTF-8 -d "$ROOT/build/host-test" "$ROOT/templates/src/org/kyf37/pokedex/DexLogic.java" "$ROOT/tools/DexLogicTest.java"
java -cp "$ROOT/build/host-test" DexLogicTest
