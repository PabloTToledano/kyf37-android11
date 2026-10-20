#!/usr/bin/env python3
"""Keep quick physical presses visible for a minimum amount of emulated time."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'templates/src/org/kyf37/walker/EmulatedButtons.java'
p.write_text('''package org.kyf37.walker;

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
''')
p=R/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text()
if 'private final EmulatedButtons buttons' not in s:s=s.replace('    private volatile int keys;', '    private volatile int keys;\n    private final EmulatedButtons buttons = new EmulatedButtons();')
s=s.replace('        keys = 0;\n        final int generation', '        keys = 0; buttons.clear();\n        final int generation')
s=s.replace('        release.removeCallbacksAndMessages(null);','        buttons.clear();')
if 'buttons.sample(slice)' not in s:s=s.replace('                if (PwCore.run(slice, keys)', '                keys = buttons.sample(slice);\n                if (PwCore.run(slice, keys)')
s=s.replace('    // the firmware samples its buttons slowly; hold every press at least 120 ms so quick taps register\n    private final Handler release = new Handler(Looper.getMainLooper());', '    // Minimum hold is counted by EmulatedButtons in emulated time, never UI wall time.')
s=s.replace('keys |= k; view.invalidate(); return true;', 'buttons.press(k); view.invalidate(); return true;')
s=s.replace('        long held = e.getEventTime() - e.getDownTime();\n        release.postDelayed(() -> { keys &= ~k; view.invalidate(); }, Math.max(0, 120 - held));', '        buttons.release(k); view.invalidate();')
p.write_text(s)
