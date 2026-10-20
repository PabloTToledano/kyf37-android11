#!/usr/bin/env python3
"""Rerunnable: keep emulation in the app task and open IR for receiver-first reconnects."""
from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]
def patch(path,old,new):
 p=R/path;s=p.read_text()
 if new in s:return
 if s.count(old)!=1:raise SystemExit(str(path)+': anchor mismatch')
 p.write_text(s.replace(old,new,1))
p=R/'templates/AndroidManifest.xml';s=p.read_text();s=s.replace(' android:taskAffinity="org.kyf37.walker.emulated"','').replace(' android:launchMode="singleTask"','');p.write_text(s)
# Older integration scripts must also generate the same internal activity.
p=R/'tools/fix_full_emulation.py';s=p.read_text().replace(' android:taskAffinity="org.kyf37.walker.emulated"','').replace(' android:launchMode="singleTask"','').replace('android:exported="true" android:theme="@android:style/Theme.Material.NoActionBar"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>','android:exported="false" android:theme="@android:style/Theme.Material.NoActionBar"></activity>');p.write_text(s)
patch('native/pwcore/pwcore.h','void pwcore_ir_push(', '/* Firmware SCI enable state, including receive-only connection attempts. */\nint pwcore_ir_enabled(void);\nvoid pwcore_ir_push(')
patch('native/pwcore/pwcore_glue.inc','void pwcore_ir_push(', 'int pwcore_ir_enabled(void) { return g_ready && (g_ctx.scr & 0x30) != 0; }\n\nvoid pwcore_ir_push(')
patch('templates/src/org/kyf37/walker/PwCore.java','    static native void irPush(', '    static native boolean irEnabled();\n    static native void irPush(')
patch('native/pwcore/pwcore_jni.c','JNIEXPORT void JNICALL FN(irPush)', 'JNIEXPORT jboolean JNICALL FN(irEnabled)(JNIEnv *e, jclass c) {\n    (void)e; (void)c; return pwcore_ir_enabled() ? JNI_TRUE : JNI_FALSE;\n}\n\nJNIEXPORT void JNICALL FN(irPush)')
p=R/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text()
a=s.find('                while (pc == null && (burst = PwCore.irPop()) != null) {');b=s.index('                byte[] dirty =',max(a,0))
new='''                // Follow the firmware's receiver as well as its transmitter. A paired
                // walker may listen first; waiting for a TX burst deadlocks that reconnect.
                boolean irEnabled = pc == null && PwCore.irEnabled();
                if (pc == null) {
                    try {
                        if (ir == null && irEnabled && SystemClock.uptimeMillis() >= retryIrAt) {
                            irState = "IR opening…"; view.postInvalidate();
                            ir = new IrSession(this); status = ""; irState = "IR open";
                            lastIr = SystemClock.uptimeMillis(); view.postInvalidate();
                        }
                        while ((burst = PwCore.irPop()) != null) {
                            if (ir != null) { trace("TX", burst); ir.send(burst); irTx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                        }
                        if (ir != null) {
                            byte[] rx = ir.exchange(2, 2, null);
                            if (rx.length > 0) { trace("RX", rx); PwCore.irPush(rx); irRx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            else if (!irEnabled && SystemClock.uptimeMillis() - lastIr > 15000) {
                                ir.close(); ir = null; irState = "IR idle"; view.postInvalidate();
                            }
                        }
                    } catch (IOException failure) {
                        // A closed helper/UART must not stop the emulated firmware or
                        // strand future connection attempts. Reopen on its next enable.
                        if (ir != null) ir.close(); ir = null;
                        retryIrAt = SystemClock.uptimeMillis() + 1000;
                        status = "Infrared unavailable: " + failure.getMessage(); irState = "IR failed";
                        android.util.Log.w("Pokewalker", "IR session failed; retrying", failure);
                        view.postInvalidate();
                    }
                }
'''
if '// Follow the firmware' not in s:s=s[:a]+new+s[b:]
s=s.replace('        long lastIr = 0;', '        long lastIr = 0, retryIrAt = 0;')
p.write_text(s)
print('IR_RECONNECT_SOURCE_OK')
# Do not let a new resume reset the singleton native core while the previous
# worker is still finishing a blocking UART startup or durable EEPROM save.
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java',
      '    private final Object lock = new Object();',
      '    private static final Object CORE_LOCK = new Object();\n    private volatile int emulationGeneration;\n    private final Object lock = new Object();')
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java',
      '        thread = new Thread(this::emulate, "pokewalker");',
      '        keys = 0;\n        final int generation = ++emulationGeneration;\n        thread = new Thread(() -> emulate(generation), "pokewalker");')
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java',
      '        running = false;\n        try { if (thread != null)',
      '        running = false; ++emulationGeneration; keys = 0;\n        release.removeCallbacksAndMessages(null);\n        try { if (thread != null)')
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java',
      '    private void emulate() {',
      '    private void emulate(int generation) {\n        synchronized (CORE_LOCK) {\n            if (!running || generation != emulationGeneration) return;\n            emulateLocked(generation);\n        }\n    }\n\n    private void emulateLocked(int generation) {')
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java',
      '            while (running) {',
      '            while (running && generation == emulationGeneration) {')
p=R/'templates/AndroidManifest.xml';s=p.read_text().replace('android:versionCode="5" android:versionName="0.5-button-icons"','android:versionCode="6" android:versionName="0.6-ir-reconnect"');p.write_text(s)
patch('templates/src/org/kyf37/walker/WalkerActivity.java',
      '        super.onCreate(state);',
      '''        super.onCreate(state);
        // Remove the legacy standalone emulator task; save files are untouched.
        try {
            ActivityManager manager = (ActivityManager)getSystemService(ACTIVITY_SERVICE);
            for (ActivityManager.AppTask task : manager.getAppTasks()) {
                ActivityManager.RecentTaskInfo info = task.getTaskInfo();
                ComponentName component = info.baseIntent == null ? null : info.baseIntent.getComponent();
                if (info.id != getTaskId() && component != null
                        && getPackageName().equals(component.getPackageName())
                        && EmulatedWalkerActivity.class.getName().equals(component.getClassName())) {
                    task.finishAndRemoveTask();
                }
            }
        } catch (RuntimeException failure) {
            android.util.Log.w("Pokewalker", "Legacy task cleanup unavailable", failure);
        }''')
