package org.kyf37.walker;

/** Button hold measured in firmware time, even when the host thread stalls. */
final class EmulatedButtons {
    private int held;
    private final int[] remaining = new int[8];
    synchronized void press(int bits) {
        int fresh = bits & ~held;
        held |= bits;
        for (int i = 0; i < 8; i++) if ((fresh & (1 << i)) != 0) remaining[i] = 200;
    }
    synchronized void release(int bits) { held &= ~bits; }
    synchronized void clear() { held = 0; java.util.Arrays.fill(remaining, 0); }
    synchronized int sample(int milliseconds) {
        int bits = held;
        for (int i = 0; i < 8; i++) {
            if (remaining[i] > 0) bits |= 1 << i;
            remaining[i] = Math.max(0, remaining[i] - milliseconds);
        }
        return bits;
    }
}
