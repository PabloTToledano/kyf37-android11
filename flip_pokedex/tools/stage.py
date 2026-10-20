#!/usr/bin/env python3
"""Recreate app sources from canonical templates; optionally stage a Soong module."""
from pathlib import Path
import argparse, shutil
root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(); p.add_argument('--tree', type=Path); p.add_argument('--keypad-policy', action='store_true'); args = p.parse_args()
dest = args.tree / 'packages/apps/FlipPokedex' if args.tree else root / 'app'
dest.mkdir(parents=True, exist_ok=True)
shutil.copytree(root / 'templates', dest, dirs_exist_ok=True)
if (root / 'app/assets/data').exists() and dest != root / 'app':
    shutil.copytree(root / 'app/assets', dest / 'assets', dirs_exist_ok=True)
    if (root / 'app/libs').exists(): shutil.copytree(root / 'app/libs',dest / 'libs',dirs_exist_ok=True)
if args.keypad_policy:
    if not args.tree: p.error('--keypad-policy requires --tree')
    policy = args.tree / 'frameworks/base/services/core/java/com/android/server/policy/PhoneWindowManager.java'
    text = policy.read_text()
    if 'case "org.kyf37.pokedex":' not in text:
        anchor = '            case "jp.kyocera.camera":'
        if text.count(anchor) != 1: raise SystemExit('Native-softkey policy anchor is not unique; policy left unchanged')
        policy.write_text(text.replace(anchor, anchor + '\n            case "org.kyf37.pokedex":', 1))
print(dest)
