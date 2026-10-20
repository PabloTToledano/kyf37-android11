# Before starting and if installation stops

The installer first backs up the stock partitions to the microSD and keeps the essential signing inputs in
its per-phone workspace. This backup excludes userdata; copy personal files separately before starting.
Keep the complete workspace, generated signing key and microSD backup private and intact.

The stock-phone installer includes a guided microSD rescue test. Complete it before any signing-partition
changes. It creates NOTPUSH, CHKCODE and FASTBOOT markers with DEVKEYDL content, asks the user to test the
0482:0a7f USB download entry, and removes its markers afterwards. If interrupted, check the card on a computer
and remove these three markers before a normal boot. Existing unknown markers are never overwritten.

After a failed write, remain in recovery. A software rollback may have been attempted, but it must be checked
against the recorded partition hashes. A power interruption or mixed signing state requires investigation;
do not keep retrying unknown partition writes. Preserve all original and custom rollback backups.

Do not factory-reset or wipe userdata. Do not flash the stock ROM, or use another device's keystore, radio,
modem, persist or calibration images. Rescue USB detection is not a complete unbrick procedure.

The ROM/recovery in this package are templates for per-phone signing. Never install the bundled ROM ZIP or
recovery image directly. Resume through the installer with the original workspace and key.

If you need help, share the stage name and error text after reviewing it for personal information.
Never share a private signing key, per-phone partition backup or calibration data.
