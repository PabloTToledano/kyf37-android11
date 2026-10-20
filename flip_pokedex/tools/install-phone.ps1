# Explicit user-requested APK install. No reboot, wipe, partition write, or PIN entry.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$project = Split-Path $root -Parent
$lockTool = Join-Path $project 'tools/phone-lock.ps1'
$owner = 'codex-flip-pokedex-install'
$serial = 'YOUR_ADB_SERIAL'
$apk = Join-Path $root 'dist/FlipPokedex.apk'
$record = Get-Content (Join-Path $root 'dist/FlipPokedex-packaged-validation.json') -Raw | ConvertFrom-Json
$hash = (Get-FileHash $apk -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $record.apkSha256) { throw 'APK integrity mismatch' }
& $lockTool status
& $lockTool acquire $owner 15
try {
    $lock = Get-Content (Join-Path $project '.phone.lock') -Raw | ConvertFrom-Json
    if ($lock.owner -ne $owner) { throw 'Phone lock ownership changed' }
    $boot = (& adb -s $serial shell getprop sys.boot_completed | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $boot -ne '1') { throw 'Phone is not in booted Android; no install performed' }
    $abi = (& adb -s $serial shell getprop ro.product.cpu.abilist | Out-String).Trim()
    if ($abi -notmatch 'armeabi-v7a') { throw 'Unexpected phone ABI' }
    & adb -s $serial shell df -k /data
    $output = (& adb -s $serial install -r $apk 2>&1 | Out-String)
    $code = $LASTEXITCODE
    Write-Output $output
    if ($code -ne 0 -or $output -notmatch 'Success') { throw 'ADB installation failed; no data was cleared' }
    $path = (& adb -s $serial shell pm path org.kyf37.pokedex | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $path -notmatch '^package:') { throw 'Installed package path not confirmed' }
    $info = (& adb -s $serial shell dumpsys package org.kyf37.pokedex | Out-String)
    if ($info -notmatch 'versionName=1.1-experimental-ai') { throw 'Installed version mismatch' }
    @{ installed = $true; serial = $serial; apkSha256 = $hash; versionName = '1.1-experimental-ai'; packagePath = $path; date = (Get-Date).ToString('o'); modelHardwareVerified = $false; note = 'APK installation only; no reboot or PIN entry; existing app data retained.' } | ConvertTo-Json | Set-Content (Join-Path $root 'dist/phone-installation.json')
    Write-Output 'PHONE_INSTALL_VERIFIED'
} finally {
    & $lockTool release $owner
}
