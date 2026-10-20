#!/usr/bin/env python3
"""Prepare, but do not apply, corner-key ROM changes. No device access.

Re-run after other policy generators, before building matching ROM images.
--apply writes only the explicitly selected source tree, under the build lock.
"""
from pathlib import Path
import argparse,difflib,fcntl,os,re
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--tree',type=Path,default=root.parent/'native/kyf37-android10');p.add_argument('--apply',action='store_true')
args=p.parse_args()
path=args.tree/'frameworks/base/services/core/java/com/android/server/policy/PhoneWindowManager.java'
original=path.read_text();s=original
anchor='    private boolean isKyf37NativeSoftkeyApp(String name) {'
assert anchor in s,'Unknown key policy; refusing a speculative patch'
methods=list(re.finditer(r'    private boolean isKyf37NativeSoftkeyApp\(String name\) \{.*?\n    }\n',s,re.S))
if len(methods)>1:
    normalized=[m.group().replace('            case "org.kyf37.walker":\n','') for m in methods]
    assert len(set(normalized))==1,'Conflicting corner-key policies; refusing to discard one'
    for m in reversed(methods[1:]):s=s[:m.start()]+s[m.end():]
start=s.index(anchor);end=s.index('\n    }',start)+6
section=s[start:end]
if 'case "org.kyf37.walker":' not in section:
    assert 'switch (name) {' in section
    s=s[:start]+section.replace('switch (name) {','switch (name) {\n            case "org.kyf37.walker":',1)+s[end:]
out=root/'dist';out.mkdir(exist_ok=True)
patch=''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/'+str(path.relative_to(args.tree)),tofile='b/'+str(path.relative_to(args.tree))))
(out/(args.tree.name+'-corner-keys.patch')).write_text(patch)
if args.apply:
    try: fcntl.flock(9,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except (OSError,ValueError): raise SystemExit('Run --apply only through build-locked.sh --script')
    assert Path(os.readlink('/proc/self/fd/9')).resolve()==(Path.home()/'kyf37-build.lock').resolve(),'Unexpected lock file'
    if s!=original:path.write_text(s)
print(('Applied' if args.apply else 'Prepared')+' corner-key policy for '+args.tree.name)
