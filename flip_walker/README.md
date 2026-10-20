# Bottom controls

The bottom bar uses the phone's physical **Contacts**, **Camera**, **Mail** and
**Browser** icons instead of F1–F4 text. The left/right action labels use the same
fixed positions and baselines in both rows. The center OK button has its action
centered beneath it on the lower-row baseline. English and Spain Spanish labels
fit in separate columns; button bindings and all app functions stay the same.

# English + Español (España)

Settings (**main menu 7**) → **F2 Language / Idioma** switches between English
and Spanish from Spain and remembers the choice. First launch follows the
phone's language, using es-ES for Spanish. **F3 still switches real/demo data**.
Menus, reviews, progress/errors, bottom controls, walking notifications and
item/move/ability catalogs are translated. Pixel lettering includes accented
vowels, ñ, ü, ¿ and ¡. Language changes do not modify walking or captured data.
Spanish catalog names use PokeAPI's Spain language entry and Gen IV item indexes,
not the separate Latin American entry. Pokémon species and trainer names retain
their identities. All previous app functions remain.

# Flip Walker 0.5 — colorful DS interface and real-device tools

The original seven app functions remain available. Main-menu **8** opens
**Real Pokewalker**. Its six operations match pwalkerHax:

1. Read trainer, trainer/secret IDs, today steps, pairing/Pokémon flags and raw sync time.
2. Back up the complete 64 KiB EEPROM separately from the app's walking save.
3. Add 1–65,535 watts; optionally replace today steps (1–99,999; **0 keeps today unchanged**) and set total steps to 9,999,999.
4. Gift Pokémon: all 493 species, held item, four moves, level, gender, shiny and ability. A species and first move are required. Trainer ownership comes from the physical walker. As upstream, the event uses placeholder animation, not species artwork.
5. Gift an item from the full reference catalog.
6. Dump the 48 KiB ROM via the upstream temporary RAM payload; no firmware is installed.

Up/down chooses fields, left/right adjusts values, number keys enter a numeric
value or catalog ID, and OK toggles entry. Select **Review & connect** to inspect
all parameters; OK then starts the operation. Back cancels the review. F2 selects
or stops an operation, F3 exports the latest EEPROM backup (or ROM when Dump ROM
is selected), F1 returns to the app menu, F4/Clear returns one level.

Open **CONNECT** on the physical walker and aim its infrared window at the
phone. Gift/watts operations save a full EEPROM capture **before any change**;
if that read or local save fails, writes do not start. Stopping after changes
begin can leave a partial operation. Prior captures stay preserved; automatic
restore is not implemented by the reference app or this build. ROM export and
EEPROM export are raw binaries stored separately; neither replaces walker.eeprom.

The interface uses original pixel lettering and artwork with brighter blue,
mint, coral, purple and gold cards, clear selection borders and the four-key
bottom bar. No copyrighted game art or ROM is bundled.

These physical-device operations are experimental until tested against a real
Pokéwalker. UART access alone is not an optical exchange test. Existing game
pairing/return still needs the patched 3DS peer. Generated catalogs/payloads and
adapted master routines are GPL-3.0; see THIRD_PARTY.md and LICENSE.

---

# Flip Walker for KYF37

Pixel-art development candidate, **real-game compatibility not yet verified**.
The app and matching UART kernel/companion are installed on the phone. Physical
phone checks passed for keypad events, the step-sensor registration and infrared
UART access through both the companion and Magisk 30.7. Optical signaling and a
real patched-3DS exchange remain unverified. See `VALIDATION.md` and `MAGISK.md`.

This is a native Android app with original bitmap lettering, tile scenery, pixel
icons, stepped frames and a gold/green HeartGold/SoulSilver-inspired palette.
It has a keypad interface and an app-owned two-row bottom action bar. It implements
a virtual Pokéwalker EEPROM and experimental
HeartGold / SoulSilver slave-side communication over the KYF37 infrared hardware.
It does not require a game ROM or original Pokéwalker firmware in the APK.

## Implemented

- D-pad, OK, Clear, 1–8 shortcuts and F1–F4 actions.
- Walking screen, game-provided 2-bit animated Pokémon graphics, trainer card,
  collected Pokémon/items, basic radar and dowsing minigames.
- Foreground service using the real Android step-counter sensor, 20 steps per
  watt, daily history and limits. No artificial real-save steps or automatic boot
  service. If the sensor is unavailable, counting stops with an explicit status.
- Separate disposable demo save: F3 opens settings; F3 again switches mode;
  `*` runs a synthetic game transfer. OK on Walk adds demo steps only.
- Raw SIR 115200 8N1, XOR 0xAA, seeded/byte-swapped checksum, FA/F8 session
  establishment, session filtering, EEPROM reads, direct and LZ10 compressed
  writes, identity, clock staging, walk start/end, ping and disconnect.
- App-private 64 KiB saves through Android AtomicFile. Write acknowledgments
  follow successful durable saves. Malformed or unsupported commands fail
  without changing EEPROM. No phone partition paths are used.
- ARMv7 root helper that acquires a real kernel UART lease or kflcd arbitration, opens
  ttyHSL3, enables the existing kernel SIR mode, holds the irdasd power-control
  descriptor, then restores settings and releases ownership at session end.
  The companion verifies the app's UID through kernel peer credentials; the app
  verifies that the companion runs as root. Hardware opens only after Connect.
  A conventional `su` launch is a fallback on compatible rooted ROMs.
