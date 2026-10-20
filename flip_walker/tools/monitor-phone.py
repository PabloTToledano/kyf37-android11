#!/usr/bin/env python3
"""Read-only 15-minute boot stability gate. No keys, reboots or root changes."""
import subprocess,time,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def adb(command):
    return subprocess.check_output(['/usr/bin/adb','-s','YOUR_ADB_SERIAL','shell',command],timeout=25).decode().strip()
initial=adb('cat /proc/sys/kernel/random/boot_id');samples=[]
deadline=time.monotonic()+1100
while time.monotonic()<deadline:
    boot=adb('cat /proc/sys/kernel/random/boot_id')
    assert boot==initial,'Phone restarted during monitoring'
    completed=adb('getprop sys.boot_completed')
    uptime=float(adb('cat /proc/uptime').split()[0])
    version=adb('/sbin/magisk -V')
    assert completed=='1','Android is not fully booted'
    assert version=='30700','Magisk 30.7 daemon unavailable'
    crashes=adb('logcat -b crash -d')
    assert not re.search(r'FATAL EXCEPTION|Fatal signal',crashes), 'New crash in Android crash buffer'
    sample={'uptime_seconds':uptime,'boot_completed':True,'magisk_version':version,'new_fatal_crashes':False}
    samples.append(sample);print(json.dumps(sample),flush=True)
    if uptime>900:
        window=adb('dumpsys window');focus=next((l.strip() for l in window.splitlines() if 'mCurrentFocus=' in l),'')
        assert re.search(r'org\.kyf37\.(walker|home)|com\.android\.settings/|NotificationShade|Keyguard',focus),'Unexpected foreground window: '+focus
        report={'stable_over_15_minutes':True,'same_boot':True,'focus':focus,'samples':samples}
        (root/'dist/hardware/boot-stability.json').write_text(json.dumps(report,indent=2))
        print('PHONE_STABILITY_OK',flush=True);break
    time.sleep(30)
else:raise RuntimeError('Stability gate timed out')
