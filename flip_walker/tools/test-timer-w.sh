#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/build/tests"
cc -O2 -w "$ROOT/tests/pwcore/timer_w_test.c" "$ROOT/native/pwcore/ssu.c" "$ROOT/native/pwcore/eeprom.c" "$ROOT/native/pwcore/lcd.c" "$ROOT/native/pwcore/accel.c" "$ROOT/native/pwcore/rtc.c" "$ROOT/native/pwcore/portb.c" "$ROOT/native/pwcore/interrupts.c" -lm -o "$ROOT/build/tests/timer-w"
"$ROOT/build/tests/timer-w"
