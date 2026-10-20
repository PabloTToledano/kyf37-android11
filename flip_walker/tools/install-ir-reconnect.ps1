param([switch]$WalkerOnly)
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $root 'tools/phone-host.ps1')
$lockTool=Join-Path $root 'tools/phone-lock.ps1'
$owner='pokedex-walker-update'
$adb=Get-Kyf37Adb
$serial='YOUR_ADB_SERIAL'
& $lockTool status
if ((& $adb -s $serial shell getprop sys.boot_completed).Trim() -ne '1') { throw 'Phone is not fully booted; no installation attempted.' }
& $lockTool acquire $owner 15
try {
 foreach ($app in @(@{ Package='org.kyf37.pokedex'; Apk='flip_pokedex/dist/FlipPokedex.apk' },@{ Package='org.kyf37.walker'; Apk='flip_walker/dist/FlipWalker.apk' })) {
  if ($WalkerOnly -and $app.Package -ne 'org.kyf37.walker') { continue }
  Assert-Kyf37PhoneLock $owner
  $apk=Join-Path $root $app.Apk
  Write-Output "INSTALLING $($app.Package)"
  & $adb -s $serial install -r $apk
  if ($LASTEXITCODE -ne 0) { throw "Update failed: $($app.Package); existing data preserved, no uninstall attempted." }
  $path=(& $adb -s $serial shell pm path $app.Package | Where-Object { $_ -match '/base.apk$' } | Select-Object -First 1)
  if (-not $path) { throw 'Installed APK path unavailable' }
  $remote=$path.Trim().Substring(8)
  $copy=Join-Path $root ("flip_walker/dist/installed-"+$app.Package+'.apk')
  & $adb -s $serial pull $remote $copy
  if ($LASTEXITCODE -ne 0) { throw 'Could not verify installed APK' }
  if ((Get-FileHash -Algorithm SHA256 $copy).Hash -ne (Get-FileHash -Algorithm SHA256 $apk).Hash) { throw 'Installed bytes do not match built APK' }
  Write-Output "INSTALLED_BYTES_OK $($app.Package)"
 }
} finally { & $lockTool release $owner }
