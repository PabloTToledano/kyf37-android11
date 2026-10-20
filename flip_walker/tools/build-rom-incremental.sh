#!/usr/bin/env bash
# Rebuild an already fully staged candidate after app-only changes.
# Invoke via run-native-build-host.sh LOG --script THIS_FILE.
set -eo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
PROJECT=$(cd "$(dirname "$0")/../.." && pwd)
python3 "$PROJECT/device-inspection/stage-android11-flip-walker.py"
python3 "$PROJECT/device-inspection/preflight-android11-candidate.py"
export LC_ALL=C BUILD_USERNAME=althia
export PATH=/home/pablo/kyf37-android11-host/bin:$PATH
cd /home/pablo/kyf37-android11
source build/envsetup.sh
lunch lineage_kyf37-userdebug
m -j8 FlipWalker Kyf37WalkerIrDaemon bootimage systemimage
