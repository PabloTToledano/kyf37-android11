#!/bin/bash
set -euo pipefail
flock -n 9 || exit 1
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cc -DPW_LIBRARY -w -O2 -I"$ROOT/native/pwcore" "$ROOT/tests/pwcore/firmware_ir_diagnostic.c" "$ROOT/native/pwcore/ssu.c" "$ROOT/native/pwcore/eeprom.c" "$ROOT/native/pwcore/lcd.c" "$ROOT/native/pwcore/accel.c" "$ROOT/native/pwcore/rtc.c" "$ROOT/native/pwcore/portb.c" "$ROOT/native/pwcore/interrupts.c" -lm -o "$ROOT/build/tests/firmware-ir-diagnostic"
"$ROOT/build/tests/firmware-ir-diagnostic" "$ROOT/cache/owner-walker-rom.bin"
