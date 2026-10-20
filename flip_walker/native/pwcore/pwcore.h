/* Pokéwalker full-emulation core (Powar, GPL-3.0). Single instance per process. */
#pragma once
#include <stdint.h>

#define PWCORE_W 96
#define PWCORE_H 64
enum { PWCORE_KEY_ENTER = 1, PWCORE_KEY_LEFT = 4, PWCORE_KEY_RIGHT = 16 };

/* rom: 48 KiB walker ROM dump; eeprom: 64 KiB. Returns 0 on success. */
int pwcore_init(const uint8_t *rom, int rom_len, const uint8_t *eeprom);
/* Emulate `ms` milliseconds with the given key mask. Returns 0, or -1 if the CPU halted. */
int pwcore_run(int ms, int keys);
/* 96x64 pixels, shade 0 (light) .. 3 (dark). Returns 1 if the LCD changed since last call. */
int pwcore_frame(uint8_t *out);
const uint8_t *pwcore_eeprom(void);
/* 1 once the firmware changed EEPROM since the last call. */
int pwcore_eeprom_dirty(void);
/* Infrared: deliver one received burst / take one burst the walker transmitted. */
/* Firmware SCI enable state, including receive-only connection attempts. */
int pwcore_pc(void);
int pwcore_ir_enabled(void);
void pwcore_ir_push(const uint8_t *data, int len);
int pwcore_ir_pop(uint8_t *out, int max);
/* Queue `steps` of emulated walking (fed to the accelerometer at ~2 steps/s). */
void pwcore_walk(int steps);
int pwcore_walk_pending(void);
int pwcore_ram_read(int addr);
void pwcore_ram_write(int addr, int val);
void pwcore_eeprom_write(int addr, int val);
/* Call a firmware routine (e.g. 0x1F40 add watts with r0 = amount). 0 on success. */
int pwcore_call(int addr, int r0);
