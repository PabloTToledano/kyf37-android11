#!/usr/bin/env python3
"""Final source migration after diagnosing RTC startup; remove costly tracing."""
from pathlib import Path
import re
r=Path(__file__).resolve().parents[1]
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text()
s=re.sub(r'^\s*atomic_store\(&diagnostic_pc,.*\n','\n',s,flags=re.M)
s=s.replace('    return halt ? -1 : 0;', '    atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed);\n    return halt ? -1 : 0;') if 'atomic_store_explicit(&diagnostic_pc' not in s else s
s=s.replace('atomic_store(&diagnostic_clock,','atomic_store_explicit(&diagnostic_clock,').replace('| g_ctx.ccr);','| g_ctx.ccr, memory_order_relaxed);')
p.write_text(s)
p=r/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text()
s=re.sub(r'^\s*new Handler\(Looper.getMainLooper\(\)\).postDelayed\(\(\) -> android.util.Log.i\("Pokewalker", "Core stage/PC.*\n','\n',s,flags=re.M)
s=s.replace('buttons.press(k); android.util.Log.i("Pokewalker", "Button down " + code + " bit=" + k);','buttons.press(k);')
s=s.replace('                keys = buttons.sample(slice);','                int sampled = buttons.sample(slice);\n                if (keys != sampled) { keys = sampled; view.postInvalidate(); }')
if 'byte[] pendingBurst = pc == null ?' not in s:s=s.replace('                boolean irEnabled = pc == null && PwCore.irEnabled();','                byte[] pendingBurst = pc == null ? PwCore.irPop() : null;\n                boolean irEnabled = pc == null && PwCore.irEnabled();')
s=s.replace('ir == null && irEnabled &&','ir == null && (irEnabled || pendingBurst != null) &&')
s=s.replace('                        while ((burst = PwCore.irPop()) != null) {','                        while ((burst = pendingBurst) != null) {\n                            pendingBurst = PwCore.irPop();')
p.write_text(s)
# Give the firmware time to finish boot before testing the selected menu item.
p=r/'tools/check-connect-button.ps1';s=p.read_text().replace('  Start-Sleep 2','  Start-Sleep 8');p.write_text(s)
