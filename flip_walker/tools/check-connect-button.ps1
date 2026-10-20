param([int]$KeyCode=23)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $root 'tools/phone-host.ps1')
$lt=Join-Path $root 'tools/phone-lock.ps1';$owner='walker-button-check';$adb=Get-Kyf37Adb;$s='YOUR_ADB_SERIAL'
& $lt status
& $lt acquire $owner 3
try {
 $dump=(& $adb -s $s shell dumpsys window) -join "`n"; $focus=[regex]::Match($dump,'(?m)^\s*mCurrentFocus=[^\r\n]*').Value
 if ($focus -match '/org.kyf37.walker.WalkerActivity') {
  Assert-Kyf37PhoneLock $owner
  & $adb -s $s shell input keyevent 16
  Start-Sleep 8
  $dump=(& $adb -s $s shell dumpsys window) -join "`n"; $focus=[regex]::Match($dump,'(?m)^\s*mCurrentFocus=[^\r\n]*').Value
 }
 if ($focus -notmatch 'EmulatedWalkerActivity') {throw 'Emulator not focused; no keys sent'}
 Assert-Kyf37PhoneLock $owner
 & $adb -s $s shell input keyevent --longpress $KeyCode
 Start-Sleep 2
 & $adb -s $s logcat -d -t 100 -s Pokewalker:I AndroidRuntime:E
}finally {& $lt release $owner}
