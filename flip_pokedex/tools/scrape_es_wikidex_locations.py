#!/usr/bin/env python3
"""Spanish Unova place names, Black 2 / White 2 encounter areas and place-based evolution conditions.

- Locations: the WikiDex pages under Categoría:Lugares de Teselia are walked through the MediaWiki API
  (categories are followed recursively). A page whose English interlanguage link names an English
  location used by the Black 2 / White 2 encounters or by an evolution gives its Spanish name, with
  the "(Teselia)" qualifier and alternative titles removed. Locations with no matching page are looked
  up by candidate title; the rest are translated here and recorded as "translated".
- Encounter areas: each English area string exactly as tools/fetch_data.py builds it ("Location /
  sub-area") gets a Spanish string from the Spanish location name plus the translated sub-area. The
  sub-area table below is ours (WikiDex has no per-floor list), so those areas are "translated".
- Evolution conditions: English strings that the Spanish mode would otherwise show in English.

Writes cache/es_fill.json keys "locations", "areas" and "conditions"; every entry records its WikiDex
page URL where one was used. Without --fetch only the cache and the cached CSVs are read.
"""
import argparse, csv, json, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'
OUT = CACHE / 'es_fill.json'
API = 'https://www.wikidex.net/api.php'
SITE = 'https://www.wikidex.net/wiki/'
UA = 'FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'
ROOT_CATEGORY = 'Categoría:Lugares de Teselia'
DELAY = 1.5

# English location names (as PokeAPI writes them) with no WikiDex page that names them: our translation.
TRANSLATED_LOCATIONS = {
    'Glacier Room': 'Sala Glaciar',
    'Iron Room': 'Sala Férrea',
    'Rocky Mountain Room': 'Sala Montaña Rocosa',
    'Nature Sanctuary': 'Santuario Natural',
}
# English location names matched by an existing WikiDex title (the English interlanguage link is absent).
TITLE_MATCH = {
    'Guidance Chamber': 'Cámara Orientación',
    'Victory Road': 'Calle Victoria',
    'Mt. Coronet': 'Monte Corona',
}
# Sub-area words translated by us (the Spanish games use these terms; WikiDex has no floor or room list).
NAME_ES = {
    'Relic Tunnel': 'Túnel Ancestral',
    'Weather Institute': 'Instituto Meteorológico',
    'Nacrene Museum': 'Museo Esmalte',
}
TAIL_ES = {
    '1F': 'Planta 1', '2F': 'Planta 2', '3F': 'Planta 3', '4F': 'Planta 4', '5F': 'Planta 5', '7F': 'Planta 7',
    'B1F': 'Sótano 1', 'B2F': 'Sótano 2', 'A': 'A', 'C': 'C', 'D': 'D',
    'entrance': 'entrada', 'outside': 'exterior', 'inside': 'interior', 'inner': 'interior', 'outer': 'exterior',
    'west gate': 'puerta oeste', 'forest': 'bosque', 'forest cave': 'cueva del bosque',
    'Hidden Grotto': 'Gruta oculta',
    'Hidden Grotto – Inner area': 'Gruta oculta – zona interior',
    'Hidden Grotto – Outer area': 'Gruta oculta – zona exterior',
    'Hidden Grotto – Near Youngster': 'Gruta oculta – cerca de Pillastre',
    'Hidden Grotto – Shrine': 'Gruta oculta – santuario',
    'Hidden Grotto – Giant Chasm': 'Gruta oculta – Cuenca Gigante',
    'Hidden Grotto – Stairs': 'Gruta oculta – escaleras',
    'Hidden Grotto – Dark Grass': 'Gruta oculta – hierba oscura',
    'Hidden Grotto – Pond': 'Gruta oculta – estanque',
    'Hidden Grotto – Mistralton Cave': 'Gruta oculta – Cueva Loza',
    'Hidden Grotto – Near Pokemon Breeder': 'Gruta oculta – cerca de Criador Pokémon',
    'Castelia Sewers entrance': 'entrada de Cloacas Porcelana',
    'PWT entrance': 'entrada del Pokémon World Tournament',
    'Relic Castle entrance': 'entrada de Castillo Ancestral',
    'Relic Castle entrance ': 'entrada de Castillo Ancestral',
}
# Spanish names for evolution conditions that the Spanish mode would otherwise show in English.
CONDITION_TRANSLATED = {
    'Three Defeated Bisharp': 'Tres Bisharp derrotados',
    'Use Move': 'Usar movimiento',
    'Gimmighoul Coins': 'Monedas Gimmighoul',
    'Meltan Candies': 'Caramelos Meltan',
}
# Item names: a WikiDex page under one of these candidate titles is used first (its title is the name).
CONDITION_CANDIDATES = {
    'Gimmighoul Coins': ['Monedas Gimmighoul', 'Moneda Gimmighoul'],
    'Meltan Candies': ['Caramelos Meltan', 'Caramelo Meltan'],
}


