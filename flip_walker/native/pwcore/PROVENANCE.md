# pwcore — Pokéwalker H8/38606 emulator core

Vendored from Powar (https://github.com/UnrealPowerz/powar, GPL-3.0) at commit
df3ca7e, plus `powar-fixes.patch` (recorded from the working tree before vendoring):

- SCI3/IrDA UART model with byte pacing and read-then-clear SSR flag semantics
  (the earlier write-to-clear race dropped received IR bytes)
- OR.L / XOR.L / AND.L ERs,ERd; MOV.L @ERs+ / @-ERd / @aa:24 forms
- EEPROM persistence, IR debug/trace hooks

`tools/stage_pwcore.py` adds the PW_LIBRARY build (no SDL, no sockets, in-memory IR
queues and a C API in `pwcore.h`) used by the app's full-emulation mode. No ROM is
bundled; the user's own dump is loaded at runtime.
