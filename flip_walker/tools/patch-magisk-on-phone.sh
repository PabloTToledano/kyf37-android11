#!/usr/bin/env bash
# Official patcher, on this phone, against our custom candidate FILE only.
# Run through build-locked.sh while holding the PowerShell phone lock.
set -euo pipefail
flock -n 9 || exit 1
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
python3 - "$PROJECT" "${1:-walker-ir-v3}" <<'PY'
from pathlib import Path
import json,datetime,hashlib,zipfile,shutil,sys
p=Path(sys.argv[1]);lock=json.loads((p/'.phone.lock').read_text())
assert lock['owner']=='flip-walker-ir'
assert datetime.datetime.fromisoformat(lock['expires'])>datetime.datetime.now(datetime.timezone.utc)
r=p/'flip_walker/cache/magisk-v30.7';apk=r/'Magisk-v30.7.apk'
assert hashlib.sha256(apk.read_bytes()).hexdigest()=='e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5'
stage=r/'phone';stage.mkdir(exist_ok=True)
with zipfile.ZipFile(apk) as z:
 for n in ['boot_patch.sh','util_functions.sh','stub.apk']:(stage/n).write_bytes(z.read('assets/'+n))
 for n in ['busybox','magisk','magiskboot','magiskinit','init-ld','magiskpolicy']:(stage/n).write_bytes(z.read('lib/armeabi-v7a/lib'+n+'.so'))
shutil.copyfile(p/('kyf37-rom/android11-'+sys.argv[2]+'/boot-unsigned.img'),stage/'boot.img')
PY
ADB=/usr/bin/adb
SERIAL=YOUR_ADB_SERIAL
"$ADB" -s "$SERIAL" shell id | grep -q 'uid=0'
"$ADB" -s "$SERIAL" shell mkdir -p /data/local/tmp/flipwalker-magisk307
"$ADB" -s "$SERIAL" push "$PROJECT/flip_walker/cache/magisk-v30.7/phone/." /data/local/tmp/flipwalker-magisk307/
"$ADB" -s "$SERIAL" shell 'cd /data/local/tmp/flipwalker-magisk307 && chmod 755 busybox magisk magiskboot magiskinit init-ld magiskpolicy && ASH_STANDALONE=1 BOOTMODE=true KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false RECOVERYMODE=false LEGACYSAR=false PREINITDEVICE=cache ./busybox sh ./boot_patch.sh ./boot.img'
"$ADB" -s "$SERIAL" pull /data/local/tmp/flipwalker-magisk307/new-boot.img "$PROJECT/kyf37-rom/android11-${1:-walker-ir-v3}/boot-magisk-unsigned.img"
echo MAGISK_PATCH_FILE_OK
