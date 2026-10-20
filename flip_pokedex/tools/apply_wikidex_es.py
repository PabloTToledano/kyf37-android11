#!/usr/bin/env python3
"""Rerunnable patch: Spanish text from WikiDex (cache/es_fill.json).

- Gen IX abilities: official WikiDex Spanish name and text (status "wikidex", written by
  tools/scrape_es_wikidex_abilities.py) fill the PokeAPI gaps in tools/fetch_data.py.
- Black 2 / White 2 Spanish Pokedex entries for #1-649 (key "b2w2", written by
  tools/scrape_es_wikidex_b2w2.py) become black2_es / white2_es when WikiDex has them. Otherwise the
  existing CSV value (empty) is kept and fallbackText_es still holds the newest Spanish entry.
- tools/verify_data.py: every ability of every entry must have Spanish name and text.

A pair whose new text is already present is skipped; any other mismatch stops before writing.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / 'tools/fetch_data.py'
VERIFY = ROOT / 'tools/verify_data.py'

MERGE = """# Gen IX abilities: official WikiDex Spanish name and text (cache/es_fill.json, status "wikidex") fill PokeAPI gaps.
ES_FILL_ABILITIES=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8')).get('abilities',{}) if (CACHE/'es_fill.json').exists() else {}
_ability_id_by_en={v:k for k,v in ability_names.items()}
for _en,_rec in ES_FILL_ABILITIES.items():
    if _rec.get('status')=='wikidex' and _en in _ability_id_by_en:
        _aid=_ability_id_by_en[_en]
        if not ability_es.get(_aid): ability_es[_aid]=_rec['name_es']
        if not ability_text_es.get(_aid): ability_text_es[_aid]=_rec['text_es']
# Spanish Black 2 / White 2 entries from WikiDex (cache/es_fill.json key "b2w2").
ES_B2W2=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8')).get('b2w2',{}) if (CACHE/'es_fill.json').exists() else {}
def b2w2_es(sid,key): return ES_B2W2.get(str(sid),{}).get(key,'')
# Regional form names from WikiDex (cache/es_fill.json key "forms", tools/scrape_es_wikidex_forms.py).
ES_FILL_FORMS=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8')).get('forms',{}) if (CACHE/'es_fill.json').exists() else {}
eggs=defaultdict(list); eggs_es=defaultdict(list)"""

FETCH_PAIRS = [
    ("eggs=defaultdict(list); eggs_es=defaultdict(list)", MERGE),
    ("fes=form_names_es.get(form['id'],fn) if form else ''",
     "fes=(form_names_es.get(form['id']) or ES_FILL_FORMS.get(str(form['id']),{}).get('form_es') or fn) if form else ''"),
    ("'black2_es':fl.get(21,''),'white2_es':fl.get(22,'')",
     "'black2_es':b2w2_es(sid,'black2_es') or fl.get(21,''),'white2_es':b2w2_es(sid,'white2_es') or fl.get(22,'')"),
]

VERIFY_PAIRS = [
    ("assert all(a['name_es'] and (a['text_es'] or e['species']>649) for e in entries for a in pokemon(e['id'])['abilities'])",
     "assert all(a['name_es'] and a['text_es'] for e in entries for a in pokemon(e['id'])['abilities']), 'Spanish ability fallback'"),
]


def plan(path, pairs):
    text = path.read_text(encoding='utf-8')
    for old, new in pairs:
        if new in text:
            continue
        found = text.count(old)
        if found != 1:
            raise SystemExit(f'{path.name}: expected 1 match, found {found}: {old[:90]!r}')
        text = text.replace(old, new)
    return text


if __name__ == '__main__':
    for path, pairs in [(FETCH, FETCH_PAIRS), (VERIFY, VERIFY_PAIRS)]:
        path.write_text(plan(path, pairs), encoding='utf-8')
    print('patched', FETCH.name, VERIFY.name)
