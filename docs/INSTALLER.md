# KYF37 installer — stock Android 5.1 → rooted → backed up → custom TWRP → custom Android 11 ROM

Interactive installer for **Linux** (`./install.sh`) and **Windows** (`.\install.ps1`). It walks you through nine stages:

| # | Stage | What it does | Changes the phone? |
|---|---|---|---|
| 1 | Check | model KYF37, stock Android 5.1, battery ≥ 50 %, free disk space, bundled tools verified | no |
| 2 | Diagnostic USB mode | switches on the factory diagnostic USB mode (`05c6:9091`) through the `transfer` service, reboots | yes (one setting) |
| 3 | Root | pushes BusyBox + Magisk 23, sets the factory flag to permissive SELinux, starts Magisk through the diagnostic root shell, installs the Magisk app | yes |
| 4 | Backup | copies every partition except `userdata`/`cache` (boot, recovery, aboot, keystore, system, modem, modemst1/2, fsg, **persist**, …) to a folder on the microSD, with md5 verification of each | writes only to the card |
| 5 | microSD recovery test | creates the three marker files that make the bootloader enter its USB download mode, asks you to try it, then removes them | writes marker files to the card |
| 6 | Signing | creates **your own** RSA key on this computer, reads the OEM key from your phone's `aboot`, and builds a keystore + signed boot/recovery/TWRP images | no (offline) |
| 7 | TWRP | phase A: stock recovery → boot → keystore (written last), each verified, automatic rollback on any failure; reboot to prove Android still starts; phase B: custom TWRP | yes |
| 8 | ROM | rebuilds the ROM ZIP for *your* phone and key, sideloads it in TWRP | yes |
| 9 | Apps | waits for Android boot, verifies/installs bundled Pokédex and Flip Walker APKs | yes (ordinary app updates; existing data retained) |

## Read this first

* **It is a dry run unless you pass `--live`.** In a dry run, read-only checks and the offline signing/ZIP work still
  run; every command that would change the phone is printed instead of executed. Do a dry run first.
* **It has never been run end to end on a stock KYF37.** The author's phone was already converted. Each piece comes
  from a procedure that worked on that phone, and the signing code and ZIP rebuild were tested offline against that
  phone's stock images (the stock boot verifies against the OEM key read from `aboot`, new images verify with the new
  key, the rebuilt ZIP's checks and hashes are consistent). The hidden-service call (stage 2), the diagnostic root
  route (stage 3), and the partition writes on someone else's phone are **unverified here**. Writing the keystore,
  boot and recovery of a locked-bootloader phone can leave it unbootable if something differs. You are doing this at
  your own risk.
* **Your signing key** is created at `~/kyf37-installer-work/<serial>/owner-signing-key.pem`. Back it up and never
  share it. After stage 7 the phone only boots images signed with it, so you need it for every future boot or
  recovery update. The private key never leaves your computer.
* **Your data.** The ROM installer preserves `userdata` and never wipes. Going from Android 5.1 straight to Android 11
  with the old app data has not been tested and may not boot; if the first boot loops, preserve userdata and seek help; do not wipe it. Back up anything you care about first (stage 4 does not copy `userdata`).
* The backup in stage 4 includes `persist`, `modem*` and `fsg`, which hold your radio/IMEI calibration. Keep a copy
  of the card folder on your computer.

## What you need

* A stock KYF37 on Android 5.1, ≥ 50 % battery, USB debugging on, a FAT32 microSD with ≥ 3 GB free.
* Android platform-tools are downloaded from Google automatically when ADB is missing. Existing ADB on PATH is reused.
* The launchers obtain Python when missing and maintain a private `.venv` with `cryptography`, `pyusb`, and `libusb-package`. Linux needs curl or wget and tar to obtain Python; automatic ADB downloads support x86-64 Linux and Windows. Other CPUs need a compatible ADB on PATH.
* The ROM installer ZIP is downloaded from the latest GitHub release when a unique Android 11 TWRP asset with a published digest is available. You can supply `--rom FILE` or `--rom-url HTTPS_URL --rom-sha256 HASH` instead. The script rebuilds it into
  `~/kyf37-installer-work/<serial>/kyf37-rom-for-<serial>.zip` (about 1.6 GB).
* **Windows only:** the WinUSB driver for interface 0 of `05c6:9091` via [Zadig](https://zadig.akeo.ie/) (Options →
  List all devices → the interface-0 entry → WinUSB → Replace Driver). Leave interface 3 (ADB) alone.
* **Linux only:** a udev rule for `05c6:9091` (the script prints it), or run with `sudo`.

## Usage

```bash
./install.sh                         # Linux, dry run, interactive menu
./install.sh --live --rom ~/Downloads/kyf37-android11-go-...-twrp.zip
./install.sh --stage check           # run a single stage
```
```powershell
.\install.ps1
.\install.ps1 --live --rom C:\Users\you\Downloads\kyf37-android11-go-....zip
```

Progress is kept in `~/kyf37-installer-work/<serial>/state.json`, so you can stop and continue. Every write stage
asks you to type `I UNDERSTAND` first.

## If something goes wrong

