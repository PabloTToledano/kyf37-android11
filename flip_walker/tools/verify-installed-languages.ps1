$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock 'gps-walker-read'
$adb=Get-Kyf37Adb
$path=(& $adb -s YOUR_ADB_SERIAL shell pm path org.kyf37.walker).Trim() -replace '^package:', ''
if ($path -notmatch '^/data/app/[A-Za-z0-9_./=+~:-]+/base.apk$') { throw 'Unexpected active APK path' }
$hash=(& $adb -s YOUR_ADB_SERIAL shell sha256sum $path).Trim().Split(' ')[0]
$expected=(Get-FileHash -Algorithm SHA256 (Join-Path $PSScriptRoot '../dist/FlipWalker.apk')).Hash.ToLowerInvariant()
if ($hash -ne $expected) { throw 'Installed APK does not match final artifact' }
"INSTALLED_APK_MATCH=$hash"
& $adb -s YOUR_ADB_SERIAL shell id
& $adb -s YOUR_ADB_SERIAL shell dumpsys package org.kyf37.walker | Select-String 'versionCode=|versionName=|userId='
