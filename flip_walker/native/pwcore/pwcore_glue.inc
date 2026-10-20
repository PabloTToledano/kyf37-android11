/* Library glue, compiled inside main.c (PW_LIBRARY) so it can reach the core's statics. */
#include "pwcore.h"
#include <stdatomic.h>
static _Atomic unsigned diagnostic_pc;

#define PWQ 8
static pw_context_t g_ctx;
static int g_redraw, g_ready;
static uint8_t g_rxq[PWQ][263], g_txq[PWQ][263];
static int g_rxlen[PWQ], g_txlen[PWQ], g_rxh, g_rxt, g_txh, g_txt;
static uint8_t g_eeprom_seen[1 << 16];

void pwlib_ir_tx(const uint8_t *data, int len) {
    if (len > 263) len = 263;
    int next = (g_txt + 1) % PWQ;
    if (next == g_txh) g_txh = (g_txh + 1) % PWQ; /* drop oldest */
    memcpy(g_txq[g_txt], data, len); g_txlen[g_txt] = len; g_txt = next;
}
int pwlib_ir_rx(uint8_t *data, int max) {
    if (g_rxh == g_rxt) return 0;
    int n = g_rxlen[g_rxh] < max ? g_rxlen[g_rxh] : max;
    memcpy(data, g_rxq[g_rxh], n); g_rxh = (g_rxh + 1) % PWQ;
    return n;
}
int pwcore_pc(void) { return (int)atomic_load(&diagnostic_pc); }
int pwcore_ir_enabled(void) { return g_ready && (g_ctx.scr & 0x30) != 0; }

void pwcore_ir_push(const uint8_t *data, int len) {
    if (len <= 0) return;
    if (len > 263) len = 263;
    int next = (g_rxt + 1) % PWQ;
    if (next == g_rxh) return; /* full: real IR would lose it too */
    memcpy(g_rxq[g_rxt], data, len); g_rxlen[g_rxt] = len; g_rxt = next;
}
int pwcore_ir_pop(uint8_t *out, int max) {
    if (g_txh == g_txt) return 0;
    int n = g_txlen[g_txh] < max ? g_txlen[g_txh] : max;
    memcpy(out, g_txq[g_txh], n); g_txh = (g_txh + 1) % PWQ;
    return n;
}

int pwcore_init(const uint8_t *rom, int rom_len, const uint8_t *eeprom) {
    if (rom_len <= 0 || rom_len > (1 << 16)) return -1;
    memset(&g_ctx, 0, sizeof(g_ctx));
    memset(g_ctx.rom, 0xFF, sizeof(g_ctx.rom));
    memcpy(g_ctx.rom, rom, rom_len);
    memcpy(g_ctx.eeprom_data, eeprom, 1 << 16);
    memcpy(g_eeprom_seen, eeprom, 1 << 16);
    g_rxh = g_rxt = g_txh = g_txt = 0;
    halt = 0;
    pw_init(&g_ctx, &g_redraw);
    g_redraw = 1;
    g_ready = 1;
    return 0;
}

/* RTC in emulated time, seeded from the host clock when the firmware starts it. Sets RTCFLG
 * bits and, for those enabled in RTCCR2, pending interrupts (0.25 s .. 1 week vectors). */
static long g_rtc_states;
static void rtc_tick(int states) {
    rtc_t *r = &g_ctx.rtc;
    if (!(r->rtccr1 & (1 << RTCCR1_RUN_BIT))) { g_rtc_states = 0; return; }
    g_rtc_states += states;
    const long quarter = STATES_PER_SECOND / 4;
    static unsigned quarters;
    while (g_rtc_states >= quarter) {
        g_rtc_states -= quarter; quarters++;
        uint8_t bits = 1 << 0;
        if (quarters % 2 == 0) bits |= 1 << 1;
        if (quarters % 4 == 0) {
            struct tm before = r->time;
            r->time.tm_sec++;
            time_t t = mktime(&r->time);
            r->time = *localtime(&t);
            bits |= 1 << 2;
            if (r->time.tm_min != before.tm_min) bits |= 1 << 3;
            if (r->time.tm_hour != before.tm_hour) bits |= 1 << 4;
            if (r->time.tm_mday != before.tm_mday) bits |= 1 << 5;
            if (r->time.tm_wday != before.tm_wday && r->time.tm_wday == 0) bits |= 1 << 6;
        }
        r->flg |= bits;
        r->pending_ints |= bits & r->rtccr2;
    }
}

