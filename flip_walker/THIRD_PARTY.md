# Provenance

Flip Walker's Java and C code is newly written for this project. No original
Pokémon ROM, Pokéwalker firmware, ripped image pack, proprietary Kyocera library,
or picowalker binary core is included in the APK. Pokémon and route graphics are
expected to arrive from the user's game over its normal transfer protocol. Demo
mode draws a simple geometric placeholder in code.

The protocol implementation follows published interoperability research:

- Dmitry.GR, “PokéWalker hacking”: packet commands, virtual EEPROM map, LZ10 and
  walk staging. This is a reference; no downloaded firmware or exploit is used.
- mamba2410/reverse-pokewalker (MIT): packet-format checksum description and
  published handshake examples are independent test vectors. A local research
  checkout retains its original LICENSE.md.
- francesco265/RtcPwalker (GPL-3.0): read as a game-side interoperability
  reference. Its source, patch output and executable are not compiled or copied
  into this APK. The research checkout retains its original LICENSE.
- mamba2410/picowalker (BSD-3-Clause): read for architecture and IR-driver timing
  context. Its RP2350 core archive and graphics are not used. The research
  checkout retains its original LICENSE.md.
- francesco265/pwalkerHax (GPL-3.0), commit
  `bed237a67550ff5eda2f78a0959b58dfad725416`: master-side operations,
  catalogs and H8 RAM payloads adapted for Java in WalkerTools/WalkerCatalog.
  Payloads are attributed upstream to Dmitry Grinberg's Pokéwalker research.
  These portions and their combined app are provided under GPL-3.0; the full
  license is in LICENSE and bundled in the APK assets and dist/licenses.
  Rerun tools/modern-ds/generate.py from the pinned research checkout to
  reproduce the catalogs/payloads. No Pokéwalker ROM or Nintendo sprite/font
  graphics are bundled. Gift names use our original 5x7 font. The Pokémon
  event animation follows the reference's temporary blank/filled frames.
- PokeAPI/pokeapi (BSD-3-Clause), commit
  `5ee47a9a9c1229632ec4b473a9c1c53026e005dd`: Spanish item, move and ability
  names, and generation-four item index mapping. Language 7 is es/es (Spain),
  distinct from language 14 es-419/mx. CSV files and hashes are retained under
  references/pokeapi-localization. The copyright/license is included as
  assets/PokeAPI-LICENSE.txt and dist/licenses/PokeAPI-LICENSE.txt.
- Pusty/PokewalkerUtils: additional interoperability reference and independent
  captured packet examples. Its game-side return command is 0x40 (reply 0x42),
  corroborating reverse-pokewalker's return-flow documentation. No Python source
  or image assets from that repository are bundled in the app.

The raw helper is compiled against local AOSP/Android bionic and compiler
runtime static libraries. Their upstream notices apply to the binary. The build
collects the available bionic/compiler/GCC notice files in `dist/licenses/`.
Public AOSP test credentials sign the development APK; they are not the owner's
recovery signing key. Do not distribute this development build as a production
release without selecting proper app signing credentials and reviewing notices.

Pokémon and Pokéwalker are names of their respective rights holders. This is an
unofficial interoperability project.
