#!/usr/bin/env python3
"""Check offline completeness and known Gen V historical regressions before packaging."""
import json, hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'app/assets'
manifest=json.loads((r/'data/manifest.json').read_text())
for path,expected in manifest['files'].items():
    assert hashlib.sha256((r/path).read_bytes()).hexdigest()==expected, path
entries=json.loads((r/'data/index.json').read_text()); default=[e for e in entries if e['id']==e['species']]
assert {e['id'] for e in default}==set(range(1,1026))
regional=[e for e in default if e['unova']>=0]
assert len(regional)==301 and sorted(e['unova'] for e in regional)==list(range(301))
def pokemon(i):return json.loads((r/f'data/pokemon/{i}.json').read_text())
for e in entries:
    d=pokemon(e['id']);assert d['stats'] and len(d['stats'])==6 and d['types']
    assert d['black2'] or d['white2'] or d['fallbackText'], e['id']
    sprite=d.get('sprite',str(d['id']))
    assert (r/f'sprites/{sprite}.png').exists() or (r/f'sprites/animated/{sprite}.gif').exists(), sprite
assert pokemon(35)['types']==['Normal'] # Fairy did not exist.
# Spanish (es) coverage: every national species has a Spanish name, genus and fallback entry text.
assert all(pokemon(i)['name_es'] and pokemon(i)['genus_es'] and pokemon(i)['fallbackText_es'] for i in range(1,1026))
# #899-1025 Spanish genus and entry text come from cache/es_fill.json (WikiDex; source URLs stored there).
assert all(a['name_es'] and a['text_es'] for e in entries for a in pokemon(e['id'])['abilities']), 'Spanish ability fallback'
# All-game encounter rows retain their exact version and Spanish area/method labels.
for e in entries:
    for enc in pokemon(e['id'])['encounters']:
        assert enc['area_es'] and enc['version'] > 0 and enc['method_es'], ('Spanish area fallback', e['id'], enc['area'])
# Move descriptions: every learnset row has Spanish text, and it is not the English text.
for e in entries:
    for mv in pokemon(e['id'])['moves']:
        assert mv['text_es'] and (not mv['text'] or mv['text_es'] != mv['text']), ('Spanish move text fallback', e['id'], mv['name'])
# Evolution conditions: every condition shown in Spanish differs from the English one.
for e in entries:
    for ev in pokemon(e['id'])['evolution']:
        for c, ce in zip(ev['conditions'], ev['conditions_es']):
            assert ce and ce != c, ('Spanish condition fallback', e['id'], c)
# Alternate form names: no form shows its English name (Unown letters are spelled the same in both languages).
for e in entries:
    d = pokemon(e['id'])
    if d['id'] != d['species'] and not d['name'].startswith('Unown '):
        assert d['name_es'] and d['name_es'] != d['name'], ('Spanish form fallback', e['id'], d['name'])
# Pinned upstream has no Spanish text for some Gen IX abilities; those fall back to English text.
assert all(a['text'] for e in entries if e['species']>649 for a in pokemon(e['id'])['abilities'])
i18n=json.loads((r/'data/i18n_es.json').read_text()); assert len(i18n['types'])==18 and i18n['types']['Dark']=='Siniestro' and i18n['types']['Fairy']=='Hada'

assert pokemon(25)['stats'][2]==30 # Pre-Gen VI Defense.
assert 'Levitate' in [a['name'] for a in pokemon(94)['abilities']]
assert {a['name'] for a in pokemon(609)['abilities']}=={'Flash Fire','Flame Body','Shadow Tag'}
assert any(x['type']=='Dark' and x['factor']==.5 for x in pokemon(379)['matchups'])
assert len(entries)==1219 # 1109 Gen I-V dex entries/forms plus 110 Gen VI-IX alternate forms
# Gen VI-IX alternate forms: own record, sprite files and a cry (Gen V form rules are unchanged).
alt6=[e for e in entries if 10025<=e['id']<200000]
assert len(alt6)==110 and all((r/f"sprites/{e['id']}.png").exists() and (r/f"cries/{e['id']}.ogg").exists() for e in alt6)
assert {p.stem for p in (r/'data/pokemon').glob('*.json')}=={str(e['id']) for e in entries}
assert not any('Spiky-eared' in e['name'] or '???' in e['name'] for e in entries)
assert pokemon(210041)['types']==['Bug']
assert pokemon(210046)['types']==['Fire']
assert any(x['type']=='Water' and x['factor']==2 for x in pokemon(210046)['matchups'])
assert pokemon(1)['friendship']==70 # Species metadata before Gen VIII changes.
assert pokemon(51)['stats'][1]==80 # Dugtrio Attack before Gen VII.
assert pokemon(280)['types']==['Psychic']
assert pokemon(494)['unova']==0
assert pokemon(10022)['stats'][1]==170 and pokemon(10023)['stats'][3]==170
# Gen VI+ additions: Fairy typing and chart; species 650+ use the Gen VI+ chart, Gen V species do not.
assert pokemon(700)['types']==['Fairy'] and any(x['type']=='Dragon' and x['factor']==0 for x in pokemon(700)['matchups'])
assert not any(x['type']=='Fairy' for x in pokemon(35)['matchups'])
late=[e for e in default if e['id']>649]; assert len(late)==376 and all(e['unova']==-1 for e in late)
assert all(not pokemon(i)['black2'] and not pokemon(i)['white2'] and pokemon(i)['fallbackText'] for i in range(650,1026))
assert all(pokemon(i)['moves'] for i in range(650,1026))
assert all((r/f'cries/{i}.ogg').exists() and (r/f'sprites/shiny/{i}.png').exists() for i in range(650,1026))
assert pokemon(1025)['name']=='Pecharunt' and pokemon(1025)['national']==1025
print(f"DATA_OK: {len(default)} species, {len(regional)} regional entries, {len(entries)-len(default)} alternate forms, {manifest['sprites']} sprites; content hashes and Gen V regression checks passed")
