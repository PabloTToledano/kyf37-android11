#!/bin/bash
set -euo pipefail
flock -n 9 || exit 1
ROOT=$(cd "$(dirname "$0")/.." && pwd)
JAVA="$ROOT/../native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin"
mkdir -p "$ROOT/build/tests"
"$JAVA/javac" -d "$ROOT/build/tests" "$ROOT/templates/src/org/kyf37/walker/EmulatedIr.java" "$ROOT/tests/EmulatedIrTest.java"
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.EmulatedIrTest
