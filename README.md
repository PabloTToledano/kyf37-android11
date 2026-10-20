# kyf37-android11

Install Android 11 Go, custom keypad TWRP, Flip Pokédex and Flip Walker on a Kyocera GRATINA KYF37.

## Installation

1. Start with a **stock KYF37 running Android 5.1**, at least **50% battery**, USB debugging enabled,
   a **FAT32 microSD with 3 GB free**, and **8 GB free on your computer**. Back up personal files separately.
2. Download **[kyf37-customizer-20261020.zip](https://github.com/PabloTToledano/kyf37-customizer/releases/download/v2026.10.20-experimental/kyf37-customizer-20261020.zip)**
   from the [experimental release](https://github.com/PabloTToledano/kyf37-customizer/releases/tag/v2026.10.20-experimental).
   Extract the whole ZIP to a writable folder. Use this complete bundle, not the GitHub source archives.
3. Connect the phone by USB and accept its USB-debugging authorization prompt.
4. Start the installer:

   | System | Dry run | Install |
   |---|---|---|
   | Linux | `./install.sh` | `./install.sh --live` |
   | Windows | Double-click `install.cmd` | Run `.\install.cmd --live` in PowerShell |

   Missing Python dependencies download automatically. On Windows, use the included Zadig utility when prompted:
   install WinUSB for **interface 0 of 05c6:9091**, leaving interface 3 as ADB. On Linux, follow the printed
   USB-permissions instructions if needed.
5. Follow the guided stages: root, firmware backup, rescue test, per-phone signing, recovery and ROM installation.
   Keep USB connected through the first Android boot; the final stage installs Pokédex and Flip Walker.

Keep the generated signing key, per-phone workspace and original backups private. **Do not flash the separate
ROM/recovery downloads directly, wipe userdata, or flash the stock ROM.** See the [detailed guide](docs/INSTALLER.md)
if a stage stops. To resume only the apps, use `./install.sh --live --stage apps` on Linux or
`.\install.cmd --live --stage apps` on Windows.

**Experimental:** stock-to-custom installation has not been tested end to end on a stock phone. Native Windows
launcher/driver behavior remains unverified.

## Hardware status

| Hardware | Status |
|---|---|
| Main display | ✅ Working |
| Keypad and D-pad | ✅ Working |
| USB / ADB | ✅ Working |
| Internal storage | ✅ Working |
| microSD | ✅ Working |
| Camera | ✅ Working |
| Bluetooth | ✅ Working |
| Infrared | ✅ Working |
| Wi-Fi | ✅ Working |
| Cellular radio | ✅ Working |
| GPS | ✅ Working |
| Speaker, microphone and headset | ✅ Working |
| Outer display and lid behavior | ✅ Working |
| Light, proximity and motion sensors | ✅ Working |
| Flashlight and vibration | ✅ Working |
| Battery / charging | ✅ Working |
