#!/usr/bin/env python3
"""Create deterministic photo-like training views from the cached training split."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'cache/classifier-dataset'
OUT = ROOT / 'cache/classifier-training/photo-train'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from photo_sim import make_photo, OUT as SIZE  # noqa: E402

def main():
    rows = json.loads((D / 'train.json').read_text())
    negatives = sorted((ROOT / 'cache/classifier-training/negatives/train').glob('*.jpg'))
    pool = [Image.open(p).convert('RGB') for p in negatives]
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for i, row in enumerate(rows):
        source = D / row['path'] if not Path(row['path']).is_absolute() else Path(row['path'])
        with Image.open(source) as im:
            obj = np.asarray(im.convert('RGB').resize((SIZE, SIZE), Image.Resampling.BILINEAR), np.uint8)
        rng = np.random.default_rng([173, i, int(row['label'])])
        generic = '/negatives/' in str(source)
        photo = make_photo(rng, obj, pool, opaque=generic)
        dest = OUT / f'{i:06d}-{int(row["label"]):03d}.jpg'
        Image.fromarray(photo).save(dest, quality=92, optimize=True)
        made.append({'path': str(dest), 'label': int(row['label']), 'national': int(row.get('national', 0))})
        if i and i % 1000 == 0:
            print('PHOTO_AUGMENT', i, '/', len(rows), flush=True)
    (ROOT / 'cache/classifier-training/photo-train.json').write_text(json.dumps(made))
    print('PHOTO_AUGMENT_READY', len(made), flush=True)

if __name__ == '__main__':
    main()
