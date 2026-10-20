#!/usr/bin/env python3
"""Spanish Black 2 / White 2 Pokedex entries for #1-649 from the Spanish WikiDex.

Reads each species page's main-series table and stores the "Negro 2" and "Blanco 2" texts in
cache/es_fill.json under "b2w2" (with the page URL). Placeholder rows ("... no aparece en ...") are
stored as absent. tools/fetch_data.py merges them into black2_es / white2_es; missing entries keep the
existing behaviour (fallbackText_es is the newest Spanish entry). Run with --fetch to query WikiDex.
"""
import argparse, csv, json, re, time
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'
OUT = CACHE / 'es_fill.json'
_spec = importlib.util.spec_from_file_location('scrape_es', ROOT / 'tools/scrape_es_wikidex.py')
S = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(S)
GAMES = {'Negro 2': 'black2_es', 'Blanco 2': 'white2_es'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--only'); args = ap.parse_args()
    names_es = {}
    for r in csv.DictReader(open(CACHE / 'pokemon_species_names.csv', encoding='utf-8-sig')):
        if r['local_language_id'] == '7' and r['name']:
            names_es[int(r['pokemon_species_id'])] = r['name']
    data = json.loads(OUT.read_text(encoding='utf-8'))
    b2 = data.setdefault('b2w2', {})
    wanted = [int(x) for x in args.only.split(',')] if args.only else range(1, 650)
    if args.fetch:
        for sid in wanted:
            if str(sid) in b2 and 'error' not in b2[str(sid)]:
                continue
            title = names_es.get(sid)
            rec = {'name_es': title}
            try:
                url, page = S.fetch(title)
                _, entries = S.parse_species(page)
                rec['url'] = url
                for game, key in GAMES.items():
                    txt = entries.get(game, '')
                    if txt and not S.PLACEHOLDER.search(txt):
                        rec[key] = txt
            except Exception as exc:
                rec['error'] = repr(exc)
            b2[str(sid)] = rec
            if sid % 50 == 0 or 'error' in rec:
                print(sid, title, rec.get('error', ''), flush=True)
                OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            time.sleep(0.5)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    have_b = sum(1 for r in b2.values() if r.get('black2_es'))
    have_w = sum(1 for r in b2.values() if r.get('white2_es'))
    print('black2_es', have_b, 'white2_es', have_w, 'species fetched', len(b2))


if __name__ == '__main__':
    main()