def api(**params):
    params.update(format='json', action='query')
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(6):
        time.sleep(DELAY)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError('WikiDex still rate-limiting after retries')


def category_pages(root):
    """Every article title below root, following subcategories (namespace 14) recursively."""
    pages, seen, stack = set(), set(), [root]
    while stack:
        cat = stack.pop()
        if cat in seen:
            continue
        seen.add(cat)
        cont = {}
        while True:
            d = api(list='categorymembers', cmtitle=cat, cmlimit=500, **cont)
            for m in d['query']['categorymembers']:
                if m['ns'] == 14:
                    stack.append(m['title'])
                else:
                    pages.add(m['title'])
            if 'continue' not in d:
                break
            cont = d['continue']
    return sorted(pages)


def langlinks(titles):
    out = {}
    for i in range(0, len(titles), 50):
        d = api(prop='langlinks', lllang='en', lllimit=500, titles='|'.join(titles[i:i + 50]))
        for p in d['query']['pages'].values():
            out[p['title']] = [l['*'] for l in p.get('langlinks', [])]
    return out


def existing_titles(titles):
    d = api(titles='|'.join(titles))
    return {p['title'] for p in d['query']['pages'].values() if 'missing' not in p}


def en_key(title):
    """English interlanguage title -> PokeAPI location name ("Unova Route 1" -> "Route 1")."""
    t = title.replace(' (Pokémon)', '')
    return t[6:] if t.startswith('Unova ') else t


def spanish_title(title):
    return re.sub(r'\s*\((Teselia|Unova)\)$', '', title).split('/')[0].strip()


def tail_es(tail):
    if tail in TAIL_ES:
        return TAIL_ES[tail]
    m = re.fullmatch(r'unknown area (\d+)', tail)
    if m:
        return f'zona desconocida {m.group(1)}'
    m = re.fullmatch(r'Road (\d+)', tail)
    if m:
        return f'Ruta {m.group(1)}'
    raise KeyError(f'no Spanish for area tail {tail!r}')


def translate_prose(prose, loc_en, loc_es):
    """Spanish sub-area name for an English sub-area string, built on the Spanish location name."""
    m = re.fullmatch(r'Road (\d+)', prose)
    if m:
        return f'Ruta {m.group(1)}'
    m = re.fullmatch(r'(.+?) \((.+)\)', prose)
    name, tail = (m.group(1), m.group(2)) if m else (prose, None)
    if name == loc_en or name.startswith(loc_en + ' '):
        name_es = loc_es + name[len(loc_en):]
    else:
        name_es = NAME_ES[name]
    return name_es if tail is None else f'{name_es} ({tail_es(tail)})'


def read_csv(name):
    return list(csv.DictReader(open(CACHE / name, encoding='utf-8-sig')))


def english_areas():
    """Encounter areas for Black 2 (21) and White 2 (22), keyed as tools/fetch_data.py keys them."""
    loc_name = {int(r['id']): r['identifier'] for r in read_csv('locations.csv')}
    for r in read_csv('location_names.csv'):
        if r['local_language_id'] == '9':
            loc_name[int(r['location_id'])] = r['name']
    areas = {int(r['id']): r for r in read_csv('location_areas.csv')}
    prose = {int(r['location_area_id']): r['name'] for r in read_csv('location_area_prose.csv') if r['local_language_id'] == '9'}
    found = {}
    for r in read_csv('encounters.csv'):
        if r['version_id'] not in ('21', '22'):
            continue
        area = areas[int(r['location_area_id'])]
        loc_id = int(area['location_id'])
        loc = loc_name[loc_id]
        sub = prose.get(int(area['id']))
        found[loc + (' / ' + sub if sub else '')] = (loc_id, loc, sub)
    return found


def pokeapi_spanish_locations():
    return {int(r['location_id']): r['name'] for r in read_csv('location_names.csv') if r['local_language_id'] == '7' and r['name']}


