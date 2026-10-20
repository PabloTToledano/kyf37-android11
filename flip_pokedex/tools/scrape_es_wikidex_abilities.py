#!/usr/bin/env python3
"""Fill Spanish ability text from WikiDex for the Gen IX abilities that PokeAPI leaves untranslated.

For each ability in cache/es_fill.json, the WikiDex page titled with the Spanish name is read and its
"Efecto" section (WikiDex's official Spanish effect text) is stored as text_es with status "wikidex"
and the page URL. Abilities without a usable WikiDex page keep the existing translation, marked
status "translated", and are shown in the app as the translation (owner rule: Spanish everywhere).
Run with --fetch to query WikiDex; without it the script only reports coverage from the cache.
"""
import argparse, html, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cache' / 'es_fill.json'
SITE = 'https://www.wikidex.net/wiki/'
UA = 'FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'


def fetch(title):
    url = SITE + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return url, r.read().decode('utf-8')


def efecto(page, title):
    """Return the text of the 'Efecto' section, or ''. The section ends at the 'Pokémon con <title>' heading."""
    page = re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S)
    text = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', page)).split())
    start = text.find('Efecto [ editar código | editar ] ')
    if start < 0:
        return ''
    chunk = text[start + len('Efecto [ editar código | editar ] '):]
    end = chunk.find(' Pokémon con ' + title + ' [ editar')
    if end < 0:
        end = chunk.find(' [ editar código')
    return chunk[:end].replace('[ editar código | editar ]', '').strip() if end > 0 else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    args = ap.parse_args()
    data = json.loads(OUT.read_text(encoding='utf-8'))
    for name, rec in sorted(data['abilities'].items()):
        if rec.get('status') == 'wikidex' or not args.fetch:
            continue
        title = rec['name_es']
        try:
            url, page = fetch(title)
            text = efecto(page, title)
        except Exception as exc:
            text, url = '', SITE + title.replace(' ', '_')
            rec['error'] = repr(exc)
        if text:
            rec.update({'name_es': title, 'text_es': text, 'status': 'wikidex', 'url': url})
        else:
            rec.setdefault('error', 'no Efecto section')
        print(name, '->', title, rec['status'], flush=True)
        time.sleep(0.6)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    done = sum(1 for r in data['abilities'].values() if r.get('status') == 'wikidex')
    print('wikidex', done, 'of', len(data['abilities']))


if __name__ == '__main__':
    main()
