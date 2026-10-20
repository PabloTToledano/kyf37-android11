#!/usr/bin/env python3
from pathlib import Path
import shutil
r=Path(__file__).resolve().parents[1];tree=r.parent/'native/kyf37-android11'
out=r/'dist/licenses';out.mkdir(parents=True,exist_ok=True)
for name,relative in {
    'bionic-libc-NOTICE.txt':'bionic/libc/NOTICE',
    'bionic-libdl-NOTICE.txt':'bionic/libdl/NOTICE',
    'clang-NOTICE.txt':'prebuilts/clang/host/linux-x86/clang-r377782b/NOTICE',
    'gcc-NOTICE.txt':'prebuilts/gcc/linux-x86/arm/arm-linux-androideabi-4.9/NOTICE',
}.items():shutil.copyfile(tree/relative,out/name)
for name in ['THIRD_PARTY.md','README.md','IR-EVIDENCE.md','VALIDATION.md','MAGISK.md']:shutil.copyfile(r/name,r/'dist'/name)

shutil.copyfile(r/"LICENSE",out/"FlipWalker-GPL-3.0.txt")

shutil.copyfile(r/"references/pokeapi-localization/LICENSE.md",out/"PokeAPI-LICENSE.txt")
