#!/usr/bin/env bash
set -eo pipefail
flock -n 9 || exit 1
P=$(cd "$(dirname "$0")/../.." && pwd)
python3 "$P/device-inspection/fix-android11-microsd.py"
export LC_ALL=C BUILD_USERNAME=althia
export PATH=/home/pablo/kyf37-android11-host/bin:$PATH
cd /home/pablo/kyf37-android11
source build/envsetup.sh
lunch lineage_kyf37-userdebug
m -j8 out/target/product/kyf37/root/fstab.qcom bootimage
bash "$P/device-inspection/package-android11-release.sh" "${1:?Candidate name required}" --magisk-legacy-hooks