def build_location_map(needed, fetch):
    """English location name -> record, from WikiDex (fetch) or the cache."""
    data = json.loads(OUT.read_text(encoding='utf-8'))
    locs = data.setdefault('locations', {})
    if fetch:
        ll = {}
        pages = category_pages(ROOT_CATEGORY)
        ll = langlinks(pages)
        by_en = {}
        for title in pages:
            for en in ll.get(title, []):
                by_en.setdefault(en_key(en), (title, SITE + urllib.parse.quote(title.replace(' ', '_'))))
        missing = [en for en in needed if en not in by_en and en not in TRANSLATED_LOCATIONS]
        cands = {en: TITLE_MATCH[en] for en in missing if en in TITLE_MATCH}
        found_titles = existing_titles(list(cands.values())) if cands else set()
        for en in needed:
            if en in by_en:
                title, url = by_en[en]
                locs[en] = {'name_es': spanish_title(title), 'url': url, 'wikidex_title': title, 'status': 'wikidex'}
            elif en in TITLE_MATCH and TITLE_MATCH[en] in found_titles:
                title = TITLE_MATCH[en]
                locs[en] = {'name_es': spanish_title(title), 'url': SITE + urllib.parse.quote(title.replace(' ', '_')),
                            'wikidex_title': title, 'status': 'wikidex', 'note': 'matched by title, no English link on the page'}
            elif en in TRANSLATED_LOCATIONS:
                locs[en] = {'name_es': TRANSLATED_LOCATIONS[en], 'status': 'translated',
                            'note': 'no WikiDex page names this location'}
            else:
                locs[en] = {'name_es': '', 'status': 'missing', 'note': 'no WikiDex page and no translation'}
    return data, locs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='query WikiDex (otherwise use the cache only)')
    args = ap.parse_args()
    areas = english_areas()
    loc_ids_es = pokeapi_spanish_locations()
    needed = sorted({loc for _, (lid, loc, _) in areas.items() if lid not in loc_ids_es})
    needed = sorted(set(needed) | {'Mt. Coronet', 'Chargestone Cave'})
    data, locs = build_location_map(needed, args.fetch)
    # Areas are rebuilt from the cached location names on every run, so this step is offline.
    out_areas = {}
    unresolved = []
    for key, (lid, loc, sub) in sorted(areas.items()):
        if lid in loc_ids_es:
            loc_es, loc_status, loc_url = loc_ids_es[lid], 'pokeapi', ''
        else:
            rec = locs.get(loc, {})
            loc_es, loc_status, loc_url = rec.get('name_es', ''), rec.get('status', 'missing'), rec.get('url', '')
        if not loc_es:
            unresolved.append(key)
            continue
        if sub:
            try:
                prose_es = translate_prose(sub, loc, loc_es)
            except KeyError as exc:
                unresolved.append(f'{key} ({exc})')
                continue
            area_es = loc_es if prose_es == loc_es else f'{loc_es} / {prose_es}'
            status = loc_status if prose_es == loc_es else 'translated'
        else:
            area_es, status = loc_es, loc_status
        out_areas[key] = {'area_es': area_es, 'status': status, 'location_en': loc, 'location_es': loc_es,
                          'location_status': loc_status, 'url': loc_url}
    data['areas'] = out_areas
    # Evolution conditions: the Spanish mode only ever shows these English strings.
    conds = data.setdefault('conditions', {})
    for en, es in CONDITION_TRANSLATED.items():
        if conds.get(en, {}).get('status') != 'wikidex':
            conds[en] = {'condition_es': es, 'status': 'translated'}
    if args.fetch:
        for en, titles in CONDITION_CANDIDATES.items():
            hit = next((t for t in titles if t in existing_titles([t])), None)
            if hit:
                conds[en] = {'condition_es': hit, 'status': 'wikidex', 'wikidex_title': hit,
                             'url': SITE + urllib.parse.quote(hit.replace(' ', '_'))}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    by = {}
    for r in out_areas.values():
        by[r['status']] = by.get(r['status'], 0) + 1
    print('areas', len(out_areas), 'by status', by, 'unresolved', unresolved)
    print('locations', {k: sum(1 for v in locs.values() if v.get('status') == k) for k in ('wikidex', 'translated', 'missing')})
    print('conditions', len(conds))


if __name__ == '__main__':
    main()
