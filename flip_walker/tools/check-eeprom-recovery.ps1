$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $root 'tools/phone-host.ps1')
$lt=Join-Path $root 'tools/phone-lock.ps1';$owner='walker-eeprom-check';$adb=Get-Kyf37Adb;$s='YOUR_ADB_SERIAL'
& $lt status
& $lt acquire $owner 3
try {
 Assert-Kyf37PhoneLock $owner
 & $adb -s $s shell am start -n org.kyf37.walker/.WalkerActivity
 if($LASTEXITCODE -ne 0){throw 'Emulator launch failed'}
 Start-Sleep 2
 $dump=(& $adb -s $s shell dumpsys window) -join "`n"
 $focus=[regex]::Match($dump,'(?m)^\s*mCurrentFocus=[^\r\n]*').Value
 if($focus -notmatch '/org.kyf37.walker.WalkerActivity'){throw 'Walker not focused; no key sent'}
 Assert-Kyf37PhoneLock $owner
 & $adb -s $s shell input keyevent 16
 Start-Sleep 8
 & $adb -s $s logcat -d -t 400 -s Pokewalker:I AndroidRuntime:E
 & $adb -s $s shell dumpsys window | Select-String 'mCurrentFocus='
}finally{& $lt release $owner}
