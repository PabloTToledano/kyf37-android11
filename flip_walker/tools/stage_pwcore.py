#!/usr/bin/env python3
"""Rerunnable: add the PW_LIBRARY build to the vendored Powar core (native/pwcore).

Library mode drops SDL, sockets, file I/O and console logging; IR goes through the
pwcore_glue.inc queues and the RTC gets a readable flag register. Every edit asserts
its anchor, and already-staged files are left untouched.
"""
from pathlib import Path

core = Path(__file__).resolve().parents[1] / 'native/pwcore'


def sub(text, old, new, what):
    assert old in text, f'anchor not found: {what}'
    return text.replace(old, new, 1)


def guard_funcs(text, first, last, what):
    """Wrap everything from `first` to the end of the function starting at `last`."""
    assert first in text and last in text, f'anchor not found: {what}'
    i = text.index(first)
    k = text.index('\n}\n', text.index(last, i)) + 3
    return text[:i] + '#ifndef PW_LIBRARY\n' + text[i:k] + '#endif // PW_LIBRARY\n' + text[k:]


def stage_main(c):
    # the CPU SLEEP handler is a global `sleep`; in a shared library libc's sleep() interposes it
    c = sub(c, '#include <stdlib.h>\n', '#include <stdlib.h>\n#define sleep pw_cpu_sleep\n', 'stdlib')
    c = sub(c, '#include <SDL2/SDL.h>\n', '#ifndef PW_LIBRARY\n#include <SDL2/SDL.h>\n#endif\n#include <stddef.h>\n', 'SDL include')
    c = sub(c, 'static SDL_Window* gWindow = NULL;\nstatic SDL_Renderer* renderer;\nstatic SDL_Texture* sdlTexture;\n',
            '#ifndef PW_LIBRARY\nstatic SDL_Window* gWindow = NULL;\nstatic SDL_Renderer* renderer;\nstatic SDL_Texture* sdlTexture;\n#endif\n',
            'SDL globals')
    # Timer B1: TCB1 reads the counter (the stub returned TMB1); ticking lives in pwcore_glue.inc
    c = sub(c, '''static uint8_t tb1_get_tcb1(pw_context_t *ctx) {
    return ctx->tmb1;''', '''static uint8_t tb1_get_tcb1(pw_context_t *ctx) {
    return ctx->tcb1; // tb1 counter read''', 'tb1 counter read')
    c = sub(c, '#include "main.h"\n', '''#include "main.h"

// PW_LIBRARY_STAGED
#ifdef PW_LIBRARY
#define printf(...) ((void)0)
#define puts(x) ((void)0)
void pwlib_ir_tx(const uint8_t *data, int len);
int pwlib_ir_rx(uint8_t *data, int max);
#endif
''', 'main.h include')
    c = guard_funcs(c, 'static int sdl_init()', 'static void sdl_draw(', 'SDL video')
    c = guard_funcs(c, 'static enum keys sdl_scancode_to_key(', 'static uint8_t sdl_poll(', 'SDL input')
    c = sub(c, '''    // load ROM and EEPROM from file
    FILE *romf''', '''#ifndef PW_LIBRARY
    // load ROM and EEPROM from file
    FILE *romf''', 'pw_init files')
    c = sub(c, '''    fread(ctx->eeprom_data, 1, 1 << 16, eepromf);
    fclose(eepromf);
''', '''    fread(ctx->eeprom_data, 1, 1 << 16, eepromf);
    fclose(eepromf);
#endif
''', 'pw_init files end')
    # sockets -> queues
    c = sub(c, '#ifndef __EMSCRIPTEN__\nextern int close(int);', '#if !defined(__EMSCRIPTEN__) && !defined(PW_LIBRARY)\nextern int close(int);', 'close decl')
    for fn in ('static void ir_open(pw_context_t *ctx) {', 'static void ir_flush_tx(pw_context_t *ctx) {',
               'static void ir_update(pw_context_t *ctx, int states) {'):
        assert fn in c, f'anchor not found: {fn}'
        i = c.index(fn); k = c.index('\n}\n', i)
        c = c[:i] + c[i:k].replace('#ifndef __EMSCRIPTEN__', '#if !defined(__EMSCRIPTEN__) && !defined(PW_LIBRARY)') + c[k:]
    c = sub(c, '''    ctx->ir_tx_len = 0;
}''', '''#ifdef PW_LIBRARY
    if (ctx->ir_tx_len > 0) pwlib_ir_tx(ctx->ir_tx, ctx->ir_tx_len);
#endif
    ctx->ir_tx_len = 0;
}''', 'ir tx flush')
    c = sub(c, '''    if (ctx->ir_rx_pos < ctx->ir_rx_len) {
        ctx->ir_rx_wait -= states;''', '''#ifdef PW_LIBRARY
    if (ctx->ir_rx_pos >= ctx->ir_rx_len) {
        int n = pwlib_ir_rx(ctx->ir_rx, sizeof(ctx->ir_rx));
        if (n > 0 && (ctx->scr & (1 << 4))) { // RE off: burst is lost, as on real hardware
            ctx->ir_rx_len = n; ctx->ir_rx_pos = 0; ctx->ir_rx_wait = 8000;
        }
    }
#endif
    if (ctx->ir_rx_pos < ctx->ir_rx_len) {
        ctx->ir_rx_wait -= states;''', 'ir rx queue')
    # desktop-only persistence and main loop
    i = c.index('static void eeprom_save(pw_context_t *ctx)')
    c = c[:i] + '#ifndef PW_LIBRARY\n' + c[i:]
    c += '#endif // PW_LIBRARY\n\n#ifdef PW_LIBRARY\n#include "pwcore_glue.inc"\n#endif\n'
    return c


