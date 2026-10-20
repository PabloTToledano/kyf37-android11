$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock 'gps-walker-read'
$adb=Get-Kyf37Adb
& $adb -s YOUR_ADB_SERIAL shell am force-stop org.kyf37.walker
Assert-Kyf37PhoneLock 'gps-walker-read'
& $adb -s YOUR_ADB_SERIAL shell am start -W -n org.kyf37.walker/.WalkerActivity
& python3 (Join-Path $PSScriptRoot 'test-reader-phone.py')
if ($LASTEXITCODE -ne 0) { throw 'Reader keypad regression failed' }
