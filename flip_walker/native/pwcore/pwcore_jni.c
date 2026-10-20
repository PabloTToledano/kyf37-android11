/* JNI bridge for org.kyf37.walker.PwCore (full Pokéwalker emulation). */
#include <jni.h>
#include <string.h>
#include "pwcore.h"

#define FN(name) Java_org_kyf37_walker_PwCore_##name

JNIEXPORT jboolean JNICALL FN(init)(JNIEnv *env, jclass c, jbyteArray rom, jbyteArray eeprom) {
    (void)c;
    jsize rn = (*env)->GetArrayLength(env, rom);
    if (rn <= 0 || rn > 65536 || (*env)->GetArrayLength(env, eeprom) != 65536) return JNI_FALSE;
    jbyte *r = (*env)->GetByteArrayElements(env, rom, NULL);
    jbyte *e = (*env)->GetByteArrayElements(env, eeprom, NULL);
    int ok = pwcore_init((const uint8_t *)r, rn, (const uint8_t *)e) == 0;
    (*env)->ReleaseByteArrayElements(env, rom, r, JNI_ABORT);
    (*env)->ReleaseByteArrayElements(env, eeprom, e, JNI_ABORT);
    return ok ? JNI_TRUE : JNI_FALSE;
}
JNIEXPORT jint JNICALL FN(run)(JNIEnv *env, jclass c, jint ms, jint keys) { (void)env; (void)c; return pwcore_run(ms, keys); }
JNIEXPORT jboolean JNICALL FN(frame)(JNIEnv *env, jclass c, jbyteArray out) {
    (void)c;
    uint8_t fb[PWCORE_W * PWCORE_H];
    int changed = pwcore_frame(fb);
    (*env)->SetByteArrayRegion(env, out, 0, PWCORE_W * PWCORE_H, (const jbyte *)fb);
    return changed ? JNI_TRUE : JNI_FALSE;
}
JNIEXPORT jbyteArray JNICALL FN(eepromIfDirty)(JNIEnv *env, jclass c) {
    (void)c;
    if (!pwcore_eeprom_dirty()) return NULL;
    jbyteArray a = (*env)->NewByteArray(env, 65536);
    (*env)->SetByteArrayRegion(env, a, 0, 65536, (const jbyte *)pwcore_eeprom());
    return a;
}
JNIEXPORT jint JNICALL FN(pc)(JNIEnv *e, jclass c) { (void)e; (void)c; return pwcore_pc(); }
JNIEXPORT jboolean JNICALL FN(irEnabled)(JNIEnv *e, jclass c) {
    (void)e; (void)c; return pwcore_ir_enabled() ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT void JNICALL FN(irPush)(JNIEnv *env, jclass c, jbyteArray data) {
    (void)c;
    jsize n = (*env)->GetArrayLength(env, data);
    if (n <= 0 || n > 263) return;
    uint8_t buf[263];
    (*env)->GetByteArrayRegion(env, data, 0, n, (jbyte *)buf);
    pwcore_ir_push(buf, n);
}
JNIEXPORT jbyteArray JNICALL FN(irPop)(JNIEnv *env, jclass c) {
    (void)c;
    uint8_t buf[263];
    int n = pwcore_ir_pop(buf, sizeof buf);
    if (n <= 0) return NULL;
    jbyteArray a = (*env)->NewByteArray(env, n);
    (*env)->SetByteArrayRegion(env, a, 0, n, (const jbyte *)buf);
    return a;
}
JNIEXPORT jint JNICALL FN(ramRead)(JNIEnv *env, jclass c, jint a) { (void)env; (void)c; return pwcore_ram_read(a); }
JNIEXPORT void JNICALL FN(ramWrite)(JNIEnv *env, jclass c, jint a, jint v) { (void)env; (void)c; pwcore_ram_write(a, v); }
JNIEXPORT jint JNICALL FN(call)(JNIEnv *env, jclass c, jint addr, jint r0) { (void)env; (void)c; return pwcore_call(addr, r0); }
