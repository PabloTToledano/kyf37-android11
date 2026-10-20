#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[1]
def patch(path,old,new):
 p=r/path;s=p.read_text()
 if old=='int pwcore_clock_state(void)' and 'void pwcore_button_trace(char' in s:return
 if old=='JNIEXPORT jint JNICALL FN(clockState)' and 'FN(buttonTrace)' in s:return
 if old=='                int sampled = buttons.sample(slice);' and 'int previousKeys = keys;' in s:return
 if new not in s:
  assert old in s,path
  p.write_text(s.replace(old,new,1))
p=r/'native/pwcore/main.c';s=p.read_text().replace('''    /* Fixed healthy virtual supply; full-scale was reported as a depleted cell. */
    return 0x8000;''','    return 0xFFC0;');p.write_text(s)
patch('native/pwcore/main.c','static void branch(pw_context_t *ctx, uint32_t br_addr, uint32_t ret) {','''#ifdef PW_LIBRARY
static unsigned bt_addr[256], bt_arg[256], bt_count[256], bt_n;
#endif
static void branch(pw_context_t *ctx, uint32_t br_addr, uint32_t ret) {
#ifdef PW_LIBRARY
    if (ctx->keys_pressed & 1) {
        unsigned i;
        for (i=0; i<bt_n; i++) if (bt_addr[i] == (br_addr & 65535)) break;
        if (i<256) {
            if (i==bt_n) { bt_n++; bt_addr[i]=br_addr & 65535; bt_count[i]=0; }
            bt_arg[i]=read_reg16(ctx,R0); bt_count[i]++;
        }
    }
#endif''')
patch('native/pwcore/pwcore_glue.inc','    g_ctx.keys_pressed = (uint8_t)keys;', '    if ((keys & 1) && !(g_ctx.keys_pressed & 1)) bt_n=0;\n    g_ctx.keys_pressed = (uint8_t)keys;')
patch('native/pwcore/pwcore_glue.inc','int pwcore_clock_state(void)', '''void pwcore_button_trace(char *out, int max) {
    int off=0;
    for (unsigned i=0; i<bt_n && off<max-40; i++)
        off+=snprintf(out+off,max-off,"%04x:%04x/%u ",bt_addr[i],bt_arg[i],bt_count[i]);
    out[off]=0;
}
int pwcore_clock_state(void)''')
patch('native/pwcore/pwcore.h','int pwcore_clock_state(void);','void pwcore_button_trace(char *out, int max);\nint pwcore_clock_state(void);')
patch('native/pwcore/pwcore_jni.c','JNIEXPORT jint JNICALL FN(clockState)', '''JNIEXPORT jstring JNICALL FN(buttonTrace)(JNIEnv *e, jclass c) { (void)c; char out[4096]; pwcore_button_trace(out,sizeof out); return (*e)->NewStringUTF(e,out); }
JNIEXPORT jint JNICALL FN(clockState)''')
patch('templates/src/org/kyf37/walker/PwCore.java','    static native int clockState();','    static native String buttonTrace();\n    static native int clockState();')
patch('templates/src/org/kyf37/walker/EmulatedWalkerActivity.java','                int sampled = buttons.sample(slice);', '''                int previousKeys = keys;
                int sampled = buttons.sample(slice);
                if ((previousKeys & 1) != 0 && (sampled & 1) == 0) android.util.Log.i("Pokewalker", "CONNECT_TRACE " + PwCore.buttonTrace());''')
