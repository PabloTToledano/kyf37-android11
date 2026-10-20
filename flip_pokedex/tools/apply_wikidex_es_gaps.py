#!/usr/bin/env python3
"""Rerunnable patch: Spanish gaps for Black 2 / White 2 areas, place-based conditions, move text and forms.

Reads cache/es_fill.json, written by tools/scrape_es_wikidex_locations.py, tools/scrape_es_wikidex_moves.py
and tools/scrape_es_wikidex_forms.py, and makes tools/fetch_data.py use it:
- "areas": each English encounter area string ("Location / sub-area") gets its Spanish area_es.
  Before this patch the area_es field was always empty, so the app showed English for every area.
- "locations": WikiDex names for Unova places, applied to evolution conditions that name a place
  (Mt. Coronet, Chargestone Cave) where PokeAPI has no Spanish name.
- "conditions": the remaining English evolution conditions (items and triggers).
- "moves": Spanish descriptions for the Gen IX moves that PokeAPI leaves without text.
- "forms": Spanish names of the 13 alternate forms (already read by fetch_data via ES_FILL_FORMS).
tools/verify_data.py asserts that none of these fields falls back to English.

Run after tools/apply_wikidex_es.py and tools/apply_es_fill.py (the chain is in README.md). A pair whose
new text is already present is skipped, so this script can be rerun safely. Any other mismatch stops
the run before anything is written.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / 'tools/fetch_data.py'
VERIFY = ROOT / 'tools/verify_data.py'

# Anchor: the last line of the block written by tools/apply_wikidex_es.py.
LOADERS = """# Spanish gaps from WikiDex (cache/es_fill.json; see tools/apply_wikidex_es_gaps.py for what each key feeds).
_ES_FILL_ALL=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8')) if (CACHE/'es_fill.json').exists() else {}
ES_AREA=_ES_FILL_ALL.get('areas',{}); ES_LOC=_ES_FILL_ALL.get('locations',{}); ES_COND=_ES_FILL_ALL.get('conditions',{}); ES_MOVES=_ES_FILL_ALL.get('moves',{})
eggs=defaultdict(list); eggs_es=defaultdict(list)"""

FETCH_PAIRS = [
    ("eggs=defaultdict(list); eggs_es=defaultdict(list)", LOADERS),
    # Move descriptions: PokeAPI has no Spanish text for these Gen IX moves.
    ("methods=idx('pokemon_move_methods'); learnsets=defaultdict(list)",
     "# Gen IX moves with no Spanish flavor text upstream: translated descriptions (cache key \"moves\").\n"
     "for _mid,_rec in ES_MOVES.items():\n"
     "    if _rec.get('text_es') and not move_text_es.get(_mid): move_text_es[_mid]=_rec['text_es']\n"
     "methods=idx('pokemon_move_methods'); learnsets=defaultdict(list)"),
    # Encounter areas: the Spanish area string comes from the cache, keyed by the English string.
    ("'area_es':(loc_label_es+(' / '+areanames[area['id']] if areanames.get(area['id']) else '')) if loc_label_es else ''",
     "'area_es':ES_AREA.get(locnames.get(area['location_id'],locations[area['location_id']]['identifier'])+(' / '+areanames[area['id']] if areanames.get(area['id']) else ''),{}).get('area_es','')"),
    # Place names used by evolution conditions (PokeAPI has no Spanish for these locations).
    ("triggers=idx('evolution_triggers'); evolutions=defaultdict(list); evolutions_es=defaultdict(list)",
     "# Unova and other place names with no PokeAPI Spanish: WikiDex names keyed by the English location name.\n"
     "loc_es.update({_lid:ES_LOC[_en]['name_es'] for _lid,_en in locnames.items() if _en in ES_LOC and ES_LOC[_en].get('name_es') and not loc_es.get(_lid)})\n"
     "triggers=idx('evolution_triggers'); evolutions=defaultdict(list); evolutions_es=defaultdict(list)"),
    # Remaining English evolution conditions (items and triggers), keyed by the English string.
    ("evolutions[sid].append(build(False)); evolutions_es[sid].append(build(True))",
     "evolutions[sid].append(build(False)); _cond_es=build(True); evolutions_es[sid].append(ES_COND.get(_cond_es,{}).get('condition_es',_cond_es))"),
]

VERIFY_PAIRS = [
    ("assert all(a['name_es'] and a['text_es'] for e in entries for a in pokemon(e['id'])['abilities']), 'Spanish ability fallback'",
     "assert all(a['name_es'] and a['text_es'] for e in entries for a in pokemon(e['id'])['abilities']), 'Spanish ability fallback'\n"
     "# Black 2 / White 2 encounter areas: every row has a Spanish area that is not the English string.\n"
     "for e in entries:\n"
     "    for enc in pokemon(e['id'])['encounters']:\n"
     "        assert enc['area_es'] and enc['area_es'] != enc['area'], ('Spanish area fallback', e['id'], enc['area'])\n"
     "# Move descriptions: every learnset row has Spanish text, and it is not the English text.\n"
     "for e in entries:\n"
     "    for mv in pokemon(e['id'])['moves']:\n"
     "        assert mv['text_es'] and (not mv['text'] or mv['text_es'] != mv['text']), ('Spanish move text fallback', e['id'], mv['name'])\n"
     "# Evolution conditions: every condition shown in Spanish differs from the English one.\n"
     "for e in entries:\n"
     "    for ev in pokemon(e['id'])['evolution']:\n"
     "        for c, ce in zip(ev['conditions'], ev['conditions_es']):\n"
     "            assert ce and ce != c, ('Spanish condition fallback', e['id'], c)\n"
     "# Alternate form names: no form shows its English name (Unown letters are spelled the same in both languages).\n"
     "for e in entries:\n"
     "    d = pokemon(e['id'])\n"
     "    if d['id'] != d['species'] and not d['name'].startswith('Unown '):\n"
     "        assert d['name_es'] and d['name_es'] != d['name'], ('Spanish form fallback', e['id'], d['name'])", 1),
]


def plan(path, pairs):
    text = path.read_text(encoding='utf-8')
    for pair in pairs:
        old, new = pair[0], pair[1]
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
