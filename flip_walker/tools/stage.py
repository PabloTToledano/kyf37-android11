#!/usr/bin/env python3
"""Rerunnable app source staging; never accesses a device or shared ROM sources."""
from pathlib import Path
import shutil
root = Path(__file__).resolve().parents[1]
for source in (root / 'templates').rglob('*'):
    if source.is_file():
        target = root / 'app' / source.relative_to(root / 'templates')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
print('FlipWalker sources staged')
