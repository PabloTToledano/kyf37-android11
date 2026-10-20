$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock 'gps-walker-read'
$adb=Get-Kyf37Adb
$policy=& $adb -s YOUR_ADB_SERIAL shell dumpsys window policy
if (($policy -join "`n") -notmatch '(?m)^\s+secure=false\s*$' -or ($policy -join "`n") -notmatch 'mSimSecure=false') { throw 'Owner must unlock native authentication; no credentials will be entered.' }
Assert-Kyf37PhoneLock 'gps-walker-read'
& $adb -s YOUR_ADB_SERIAL shell input keyevent 224
& $adb -s YOUR_ADB_SERIAL shell wm dismiss-keyguard

for ($i=0; $i -lt 20; $i++) {
 $policy=& $adb -s YOUR_ADB_SERIAL shell dumpsys window policy
 if (($policy -join "`n") -match '(?m)^\s+showing=false\s*$') { break }
 Start-Sleep -Milliseconds 500
}
if (($policy -join "`n") -notmatch '(?m)^\s+showing=false\s*$') { throw 'Native lock screen remains; owner unlock required.' }