patch('native/pwcore/main.c','#define debug(...)\n#endif','''#ifdef PW_LIBRARY
static int bt_capture, bt_off;
static char bt_assembly[16384];
static void bt_format(const char *format, ...) {
    if (bt_off >= (int)sizeof(bt_assembly)-256) return;
    va_list args; va_start(args,format);
    int n=vsnprintf(bt_assembly+bt_off,sizeof(bt_assembly)-bt_off,format,args);
    va_end(args);
    if (n>0) bt_off += n;
}
#define debug(...) do { if (bt_capture) bt_format(__VA_ARGS__); } while(0)
#else
#define debug(...)
#endif
#endif''')
patch('native/pwcore/main.c','    uint16_t oip = ctx->ip;', '''    uint16_t oip = ctx->ip;
#ifdef PW_LIBRARY
    bt_capture = (ctx->keys_pressed & 1) && ctx->ip >= 0x6b4c && ctx->ip < 0x6bac;
#endif''')
p=r/'native/pwcore/main.c';s=p.read_text().replace('    debug("%.4x ", instr);','    debug("%.4x ", ctx->instr_prefetch);');p.write_text(s)
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text().replace('bt_n=0;','{ bt_n=0; bt_off=0; bt_assembly[0]=0; }');s=s.replace('    int off=0;\n    for (unsigned i=0;', '    int off=snprintf(out,max,"%s",bt_assembly);\n    if(off>=max)off=max-1;\n    for (unsigned i=0;');p.write_text(s)
p=r/'native/pwcore/pwcore_jni.c';s=p.read_text().replace('char out[4096]; pwcore_button_trace','char out[16384]; pwcore_button_trace');p.write_text(s)
p=r/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text().replace('if ((previousKeys & 1) != 0 && (sampled & 1) == 0) android.util.Log.i("Pokewalker", "CONNECT_TRACE " + PwCore.buttonTrace());','''if ((previousKeys & 1) != 0 && (sampled & 1) == 0) {
                    String traceText=PwCore.buttonTrace();
                    for(int ti=0;ti<traceText.length();ti+=2500) android.util.Log.i("Pokewalker", "CONNECT_TRACE " + traceText.substring(ti,Math.min(ti+2500,traceText.length())));
                }''');p.write_text(s)
p=r/'native/pwcore/main.c';s=p.read_text().replace('debug("sub.l #%x:32, ER%d\\n", imm, MIN_LCHK);','debug("sub.l #%x:32, ER%d\\n", peek32(ctx,addr+2), MIN_LCHK);').replace('debug("or.l #%x:32, ER%d FIXME\\n", imm, MIN_LCHK);','debug("or.l #%x:32, ER%d FIXME\\n", peek32(ctx,addr+2), MIN_LCHK);');p.write_text(s)

import re
for relative in ['native/pwcore/pwcore_glue.inc','native/pwcore/pwcore_jni.c','templates/src/org/kyf37/walker/EmulatedWalkerActivity.java']:
 p=r/relative;s=p.read_text()
 for pattern in [r'(void pwcore_button_trace\(char \*out, int max\) \{.*?\n\}\n)\1',r'(JNIEXPORT jstring JNICALL FN\(buttonTrace\)[^\n]*\n)\1',r'(                int previousKeys = keys;\n)\1',r'(                if \(\(previousKeys & 1\) != 0.*?\n                \}\n)\1']:
  while re.search(pattern,s,re.S):s=re.sub(pattern,r'\1',s,flags=re.S)
 if 'pwcore_glue' in relative:
  s=re.sub(r'^    if \(\(keys & 1\).*bt_n=0;.*$', '    if ((keys & 1) && !(g_ctx.keys_pressed & 1)) { bt_n=0; bt_off=0; bt_assembly[0]=0; }',s,flags=re.M)
 p.write_text(s)
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text();s=s.replace('    int off=snprintf(out,max,"%s",bt_assembly);','''    int off=snprintf(out,max,"EV=%04x MUSIC=%04x COUNT=%04x TMR=%02x/%02x/%02x/%02x TCNT=%04x GRA=%04x CCR=%02x IE=%d\\n%s", read16(&g_ctx,0xf7e0),read16(&g_ctx,0xf7c4),read16(&g_ctx,0xf7c8),g_ctx.tmrw,g_ctx.tcrw,g_ctx.tierw,g_ctx.tsrw,g_ctx.tcnt,g_ctx.gra,g_ctx.ccr,g_ctx.int_enabled,bt_assembly);''');p.write_text(s)