- A file-owned kernel UART lease that releases on process exit. Failed FeliCa
  opens time out and stop leaving the UART reserved. This requires the new
  matching kernel, now installed and tested for lease acquisition/release.

## Read a real Pokéwalker

The information and EEPROM-backup actions remain read-only and separate from
Connect to game. They use normal discovery/session, identity, EEPROM reads and
disconnect; the other four advanced actions are described above. Captures are
stored under private files/real-pokewalker and exported with the native document
picker. Existing captures and the app's virtual save are preserved on failure.
Non-Latin trainer-name characters may appear as question marks.

## Limits and next validation

**A successful build or simulator exchange does not establish real-game
compatibility.** Optical signaling, turnaround deadlines, self-echo behavior,
FeliCa coexistence and successful pair / send / return transactions still require
further hardware testing. Installed UART access and both root launch paths passed
phone-side checks; a peer was unavailable.
The owner's target is a 3DS running HeartGold/SoulSilver with RtcPwalker; aim at
the 3DS's rear IR window, rather than the cartridge.
The helper refuses access if arbitration fails; it does not kill FeliCa services,
change permissions, disable SELinux, or patch the live kernel.

The minigames are an initial playable adaptation, not a verified reproduction of
all original battle, reward, friendship and event-log algorithms. Peer-to-peer
walker play, event distribution, factory enrollment, special routes,
mid-stroll save restoration from hardware, and original firmware execution are
not implemented. Unsupported commands do not receive fabricated success replies.
The game-requested reset command changes only the app's virtual EEPROM and first
keeps a copy of the previous virtual save; it never formats phone userdata.
The app registered with the hardware step counter and received its initial event;
actual walking increments and closed-lid behavior remain unverified.

The installed matching ROM routes F1–F4 to the app; 12 phone key-event checks
passed. Reproducible source patches
are in `dist/kyf37-android10-corner-keys.patch` and the corresponding Android 11
file. Numeric shortcuts and the D-pad remain available. The Android 11 entry is
staged after other key-policy generators by `stage-android11-flip-walker.py`.
The app and companion are included in the candidate image. Framework/services
must be deployed only as a matching
validated ROM image set, never as isolated live replacements.

## Build and verify offline

All builds go through the mandatory workspace lock:

```sh
bash device-inspection/build-locked.sh "$PWD/flip_walker/final-build.log" \
  --script "$PWD/flip_walker/tools/build-both.sh"
```

`templates/` and `native/` are the source of truth. `tools/stage.py` recreates
`app/` on every build, so edits are repeatable. The local AOSP JDK, clang, bionic,
NDK libraries and public AOSP test signing credentials are used; the owner's
private recovery signing key is never accessed. SDK tools are prepared through
the existing `flip_pokedex/tools/prepare_sdk.py` cache.

Outputs: `dist/FlipWalker.apk` for ARMv7 and `dist/FlipWalker-emulator.apk` with
an additional x86_64 helper. Signatures and APK metadata are verified by the build.
The helper supports `--self-test` (no hardware), `--probe` (driver setup and
cleanup without optical transmission), `--session` and a UID-restricted `--broker`.

`tools/test-emulator.py` is hardcoded to **emulator-5582** and verifies
`ro.kernel.qemu=1` before installing. It never enumerates or selects physical
devices. Current checks use the isolated emulator at port 5582 with the local flip-pokedex AVD; only Flip Walker test files are changed. The physical phone is never selected by these emulator scripts. See `VALIDATION.md` for actual outcomes.

To regenerate corner-key patches without applying them:

```sh
python3 flip_walker/tools/prepare_rom_key_patch.py
python3 flip_walker/tools/prepare_rom_key_patch.py --tree native/kyf37-android11
```

For a later authorized ROM source integration, use `build-locked.sh --script
flip_walker/tools/apply-rom-keys.sh --tree <explicit tree>`, after other native-key
generators. This only patches sources; it never installs or reboots.

## References

- [Dmitry.GR PokéWalker research](https://dmitry.gr/?r=05.Projects&proj=28.%20pokewalker)
- [reverse-pokewalker](https://github.com/mamba2410/reverse-pokewalker), especially
  the packet-format algorithm and published FA/F8 checksum examples.
- [RtcPwalker](https://github.com/francesco265/RtcPwalker), an experimental
  game-side 3DS IR patch. It is a reference, not an Android dependency.
- [picowalker](https://github.com/mamba2410/picowalker), a hardware recreation.
  Its current core is supplied as an RP2350 archive rather than portable source;
  that archive is not used or bundled in this app.

- [pwalkerHax](https://github.com/francesco265/pwalkerHax), master-side operations,
  event structures, complete catalogs and temporary RAM payloads.

To reproduce the generated catalogs/payloads, place that checkout at
`flip_walker/references/pwalkerHax`, pinned to
`bed237a67550ff5eda2f78a0959b58dfad725416`. The build runs the idempotent
`tools/modern-ds/` integration scripts. Both the generated Java and their
source adapters are retained.

The Spanish reference files can be restored offline from the checked-in cache,
or fetched at the pinned commit with hash verification:

```sh
python3 flip_walker/tools/localization/fetch-reference.py
```

Other local reference checkouts are kept under `third-party/pokewalker-research/`.
See `THIRD_PARTY.md` and `IR-EVIDENCE.md` for provenance and hardware evidence.
