#!/usr/bin/env python3
"""Spanish names for regional forms and alternate forms that PokeAPI leaves untranslated.

Hisuian forms (see HISUI below) and the 13 Gen VIII-IX alternate forms still shown in English
(ALT_FORMS: Totem forms, Origin Formes, Female/Therian/Paldean/Hero/Roaming forms) are keyed by the
pokemon_forms.csv row id, which is what tools/fetch_data.py looks up. Each alternate form's Spanish
name is checked against the WikiDex species page (its wikitext must contain the name); when it does
not, the name is recorded as "translated".

Each WikiDex page titled "<species> de Hisui" (for example "Growlithe de Hisui") is checked; when it exists
and names Hisui, the form gets form_es "Forma de Hisui" with its URL in cache/es_fill.json under "forms",
keyed by PokeAPI form id. tools/fetch_data.py uses it only where PokeAPI has no Spanish form name.
"""
import argparse, csv, html, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'
OUT = CACHE / 'es_fill.json'
SITE = 'https://www.wikidex.net/wiki/'
UA = 'FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'
# PokeAPI form id -> species id for the Hisuian forms in the dex (form rows 10229-10244 in pokemon_forms.csv).
HISUI = {}
# pokemon_forms.csv row id -> (species id, Spanish form name, text the WikiDex species page must contain).
ALT_FORMS = {
    '10195': (20, 'Forma Tótem de Alola', 'forma tótem de alola'),
    '10268': (105, 'Forma Tótem', 'forma tótem'),
    '10414': (483, 'Forma Origen', 'Forma Origen'),
    '10415': (484, 'Forma Origen', 'Forma Origen'),
    '10417': (902, 'Hembra', 'Hembra'),
    '10418': (905, 'Forma Avatar', 'forma avatar'),
    '10419': (128, 'Tauros de Paldea (variedad combatiente)', 'variedad combatiente'),
    '10420': (128, 'Tauros de Paldea (variedad ardiente)', 'variedad ardiente'),
    '10421': (128, 'Tauros de Paldea (variedad acuática)', 'variedad acuática'),
    '10422': (194, 'Wooper de Paldea', 'Paldea'),
    '10423': (916, 'Hembra', 'Hembra'),
    '10425': (964, 'Forma Heroica', 'forma heroica'),
    '10432': (999, 'Forma Andante', 'forma andante'),
}


def api_text(title):
    """Current wikitext of a WikiDex page (empty string when missing)."""
    url = 'https://www.wikidex.net/api.php?' + urllib.parse.urlencode(dict(action='query', prop='revisions', rvprop='content', rvslots='main', titles=title, format='json'))
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60))
    page = list(d['query']['pages'].values())[0]
    return '' if 'missing' in page else page['revisions'][0]['slots']['main']['*']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fetch', action='store_true'); args = ap.parse_args()
    names_es = {}
    for r in csv.DictReader(open(CACHE / 'pokemon_species_names.csv', encoding='utf-8-sig')):
        if r['local_language_id'] == '7' and r['name']:
            names_es[int(r['pokemon_species_id'])] = r['name']
    for r in csv.DictReader(open(CACHE / 'pokemon_forms.csv', encoding='utf-8-sig')):
        if r['form_identifier'] == 'hisui':
            HISUI[r['id']] = int(r['pokemon_id'])
    # pokemon_forms uses pokemon ids; the species is the pokemon row's species (equal to the id for these).
    pk = {r['id']: r['species_id'] for r in csv.DictReader(open(CACHE / 'pokemon.csv', encoding='utf-8-sig'))}
    data = json.loads(OUT.read_text(encoding='utf-8'))
    forms = data.setdefault('forms', {})
    if args.fetch:
        for fid, pid in sorted(HISUI.items(), key=lambda kv: int(kv[0])):
            sid = int(pk[str(pid)])
            title = names_es.get(sid, '') + ' de Hisui'
            url = SITE + urllib.parse.quote(title.replace(' ', '_'))
            rec = {'species_es': names_es.get(sid, ''), 'title': title, 'url': url}
            try:
                page = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read().decode('utf-8')
                text = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', page, flags=re.S))).split())
                if 'Hisui' in text[:800]:
                    rec['form_es'] = 'Forma de Hisui'
                else:
                    rec['error'] = 'page does not name Hisui'
            except Exception as exc:
                rec['error'] = repr(exc)
            forms[fid] = rec
            time.sleep(0.4)
    if args.fetch or any(fid not in forms for fid in ALT_FORMS):
        for fid, (sid, form_es, check) in ALT_FORMS.items():
            species = names_es.get(sid, '')
            title = species
            url = SITE + urllib.parse.quote(title.replace(' ', '_'))
            rec = {'species_es': species, 'title': title, 'url': url, 'form_es': form_es}
            try:
                text = api_text(title)
                rec['status'] = 'wikidex' if check.lower() in text.lower() else 'translated'
                if rec['status'] == 'translated':
                    rec['note'] = 'WikiDex species page does not contain this form name'
            except Exception as exc:
                rec['status'] = 'translated'
                rec['error'] = repr(exc)
            forms[fid] = rec
            time.sleep(0.4)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('forms with form_es', sum(1 for r in forms.values() if r.get('form_es')), 'of', len(forms),
          '| alternate forms from WikiDex', sum(1 for fid in ALT_FORMS if forms.get(fid, {}).get('status') == 'wikidex'))


if __name__ == '__main__':
    main()
