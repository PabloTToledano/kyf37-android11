# Package contents

- `install.sh`, `install.ps1`, `install.cmd`: Linux/Windows entry points; dry run by default.
- `bootstrap.py`, `requirements.txt`: automatically downloaded Python dependencies.
- `payload/kyf37-twrp-candidate.img`: custom keypad TWRP source image; signed for each recipient during setup.
- `payload/`: BusyBox, Magisk 23 APK/binary, root helper and temporary write-protection helpers.
- `rom/`: matching Android 11 Go boot/system installer template; personalized before sideload.
- `apps/`: Flip Pokédex and Flip Walker APKs plus package/version/checksum metadata.
- `docs/apps/`: app usage and third-party notices. The Pokédex includes offline artwork/classifier assets;
  Flip Walker IR features require compatible ROM support and user-approved permissions/root access.
- `tools/linux/platform-tools/`, `tools/windows/platform-tools/`: Google ADB and companion libraries/notices.
- `tools/windows/zadig-2.9.exe`: diagnostic USB driver tool from the official libwdi release; manual interface selection.
- `release.json`, `SHA256SUMS`, `verify-release.py`: inventory, hashes and offline integrity verification.
- `docs/INSTALLER.md`: detailed stages, backup/resume behavior and recovery guidance.
- `LICENSE`, `NOTICE`: project licensing; bundled upstream software retains its original licenses.

BusyBox is GPL-2.0 (https://busybox.net/); Magisk is GPL-3.0 (https://github.com/topjohnwu/Magisk);
TWRP has GPL/Apache components (https://github.com/TeamWin). Google platform-tools retain their bundled
NOTICE and distribution terms. The ROM includes AOSP/LineageOS and device-specific proprietary components;
the project Apache license does not relicense those components. See NOTICE.

Zadig/libwdi: https://github.com/pbatard/libwdi (GPL-3.0).

No signing private keys, phone backups, host virtual environment, device logs or per-phone workspace are included.
