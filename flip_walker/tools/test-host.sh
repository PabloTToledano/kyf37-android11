#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
JAVA="$ROOT/../native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin"
mkdir -p "$ROOT/build/tests"
"$JAVA/javac" -d "$ROOT/build/tests" "$ROOT/templates/src/org/kyf37/walker/Packet.java" "$ROOT/templates/src/org/kyf37/walker/Walker.java" "$ROOT/tests/ProtocolTest.java" "$ROOT/templates/src/org/kyf37/walker/WalkerReader.java" "$ROOT/tests/ReaderTest.java" "$ROOT/templates/src/org/kyf37/walker/WalkerCatalog.java" "$ROOT/templates/src/org/kyf37/walker/GiftBitmap.java" "$ROOT/templates/src/org/kyf37/walker/WalkerTools.java" "$ROOT/templates/src/org/kyf37/walker/RealMenu.java" "$ROOT/tests/ToolsTest.java" "$ROOT/templates/src/org/kyf37/walker/UiText.java" "$ROOT/tests/LocaleTest.java"
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ProtocolTest
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ReaderTest
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ToolsTest
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.LocaleTest
cc -Wall -Wextra -Werror -O2 "$ROOT/native/walker_ir.c" -o "$ROOT/build/tests/walker-ir-host"
"$ROOT/build/tests/walker-ir-host" --self-test