* A failed write stage restores the partitions it changed from copies kept in `/data/local/tmp` on the phone.
* The full original partitions are on the microSD (stage 4) and the key ones in the workspace (`stock/`).
* If the phone no longer boots, the microSD download mode (stage 5) is the way back in, together with those backups.
  The project's USB recovery notes (`docs/recovery/USB-RECOVERY.md`) describe that path.

## Files

`kyf37_installer.py` stages and menu · `kyf37_diag.py` factory diagnostic USB protocol · `kyf37_crypto.py` key,
keystore and image signing · `kyf37_zip.py` per-phone ROM ZIP · `payload/` BusyBox, Magisk 23, the two
write-protection tools (the same binaries the ROM installer hash-checks), and the unsigned TWRP image
(`SHA256SUMS` is verified before use).

## Safe reruns

Use the same workspace and `--serial SERIAL` on every run. Only one installer may use a phone workspace at once.
A dry run never marks a stage complete. Old unversioned completion markers are discarded because previous versions
could record dry runs as completed installs. Backups and signing keys are preserved during migration.

* Backups are checkpointed per partition. A rerun checks saved originals against their recorded checksums and skips
  copying them. Existing untracked or damaged backups cause a stop, never an overwrite. The backup stage requires
  stock Android 5.1; never use it to replace the stock backup after conversion.
* Signed images and personalized ZIPs are reused after their inputs and output checksums match. A missing signing
  key never causes the ROM stage to silently create a replacement. Keep the entire per-phone workspace.
* Recovery retries inspect boot/recovery/keystore hashes. A completed phase A resumes at the Android boot check;
  completed phase B skips partition writes and enters recovery. Unexpected or partial partition sets stop for
  investigation. Power loss during a partition write is not automatically recoverable.
* A ROM retry skips sideload when boot and system already match the personalized ZIP. Otherwise sideload must
  succeed and new recovery log output must confirm readback. Installation completion does not prove first boot
  or hardware functionality.
* Single-stage failures return a nonzero exit status. The menu completion timestamps describe successful live
  stages; rerun an individual stage when you want it to recheck its current state.

This workflow remains **unverified end to end on stock hardware**. Offline tests simulate ADB and do not test
USB drivers, diagnostic rooting, bootloader acceptance, rescue behavior or real flash recovery.

Run offline checks with `python3 -m unittest discover -s kyf37-installer/tests -v` from the project root.
Source patches are reproducible with `device-inspection/fix-kyf37-installer-resume.py` followed by
`device-inspection/fix-kyf37-installer-guards.py`.

## Automatic downloads

Start `./install.sh` on Linux or `./install.ps1` on Windows. Both default to dry run.
The launchers download missing Python and Python dependencies, then the installer obtains missing ADB.
Downloads live in `.downloads/`; private Python lives in `.python/`. Existing system Python and ADB are reused.
Interrupted downloads use temporary files. ROM files are reused only when their published SHA-256 matches.
No signing key is downloaded or uploaded.

Windows Python is obtained from python.org and its Authenticode signature is checked before installation.
Linux's fallback Python comes from the public python-build-standalone GitHub release; system Python is preferred.
Python packages and platform-tools are fetched over HTTPS from their upstream services.

If the latest ROM release does not publish the required Android 11 asset or its SHA-256, automatic ROM selection
stops. Supply a specific release URL and its trusted published digest, or a local ZIP. No Android 10 package is
silently selected. Windows diagnostic WinUSB setup still requires manual interface selection in Zadig; replacing
the wrong interface can disable ADB. Linux USB permissions may require an administrator to install the printed
udev rule. The installer does not change host drivers or privileged system configuration automatically.

Example: `./install.sh --rom-url https://example.org/kyf37-android11-twrp.zip --rom-sha256 PUBLISHED_HASH`
(replace the URL and hash with the actual release values).

Reapply the download sources with `python3 device-inspection/fix-kyf37-installer-downloads.py` after the two
resume/guard patch scripts. Offline tests cover Windows and Linux archive layouts. Native Windows execution and
end-to-end phone installation remain unverified.

## Pokédex and Flip Walker installation

The release includes both apps in `apps/`. Stage 9 follows ROM installation and waits up to ten minutes for
Android to finish booting. It verifies the bundled APK checksums and device compatibility before installation.
Matching installed APKs are skipped, newer versions are kept, and older/mismatched APKs receive an ordinary
`adb install -r` update. Existing app data is retained; a signature conflict stops without uninstalling the app.
Installed version and APK hash must match before each app is checkpointed. A rerun rechecks both apps even if
the stage previously completed. The installer does not launch apps, grant permissions, format storage or start IR.

After an interrupted first boot, resume only this stage with `./install.sh --live --stage apps` on Linux or
`.\install.cmd --live --stage apps` on Windows. A dry run only describes the app stage and does not wait or install.
The APKs support ARMv7: Pokédex needs API 23+, Flip Walker API 26+. Both work with the bundled Android 11 ROM.
On first use, grant the permissions you choose in Android; Walker's IR functions require compatible ROM
support and user-approved root/companion access. The installer does not change native authentication or dialer.
