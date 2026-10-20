# KYF37 Customizer

Linux and Windows installer for a stock **Kyocera GRATINA KYF37**: diagnostic root, original-firmware backup,
per-phone signing, custom keypad TWRP, Android 11 Go, Flip Pokédex and Flip Walker.

**Experimental:** stock-to-custom conversion has not been tested end to end on stock hardware. Native Windows
execution is also unverified. The included ROM candidate reports `hardware_verified=false`. Offline checks do
not establish that a phone conversion will succeed. Read the [installer guide](docs/INSTALLER.md) first.

## Download and start

1. Open [Releases](https://github.com/PabloTToledano/kyf37-customizer/releases/tag/v2026.10.20-experimental) and download
   **kyf37-customizer-20261020.zip** and its `.sha256` file. The complete bundle is about 852 MiB.
   Use the complete bundle, rather than GitHub's generated **Source code** archives.
2. Extract the entire ZIP to a writable folder. It includes the ROM, unsigned custom recovery template,
   rooting tools, both APKs, Linux/Windows ADB, and Zadig for Windows.
3. Charge a stock KYF37 (Android 5.1) to at least 50%, enable USB debugging, authorize your computer,
   and insert a FAT32 microSD with at least 3 GB free. Allow at least 8 GB free on the computer.
4. Linux: run `./install.sh`. Windows: double-click `install.cmd` or run `.\install.ps1` in PowerShell.
   The first start downloads missing Python and Python packages. The default is a dry run.
5. Read `START-HERE.md`. When ready, use `./install.sh --live` or `.\install.cmd --live`.
   The guided workflow asks for confirmation before write stages.

You can also obtain and verify the pinned complete release using `python3 download-release.py`
(or `py -3 download-release.py` on Windows) from a checkout of this repository.

**The separate ROM ZIP and recovery image are personalization inputs. Do not flash them directly.**
Every phone gets its own locally generated signing key and personalized images. The installer never uploads that key.

## What the installer does

| Stage | Operation |
|---|---|
| 1 | Check model, stock version, battery, tools and computer storage |
| 2–3 | Enable diagnostic USB and obtain root |
| 4–5 | Back up original partitions to microSD and guide a rescue-mode test |
| 6–7 | Generate a local signing key, prepare signed images and install custom keypad TWRP |
| 8 | Personalize the ROM ZIP for that phone and install matching boot/system images |
| 9 | Wait for Android boot and install Flip Pokédex 1.1 and Flip Walker 0.9 |

Existing app data is retained. Exact installed APKs are skipped and newer versions are kept. For apps only:
`./install.sh --live --stage apps` or `.\install.cmd --live --stage apps`.

Keep the entire per-phone workspace and original backups private. Do not wipe userdata or flash the stock ROM.
A backup of firmware excludes personal userdata: copy your personal files separately. Never share your signing key.
Windows diagnostic root requires WinUSB on interface 0 of `05c6:9091`, while interface 3 must remain ADB.
Linux USB permissions may need an administrator-installed udev rule. These driver/permission steps are manual.

## Documentation and source

- [Detailed installer and retry behavior](docs/INSTALLER.md)
- [Recovery preparation and failure guidance](docs/recovery/USB-RECOVERY.md)
- [What was tested and what remains unverified](docs/VALIDATION.md)
- [Development and corresponding sources](docs/DEVELOPMENT.md)
- [Pokédex](flip_pokedex/README.md) and [Flip Walker](flip_walker/README.md)
- [Release inventory](docs/release/release.json) and [checksums](docs/release/SHA256SUMS)

Original installer code follows [Apache-2.0](LICENSE). Flip Walker and other bundled components retain their
own licenses; see [NOTICE](NOTICE), [Walker license](flip_walker/LICENSE), and each app's third-party notices.
ROM device-specific proprietary components and Pokémon assets are not relicensed by this repository.
