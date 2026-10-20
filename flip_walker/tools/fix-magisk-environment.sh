#!/usr/bin/env bash
# Complete the official app's environment-copy step; no partition writes/reboot.
set -euo pipefail
P=$(cd "$(dirname "$0")/../.." && pwd)
python3 - "$P" <<'PY'
from pathlib import Path
import zipfile,json,datetime,hashlib,sys
p=Path(sys.argv[1]);record=json.loads((p/'.phone.lock').read_text())
assert record['owner']=='flip-walker-ir'
assert datetime.datetime.fromisoformat(record['expires'])>datetime.datetime.now(datetime.timezone.utc)
r=p/'flip_walker/cache/magisk-v30.7';apk=r/'Magisk-v30.7.apk'
assert hashlib.sha256(apk.read_bytes()).hexdigest()=='e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5'
dest=r/'environment';dest.mkdir(exist_ok=True)
with zipfile.ZipFile(apk) as z:
 for n in ['addon.d.sh','app_functions.sh','boot_patch.sh','module_installer.sh','uninstaller.sh','util_functions.sh','stub.apk']:
  (dest/n).write_bytes(z.read('assets/'+n))
 for n in ['busybox','magisk','magiskboot','magiskinit','init-ld','magiskpolicy']:
  (dest/n).write_bytes(z.read('lib/armeabi-v7a/lib'+n+'.so'))
PY
A=/usr/bin/adb
S=YOUR_ADB_SERIAL
"$A" -s "$S" shell id | grep -q 'uid=0'
"$A" -s "$S" shell getprop sys.boot_completed | grep -qx 1
"$A" -s "$S" shell mkdir -p /data/local/tmp/flipwalker-magisk-environment
"$A" -s "$S" push "$P/flip_walker/cache/magisk-v30.7/environment/." /data/local/tmp/flipwalker-magisk-environment/
"$A" -s "$S" shell 'cd /data/local/tmp/flipwalker-magisk-environment && BOOTMODE=true && . ./util_functions.sh && . ./app_functions.sh && fix_env /data/local/tmp/flipwalker-magisk-environment && MAGISKTMP=$(/data/adb/magisk/magisk --path) && env_check 30.7 30700 && echo MAGISK_ENVIRONMENT_OK'