main = core / 'main.c'
text = main.read_text()
if 'PW_LIBRARY_STAGED' not in text:
    main.write_text(stage_main(text))

# RTC: readable flag register (read flags, write 0 to clear), ticked by pwcore_glue.inc
h = core / 'rtc.h'; ht = h.read_text()
if 'uint8_t flg;' not in ht:
    h.write_text(sub(ht, '    uint8_t pending_ints;', '    uint8_t pending_ints;\n    uint8_t flg;', 'rtc_t'))
r = core / 'rtc.c'; rt = r.read_text()
if 'rtc->flg &= byte' not in rt:
    rt = sub(rt, 'void rtc_set_flg(rtc_t *rtc, uint8_t byte) {\n', 'void rtc_set_flg(rtc_t *rtc, uint8_t byte) {\n    rtc->flg &= byte;\n', 'set_flg')
    rt = sub(rt, 'uint8_t rtc_get_flg(rtc_t *rtc) {\n    uint8_t res = 0;', 'uint8_t rtc_get_flg(rtc_t *rtc) {\n    uint8_t res = rtc->flg;', 'get_flg')
    r.write_text(rt)

# Accelerometer (BMA150): give it X/Y/Z samples (10-bit, 256 LSB/g) set by the walking generator
ah = core / 'accel.h'; at = ah.read_text()
if 'int16_t x, y, z;' not in at:
    ah.write_text(sub(at, '    uint8_t next_read;\n', '    uint8_t next_read;\n    int16_t x, y, z;\n', 'accel_t'))
ac = core / 'accel.c'; act = ac.read_text()
if 'AXIS_LO(' not in act:
    act = sub(act, 'static uint8_t internal_read(accel_t *accel, uint8_t addr) {\n    uint8_t res = 0;\n    switch(addr) {\n',
        '''#define AXIS_LO(v) ((uint8_t)((((v) & 3) << 6) | 1)) /* acc<1:0> + new_data */
#define AXIS_HI(v) ((uint8_t)(((v) >> 2) & 0xFF))
static uint8_t internal_read(accel_t *accel, uint8_t addr) {
    uint8_t res = 0;
    switch(addr) {
        case ACC_X_NEW_ADDR: return AXIS_LO(accel->x);
        case ACC_X_ADDR:     return AXIS_HI(accel->x);
        case ACC_Y_NEW_ADDR: return AXIS_LO(accel->y);
        case ACC_Y_ADDR:     return AXIS_HI(accel->y);
        case ACC_Z_NEW_ADDR: return AXIS_LO(accel->z);
        case ACC_Z_ADDR:     return AXIS_HI(accel->z);
''', 'accel read')
    act = sub(act, '''        case VERSION_ADDR:
        case ACC_X_NEW_ADDR:
        case ACC_X_ADDR:
        case ACC_Y_NEW_ADDR:
        case ACC_Y_ADDR:
        case ACC_Z_NEW_ADDR:
        case ACC_Z_ADDR:
''', '''        case VERSION_ADDR:
''', 'old axis cases')
    ac.write_text(act)
print('pwcore staged for PW_LIBRARY')