/* Timer B1 (8-bit up counter, overflow -> vector 33). The firmware runs it from the 32.768 kHz
 * watch clock /128 with reload 0xF8: a 32 Hz tick that samples the accelerometer. */
static long g_tb1_states;
static void tb1_tick(int states) {
    uint8_t m = g_ctx.tmb1;
    if (!(m & 0x40)) { g_tb1_states = 0; return; }            /* counter stopped */
    static const long div[8] = {8192, 4096, 2048, 512, 256, 128, 32, 0};
    long per = (m & 7) == 7 ? STATES_PER_SECOND / 256 : div[m & 7];
    g_tb1_states += states;

    while (g_tb1_states >= per) {
        g_tb1_states -= per;
        if (++g_ctx.tcb1 == 0) {                                /* overflow */
            if (m & 0x80) g_ctx.tcb1 = g_ctx.tlb1;              /* auto-reload */
            g_ctx.irr2 |= 1 << 2;
        }
    }
}

/* Walking motion for the accelerometer: gravity on Z plus a 0.5 s swing per step, the way a
 * walker on a belt moves. The firmware's own pedometer turns it into steps, watts and events. */
#include <math.h>
static long g_walk_pending, g_walk_phase;
void pwcore_walk(int steps) { if (steps > 0) g_walk_pending += steps; }
int pwcore_walk_pending(void) { return (int)g_walk_pending; }
static void accel_tick(int states) {
    accel_t *a = &g_ctx.accel;
    const long period = STATES_PER_SECOND / 2;
    if (g_walk_pending <= 0) { a->x = 0; a->y = 0; a->z = 256; g_walk_phase = 0; return; }
    g_walk_phase += states;
    if (g_walk_phase >= period) { g_walk_phase -= period; g_walk_pending--; }
    if (g_walk_phase < states) g_ctx.irr1 |= 2; /* motion IRQ: BMA150 INT pin on IRQ1, once per step */
    double s = sin(2 * M_PI * (double)g_walk_phase / period);
    a->z = (int16_t)(256 + 170 * s);
    a->x = (int16_t)(70 * s);
    a->y = (int16_t)(40 * cos(2 * M_PI * (double)g_walk_phase / period));
}

int pwcore_run(int ms, int keys) {
    if (!g_ready || halt) return -1;
    g_ctx.keys_pressed = (uint8_t)keys;
    portb_update(&g_ctx.portb, g_ctx.keys_pressed);
    long target = (long)STATES_PER_SECOND * ms / 1000;
    long done = 0;
    while (done < target && !halt) {
        int old = g_ctx.states;

        pw_step(&g_ctx);
        int d = g_ctx.states - old;
        if (d <= 0) { atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed); halt = 1; return -1; } /* unsupported opcode must not hang JNI */

        tmrw_update(&g_ctx, d);

        ir_update(&g_ctx, d);

        rtc_tick(d);

        accel_tick(d);

        tb1_tick(d);

        if (g_ctx.int_enabled && !get_ccr_bit(&g_ctx, CCR_I) && (g_ctx.irr1 & g_ctx.ienr1 & 2)) {
            g_ctx.irr1 &= ~2;
            interrupt(&g_ctx, INT_IRQ1);
        }
        if (g_ctx.int_enabled && !get_ccr_bit(&g_ctx, CCR_I) && (g_ctx.irr2 & g_ctx.ienr2 & (1 << 2))) {
            g_ctx.irr2 &= ~(1 << 2);
            interrupt(&g_ctx, INT_TIMER_B1);
        }
        if (g_ctx.int_enabled && !get_ccr_bit(&g_ctx, CCR_I)) {
            int v = rtc_poll_int(&g_ctx.rtc);
            if (v >= 0) interrupt(&g_ctx, v);
        }
        if (g_ctx.int_enabled && !get_ccr_bit(&g_ctx, CCR_I) && (g_ctx.tsrw & g_ctx.tierw & 0x8f))
            interrupt(&g_ctx, INT_TIMER_W);
        done += d;
        if (g_ctx.states > 1 << 28) g_ctx.states = 0;
    }

    atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed);
    return halt ? -1 : 0;
}

