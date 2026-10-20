$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $root 'tools/phone-host.ps1')
$lt=Join-Path $root 'tools/phone-lock.ps1'; $owner='walker-reconnect-check'; $adb=Get-Kyf37Adb; $s='YOUR_ADB_SERIAL'
& $lt status
& $lt acquire $owner 5
function Act([string[]]$Arguments) { Assert-Kyf37PhoneLock $owner; & $adb -s $s @Arguments; if($LASTEXITCODE -ne 0){throw 'Phone check failed'} }
function Focus([string]$Component) {
 $dump=(& $adb -s $s shell dumpsys window) -join "`n"
 $f=[regex]::Match($dump,'(?m)^\s*mCurrentFocus=[^\r\n]*').Value
 Write-Output $f
 if($f -notmatch [regex]::Escape($Component)){throw 'Expected app is not focused. No keys will be entered.'}
}
try {
 Act @('shell','am','start','-W','-n','org.kyf37.pokedex/.PokedexActivity')
 Start-Sleep 2; Focus 'org.kyf37.pokedex'
 Act @('shell','am','start','-W','-n','org.kyf37.walker/.WalkerActivity')
 Start-Sleep 1; Focus 'org.kyf37.walker'
 Act @('shell','input','keyevent','16') # 9 opens emulated walker from the main menu
 Start-Sleep 3; Focus 'EmulatedWalkerActivity'
 & $adb -s $s shell dumpsys activity activities | Select-String 'org.kyf37.walker'
 Act @('shell','input','keyevent','134') # F4 returns, no game connection initiated
 Start-Sleep 2; Focus '/org.kyf37.walker.WalkerActivity'
 Write-Output 'APP_LAUNCH_AND_INTERNAL_EMULATOR_OK'
} finally { & $lt release $owner }
