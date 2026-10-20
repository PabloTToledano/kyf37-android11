#!/usr/bin/env python3
"""Compile the full-emulation core (native/pwcore, PW_LIBRARY) as libpwcore.so for armeabi-v7a
with the local AOSP clang, linking dynamically against the NDK API-26 libc/libm stubs."""
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[1]
tree = root.parent / 'native/kyf37-android11'
clang = tree / 'prebuilts/clang/host/linux-x86/clang-r377782b/bin/clang'
ndk = tree / 'out/soong/ndk/platforms/android-26/arch-arm/usr/lib'
bionic = tree / 'bionic/libc'
src = root / 'native/pwcore'
crt = tree / 'prebuilts/ndk/r21/platforms/android-23/arch-arm/usr/lib'
includes = [bionic / 'include', bionic / 'kernel/uapi', bionic / 'kernel/uapi/asm-arm', bionic / 'kernel/android/uapi',
            tree / 'libnativehelper/include_jni', src]
builtins = list((clang.parent.parent / 'lib64/clang').glob('*/lib/linux/libclang_rt.builtins-arm-android.a'))
assert builtins and (ndk / 'libc.so').exists(), 'Missing ARM runtime or NDK stubs'
out = root / 'app/libs/armeabi-v7a/libpwcore.so'; out.parent.mkdir(parents=True, exist_ok=True)
cmd = [str(clang), '--target=armv7a-linux-androideabi26', '-march=armv7-a', '-mfloat-abi=softfp', '-mthumb', '-fuse-ld=lld',
       '-shared', '-fPIC', '-nostdlib', '-D__ANDROID_API__=26', '-DPW_LIBRARY', '-O2', '-w',
       '-Wl,-soname,libpwcore.so', '-Wl,--no-undefined', '-Wl,-z,noexecstack']
for i in includes: cmd += ['-isystem', str(i)]
cmd += [str(crt / 'crtbegin_so.o')]
cmd += [str(src / f) for f in ('main.c', 'ssu.c', 'eeprom.c', 'lcd.c', 'accel.c', 'rtc.c', 'portb.c', 'interrupts.c', 'pwcore_jni.c')]
cmd += [str(builtins[0]), '-L' + str(ndk), '-lc', '-lm', '-ldl', str(crt / 'crtend_so.o'), '-o', str(out)]
subprocess.run(cmd, check=True)
print('ARMv7 libpwcore.so built:', out)
