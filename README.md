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

These results come from recorded Android 11 tests on the development phone, including earlier builds.
The downloadable ROM has **not** passed a complete hardware-verification run. “Unverified” does not mean broken.

| Hardware | Status | Tested / still unverified |
|---|---|---|
| Main display | Working in earlier builds | Android boots and displays the UI. |
| Keypad and D-pad | Working in earlier builds | Navigation and app key handling tested. |
| USB / ADB | Working in earlier builds | Android and recovery connections tested. |
| Internal storage | Working in earlier builds | System boot and app installation tested. |
| microSD | Working in earlier builds | Portable-card mounting and file reads verified after reboot. |
| Camera | Partially verified | Preview/orientation tested; photo reliability and video recording remain unverified. |
| Bluetooth | Partially verified | Controller enabled in a live test; pairing, audio and transfers remain unverified. |
| Infrared | Partially verified | Driver access and transmit/read paths tested; real game/Pokéwalker exchanges remain unverified. |
| Wi-Fi | Unverified for this release | Connection and internet access need retesting. |
| Cellular radio | Unverified for this release | Calls, SMS and mobile data need testing. |
| GPS | Unverified | Outdoor position fix not confirmed. |
| Speaker, microphone and headset | Unverified | Audible playback, recording and call audio need testing. |
| Outer display and lid behavior | Unverified end to end | Real incoming-call display and physical lid behavior need testing. |
| Light, proximity and motion sensors | Unverified | Physical sensor readings and automatic brightness need testing. |
| Flashlight and vibration | Unverified for this release | Physical operation needs testing. |
| Battery / charging | Unverified in detail | Charging behavior, battery reporting and endurance need testing. |
