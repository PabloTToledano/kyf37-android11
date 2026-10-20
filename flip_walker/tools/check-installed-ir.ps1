# Run only after a matching ROM installation. Does not enter keys or access game saves.
param([string]$LockOwner = 'flip-walker-ir')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../tools/phone-host.ps1')
Assert-Kyf37PhoneLock $LockOwner
$adb = Get-Kyf37Adb
$serial = 'YOUR_ADB_SERIAL'
$rooted = $false
try {
    if ((& $adb -s $serial shell getprop sys.boot_completed).Trim() -ne '1') { throw 'Android has not completed boot.' }
    Assert-Kyf37PhoneLock $LockOwner
    & $adb -s $serial root
    $rooted = $true
    & $adb -s $serial wait-for-device
    if ((& $adb -s $serial shell id) -notmatch 'uid=0') { throw 'Root diagnostic access unavailable.' }
    Assert-Kyf37PhoneLock $LockOwner
    & $adb -s $serial shell /system/bin/kyf37-walker-ir --self-test
    & $adb -s $serial shell /system/bin/kyf37-walker-ir --probe
    if ($LASTEXITCODE -ne 0) { throw 'Native UART initialization failed.' }
    # Only the disposable diagnostic result is removed; walker EEPROM is untouched.
    & $adb -s $serial shell rm -f /data/user/0/org.kyf37.walker/files/last-ir-probe.txt
    & $adb -s $serial shell am start-foreground-service -n org.kyf37.walker/.IrProbeService
    if ($LASTEXITCODE -ne 0) { throw 'App diagnostic could not start.' }
    Start-Sleep -Seconds 15
    $result = & $adb -s $serial shell cat /data/user/0/org.kyf37.walker/files/last-ir-probe.txt
    $result
    if (($result -join "`n") -notmatch 'APP_IR_PROBE_OK') { throw 'App UID infrared diagnostic failed.' }
    & $adb -s $serial shell cat /proc/uptime
    & $adb -s $serial shell dumpsys sensorservice
} finally {
    if ($rooted) {
        Assert-Kyf37PhoneLock $LockOwner
        & $adb -s $serial unroot
        & $adb -s $serial wait-for-device
    }
}
