#!/usr/bin/env python3
"""Rerunnable bounded native execution with a low-cost fault PC snapshot."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text()
if '#include <stdatomic.h>' not in s:s=s.replace('#include "pwcore.h"','#include "pwcore.h"\n#include <stdatomic.h>\nstatic _Atomic unsigned diagnostic_pc;')
if 'int pwcore_pc(void)' not in s:s=s.replace('int pwcore_ir_enabled(void)','int pwcore_pc(void) { return (int)atomic_load(&diagnostic_pc); }\nint pwcore_ir_enabled(void)',1)
if 'if (d <= 0)' not in s:s=s.replace('        int d = g_ctx.states - old;', '        int d = g_ctx.states - old;\n        if (d <= 0) { atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed); halt = 1; return -1; }')
if 'atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed);\n    return halt' not in s:s=s.replace('    return halt ? -1 : 0;','    atomic_store_explicit(&diagnostic_pc, g_ctx.ip, memory_order_relaxed);\n    return halt ? -1 : 0;',1)
p.write_text(s)
for path,old,new,marker in [
 ('native/pwcore/pwcore.h','int pwcore_ir_enabled(void);','int pwcore_pc(void);\nint pwcore_ir_enabled(void);','int pwcore_pc(void);'),
 ('native/pwcore/pwcore_jni.c','JNIEXPORT jboolean JNICALL FN(irEnabled)','JNIEXPORT jint JNICALL FN(pc)(JNIEnv *e, jclass c) { (void)e; (void)c; return pwcore_pc(); }\nJNIEXPORT jboolean JNICALL FN(irEnabled)','FN(pc)'),
 ('templates/src/org/kyf37/walker/PwCore.java','    static native boolean irEnabled();','    static native int pc();\n    static native boolean irEnabled();','static native int pc();')]:
 p=r/path;s=p.read_text()
 if marker not in s:
  assert old in s,path
  p.write_text(s.replace(old,new,1))
