#!/usr/bin/env python3
"""Fetch pinned, hash-verified localization sources; never accesses a phone."""
from pathlib import Path
import urllib.request,json,hashlib
r=Path(__file__).resolve().parents[2];manifest=json.loads((r/'tools/localization/pokeapi-reference.json').read_text());dest=r/'references/pokeapi-localization';dest.mkdir(parents=True,exist_ok=True)
for name,expected in manifest['files'].items():
 p=dest/name
 if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==expected:continue
 relative=name if name=='LICENSE.md' else 'data/v2/csv/'+name
 url='https://raw.githubusercontent.com/PokeAPI/pokeapi/'+manifest['commit']+'/'+relative
 data=urllib.request.urlopen(url,timeout=30).read()
 if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Reference checksum mismatch: '+name)
 p.write_bytes(data);print('Fetched '+name)
(dest/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