int pwcore_frame(uint8_t *out) {
    lcd_t *lcd = &g_ctx.lcd;
    for (int y = 0; y < PWCORE_H; y++)
        for (int x = 0; x < PWCORE_W; x++) {
            int yo = y + lcd->display_start_line;
            int pg = (yo / 8) % LCD_NUM_PAGES, b = yo % 8;
            uint16_t v = (lcd->ram[pg][x * 2] << 8) | lcd->ram[pg][x * 2 + 1];
            v >>= b;
            out[y * PWCORE_W + x] = ((v & 0x100) >> 7) | (v & 1);
        }
    int r = g_redraw; g_redraw = 0;
    return r;
}

const uint8_t *pwcore_eeprom(void) { return g_ctx.eeprom_data; }

int pwcore_eeprom_dirty(void) {
    if (!memcmp(g_eeprom_seen, g_ctx.eeprom_data, sizeof(g_eeprom_seen))) return 0;
    memcpy(g_eeprom_seen, g_ctx.eeprom_data, sizeof(g_eeprom_seen));
    return 1;
}

/* Direct RAM access (F780-FF7F) for app-side tools such as adding steps or watts. */
int pwcore_ram_read(int addr) { return (addr >= RAM_start && addr < RAM_end) ? g_ctx.ram[addr - RAM_start] : -1; }
void pwcore_ram_write(int addr, int val) { if (addr >= RAM_start && addr < RAM_end) g_ctx.ram[addr - RAM_start] = (uint8_t)val; }
void pwcore_eeprom_write(int addr, int val) { if (addr >= 0 && addr < 65536) g_ctx.eeprom_data[addr] = (uint8_t)val; }

/* Run a firmware subroutine to completion, as pwalkerHax's payloads do on a real walker
 * (e.g. 0x1F40 = add watts, R0 = amount). CPU state is saved and restored around the call;
 * a sentinel return address marks the end. Returns 0, or -1 if it did not return. */
#define PW_CALL_SENTINEL 0x0100
int pwcore_call(int addr, int r0) {
    if (!g_ready || halt) return -1;
    /* save only the CPU context; peripherals (EEPROM bus, LCD, timers) keep running normally */
    uint16_t regs[16]; memcpy(regs, g_ctx.regs, sizeof regs);
    uint8_t ccr = g_ctx.ccr; uint16_t ip = g_ctx.ip, pf = g_ctx.instr_prefetch;
    int ie = g_ctx.int_enabled;
    g_ctx.int_enabled = 0;
    write_reg16(&g_ctx, 0, (uint16_t)r0);
    pushw(&g_ctx, PW_CALL_SENTINEL);
    g_ctx.ip = (uint16_t)addr;
    g_ctx.instr_prefetch = read16(&g_ctx, g_ctx.ip);
    int ok = -1;
    for (long n = 0; n < 2000000 && !halt; n++) {
        if (g_ctx.ip == PW_CALL_SENTINEL) { ok = 0; break; }
        pw_step(&g_ctx);
    }
    memcpy(g_ctx.regs, regs, sizeof regs); /* restores SP too, dropping anything left on the stack */
    g_ctx.ccr = ccr; g_ctx.ip = ip; g_ctx.instr_prefetch = pf; g_ctx.int_enabled = ie;
    return ok;
}
