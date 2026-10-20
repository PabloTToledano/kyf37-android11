#!/usr/bin/env python3
"""Rerunnable finalization: transparent RAM, DEC flags, no diagnostic tracing, release 0.7."""
from pathlib import Path
import re
r=Path(__file__).resolve().parents[1]
p=r/'native/pwcore/main.c';s=p.read_text()
s=s.replace("    /* Fixed healthy virtual supply; full-scale was reported as a depleted cell. */\n    return 0x8000;", "    return 0xFFC0;")
s=re.sub(r'#ifdef PW_LIBRARY\nstatic int bt_capture.*?#else\n#define debug\(\.\.\.\)\n#endif','#define debug(...)',s,flags=re.S)
s=re.sub(r'#ifdef PW_LIBRARY\nstatic unsigned bt_addr.*?#endif\n','',s,flags=re.S)
s=re.sub(r'#ifdef PW_LIBRARY\n    if \(ctx->keys_pressed & 1\).*?#endif\n','',s,flags=re.S)
s=re.sub(r'#ifdef PW_LIBRARY\n    bt_capture = .*?#endif\n','',s,flags=re.S)
s=s.replace('''        if (addr == 0xF78E) { // watts
            return 132;
        }
''','')
s=s.replace('''        if (addr == 0xF7B5) { // common_bit_flags
            return (ctx->ram[addr - RAM_start] | 1UL) & ~(1 << 4);
        }
''','')
s=s.replace('''        // Preserve the existing event-loop wake workaround, but do not clear IR state bit 4.
        if (addr == 0xF7B5) return ctx->ram[addr - RAM_start] | 1;
''','')
a=s.index('static uint16_t decw(');b=s.index('\n}',a)+2
s=s[:a]+'''static uint16_t decw(pw_context_t *ctx, uint16_t val, uint16_t dec) {
    uint16_t res = val - dec;
    set_ccr_bit(ctx, CCR_N, (res & 0x8000) != 0);
    set_ccr_bit(ctx, CCR_Z, res == 0);
    set_ccr_bit(ctx, CCR_V, val >= 0x8000 && (uint32_t)val < 0x8000u + dec);
    return res;
}'''+s[b:];p.write_text(s)
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text()
s=re.sub(r'void pwcore_button_trace\(.*?^}\n','',s,flags=re.S|re.M)
s=re.sub(r'^.*bt_n=0;.*\n','',s,flags=re.M)
s=re.sub(r'^int pwcore_clock_state.*\n','',s,flags=re.M)
s=s.replace('static _Atomic unsigned diagnostic_pc, diagnostic_clock;','static _Atomic unsigned diagnostic_pc;')
s=re.sub(r'^.*atomic_store_explicit\(&diagnostic_clock,.*\n','',s,flags=re.M)
s=s.replace('if (d <= 0) { halt = 1; return -1; }','if (d <= 0) { atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed); halt = 1; return -1; }')
p.write_text(s)
p=r/'native/pwcore/pwcore.h';s=p.read_text();s=re.sub(r'^.*pwcore_(button_trace|clock_state).*\n','',s,flags=re.M);p.write_text(s)
p=r/'native/pwcore/pwcore_jni.c';s=p.read_text();s=re.sub(r'^JNIEXPORT.*FN\((buttonTrace|clockState)\).*\n','',s,flags=re.M);p.write_text(s)
p=r/'templates/src/org/kyf37/walker/PwCore.java';s=p.read_text();s=re.sub(r'^.*static native.*(buttonTrace|clockState)\(.*\n','',s,flags=re.M);p.write_text(s)
p=r/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text()
s=s.replace('                int previousKeys = keys;\n','')
s=re.sub(r'                if \(\(previousKeys & 1\).*?\n                }\n','',s,flags=re.S)
p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('android:versionCode="6" android:versionName="0.6-ir-reconnect"','android:versionCode="7" android:versionName="0.7-core-timing"');p.write_text(s)
# Byte and word reads must observe actual firmware RAM, including watts.
p=r/'tests/pwcore/ir_reconnect_test.c';s=p.read_text();test='''    g_ctx.ram[0xF78E - RAM_start]=0xbe;g_ctx.ram[0xF78F - RAM_start]=0xef;
    assert(read16(&g_ctx,0xF78E)==0xbeef);
    g_ctx.ccr=0x21;assert(decw(&g_ctx,1,1)==0);assert(get_ccr_bit(&g_ctx,CCR_Z));assert((g_ctx.ccr&0x21)==0x21);
    assert(decw(&g_ctx,0x8000,1)==0x7fff);assert(get_ccr_bit(&g_ctx,CCR_V));
'''
if test not in s:s=s.replace('    assert(!pwcore_ir_enabled());',test+'    assert(!pwcore_ir_enabled());',1)
p.write_text(s)
print('CORE_REVIEW_FINALIZED: transparent RAM, RTC, Timer W, DEC.W, bounded CPU progress, button latch')
