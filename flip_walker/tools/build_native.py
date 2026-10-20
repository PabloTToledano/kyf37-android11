#!/usr/bin/env python3
"""Compile fixed-path SIR helper with local AOSP clang, bionic headers and NDK libc."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
tree=root.parent/'native/kyf37-android11'
clang=tree/'prebuilts/clang/host/linux-x86/clang-r377782b/bin/clang'
lib=tree/'prebuilts/ndk/r21/platforms/android-23/arch-arm/usr/lib'
bionic=tree/'bionic/libc'
includes=[bionic/'include',bionic/'kernel/uapi',bionic/'kernel/uapi/asm-arm',bionic/'kernel/android/uapi']
builtins=list((clang.parent.parent/'lib64/clang').glob('*/lib/linux/libclang_rt.builtins-arm-android.a'))
if not builtins: builtins=list((clang.parent.parent/'lib64/clang').glob('*/lib/linux/arm/libclang_rt.builtins*.a'))
assert builtins,'Missing ARM compiler runtime'
out=root/'app/libs/armeabi-v7a/libwalker_ir.so';out.parent.mkdir(parents=True,exist_ok=True)
command=[str(clang),'--target=armv7a-linux-androideabi23','-march=armv7-a','-mfloat-abi=softfp','-fuse-ld=lld','-static','-nostdlib','-D__ANDROID_API__=23','-O2','-Wall','-Wextra','-Werror']
for include in includes: command+=['-isystem',str(include)]
gcc=tree/'prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9/lib/gcc/arm-linux-androideabi/4.9.x/armv7-a/libgcc.a'
command += [str(lib/'crtbegin_static.o'),str(root/'native/walker_ir.c'),'-Wl,--start-group',str(lib/'libc.a'),str(lib/'libm.a'),str(lib/'libdl.a'),str(lib/'libcompiler_rt-extras.a'),str(builtins[0]),str(gcc),'-Wl,--end-group',str(lib/'crtend_android.o'),'-o',str(out)]
subprocess.run(command,check=True)
print('ARMv7 infrared helper compiled (hardware untested)')
if __import__('os').environ.get('WALKER_EMULATOR')=='1':
    xlib=tree/'prebuilts/ndk/r21/platforms/android-23/arch-x86_64/usr/lib64'
    if not xlib.exists(): xlib=tree/'prebuilts/ndk/r21/platforms/android-23/arch-x86_64/usr/lib'
    xout=root/'app/libs/x86_64/libwalker_ir.so';xout.parent.mkdir(parents=True,exist_ok=True)
    xcommand=[str(clang),'--target=x86_64-linux-android23','-fuse-ld=lld','-static','-nostdlib','-D__ANDROID_API__=23','-O2','-Wall','-Wextra','-Werror']
    for include in [bionic/'include',bionic/'kernel/uapi',bionic/'kernel/uapi/asm-x86',bionic/'kernel/android/uapi']:xcommand+=['-isystem',str(include)]
    xbuiltins=list((clang.parent.parent/'lib64/clang').glob('*/lib/linux/libclang_rt.builtins-x86_64-android.a'))[0]
    xcommand += [str(xlib/'crtbegin_static.o'),str(root/'native/walker_ir.c'),'-Wl,--start-group',str(xlib/'libc.a'),str(xlib/'libm.a'),str(xlib/'libdl.a'),str(xbuiltins),'-Wl,--end-group',str(xlib/'crtend_android.o'),'-o',str(xout)]
    subprocess.run(xcommand,check=True)
