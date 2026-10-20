Complete experimental KYF37 stock-to-custom bundle for Linux and Windows.

Download **kyf37-customizer-20261020.zip** and its `.sha256` file, then extract everything and read
`START-HERE.md`. The bundle includes Android 11 Go, custom keypad TWRP, rooting tools, Linux/Windows ADB,
Zadig, Flip Pokédex 1.1 and Flip Walker 0.9. Missing Python dependencies download on first start.

**Do not flash the separate ROM/recovery assets directly.** They are per-phone personalization inputs;
use the guided installer with the original backups and a signing key generated locally for your phone.
GitHub's generated source archives do not contain the firmware or apps.

35 offline tests passed; APK signatures, ROM payload hashes, per-phone ZIP personalization, Linux bootstrap,
release inventories and ZIP CRCs were checked. No phone changes were made during packaging.
**Stock-to-custom conversion and native Windows execution remain unverified.** The ROM is experimental
and its manifest reports hardware_verified=false. Existing app data and signing keys must be preserved.

The optional separate ROM, recovery and APK downloads are also included in the complete bundle.
Use `SHA256SUMS.txt` to check individual assets. Firmware and APKs are release assets, not Git history.
