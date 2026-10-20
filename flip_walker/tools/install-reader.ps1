$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock 'gps-walker-read'
$adb=Get-Kyf37Adb
$dir=Join-Path $PSScriptRoot '../dist/hardware'
& $adb -s YOUR_ADB_SERIAL root
& $adb -s YOUR_ADB_SERIAL wait-for-device
try {
 Assert-Kyf37PhoneLock 'gps-walker-read'
 & $adb -s YOUR_ADB_SERIAL shell 'for p in /data/user/0/org.kyf37.walker/files/walker.eeprom /data/user/0/org.kyf37.walker/files/walker.eeprom.bak; do if [ -f "$p" ]; then sha256sum "$p"; else echo "ABSENT $p"; fi; done' | Set-Content (Join-Path $dir 'reader-save-before.txt')
} finally {
 Assert-Kyf37PhoneLock 'gps-walker-read'
 & $adb -s YOUR_ADB_SERIAL unroot
 & $adb -s YOUR_ADB_SERIAL wait-for-device
}
Assert-Kyf37PhoneLock 'gps-walker-read'
& $adb -s YOUR_ADB_SERIAL install -r (Join-Path $PSScriptRoot '../dist/FlipWalker.apk')
if ($LASTEXITCODE -ne 0) { throw 'Reader update failed' }
& $adb -s YOUR_ADB_SERIAL shell am start -W -n org.kyf37.walker/.WalkerActivity
& $adb -s YOUR_ADB_SERIAL shell dumpsys package org.kyf37.walker
