$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $root 'tools/phone-host.ps1')
$lt=Join-Path $root 'tools/phone-lock.ps1';$owner='walker-stack-check';$adb=Get-Kyf37Adb
& $lt status
& $lt acquire $owner 2
try {Assert-Kyf37PhoneLock $owner; $appPid=(& $adb -s YOUR_ADB_SERIAL shell pidof org.kyf37.walker).Trim(); if($appPid -notmatch '^\d+$'){throw 'App not running'};& $adb -s YOUR_ADB_SERIAL shell su -c "debuggerd -b $appPid"} finally {& $lt release $owner}
