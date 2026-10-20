#!/usr/bin/env python3
"""Refresh the three generated classifier asset hashes in the app data manifest."""
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
manifest = ROOT / 'app/assets/data/manifest.json'
meta = json.loads(manifest.read_text())
files = meta.get('files', meta)
for name in ['ml/labels.json', 'ml/model.json', 'ml/pokemon-int8.tflite']:
    path = ROOT / 'app/assets' / name
    key = name if name in files else 'assets/' + name
    if key not in files:
        raise SystemExit(f'Manifest does not contain {name}')
    files[key] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
print('ML_MANIFEST_UPDATED')
for name in ['ml/labels.json', 'ml/model.json', 'ml/pokemon-int8.tflite']:
    key = name if name in files else 'assets/' + name
    print(key, files[key])
