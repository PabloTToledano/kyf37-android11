package org.kyf37.walker;

/** Real Pokéwalker firmware running on the vendored Powar H8 core (libpwcore.so, GPL-3.0).
 *  One instance per process; all calls from the emulation thread. */
final class PwCore {
    static final int W = 96, H = 64, KEY_ENTER = 1, KEY_LEFT = 4, KEY_RIGHT = 16;
    static { System.loadLibrary("pwcore"); }
    static native boolean init(byte[] rom, byte[] eeprom);
    /** Emulate ms milliseconds. Returns 0, or -1 if the CPU halted. */
    static native int run(int ms, int keys);
    /** Fills 96x64 shades 0..3; true when the LCD changed. */
    static native boolean frame(byte[] out);
    /** Full 64 KiB EEPROM copy when the firmware changed it since the last call, else null. */
    static native byte[] eepromIfDirty();
    static native int pc();
    static native boolean irEnabled();
    static native void irPush(byte[] burst);
    static native byte[] irPop();
    static native void walk(int steps);
    static native int walkPending();
    static native int ramRead(int addr);
    static native void ramWrite(int addr, int value);
    /** Run a firmware routine to completion (0x1F40 = add watts, r0 = amount). 0 on success. */
    static native int call(int addr, int r0);

    // Firmware RAM (same layout pwalkerHax uses on real walkers): live health block
    static final int RAM_TOTAL_STEPS = 0xF780, RAM_TODAY_STEPS = 0xF784, RAM_TODAY_LIVE = 0xF79C, RAM_WATTS = 0xF78E;
    static final int FW_ADD_WATTS = 0x1F40;
    static long u32(int a) { long v = 0; for (int i = 0; i < 4; i++) v = v << 8 | ramRead(a + i); return v; }
    static void put32(int a, long v) { for (int i = 0; i < 4; i++) ramWrite(a + i, (int) (v >>> (24 - 8 * i)) & 255); }
    static int watts() { return ramRead(RAM_WATTS) << 8 | ramRead(RAM_WATTS + 1); }
    /** Steps the way walking adds them: today/lifetime counters plus the earned watts (1 per 20);
     *  the firmware's add-watts routine then saves the whole health block to EEPROM. */
    static boolean addSteps(int n) {
        long today = Math.min(99999, u32(RAM_TODAY_LIVE) + n);
        put32(RAM_TODAY_LIVE, today); put32(RAM_TODAY_STEPS, today);
        put32(RAM_TOTAL_STEPS, Math.min(9999999, u32(RAM_TOTAL_STEPS) + n));
        return call(FW_ADD_WATTS, n / 20) == 0;
    }
    static boolean addWatts(int n) { return call(FW_ADD_WATTS, Math.min(n, 9999 - Math.min(9999, watts()))) == 0; }
    private PwCore() {}
}
