$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock 'gps-walker-read'
$adb=Get-Kyf37Adb
& $adb -s YOUR_ADB_SERIAL root
& $adb -s YOUR_ADB_SERIAL wait-for-device
try {
 Assert-Kyf37PhoneLock 'gps-walker-read'
 $after=& $adb -s YOUR_ADB_SERIAL shell 'for p in /data/user/0/org.kyf37.walker/files/walker.eeprom /data/user/0/org.kyf37.walker/files/walker.eeprom.bak; do if [ -f "$p" ]; then sha256sum "$p"; else echo "ABSENT $p"; fi; done'
 $after | Set-Content (Join-Path $PSScriptRoot '../dist/hardware/languages-save-after.txt')
 $before=Get-Content (Join-Path $PSScriptRoot '../dist/hardware/languages-save-before.txt')
 if (($before -join "`n") -ne ($after -join "`n")) { throw 'Virtual save changed; investigate before claiming preservation' }
 'EXISTING_VIRTUAL_SAVE_UNCHANGED'
} finally {
 Assert-Kyf37PhoneLock 'gps-walker-read'
 & $adb -s YOUR_ADB_SERIAL unroot
 & $adb -s YOUR_ADB_SERIAL wait-for-device
}
