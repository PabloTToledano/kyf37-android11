#!/usr/bin/env python3
"""Rerunnable patch: Spanish gap fill (cache/es_fill.json) and owner UI fixes.

- Merges the WikiDex Spanish genus and Pokedex text for #899-1025 (cache/es_fill.json, built by
  tools/scrape_es_wikidex.py) into tools/fetch_data.py output. Only empty PokeAPI fields are filled.
- Extends tools/verify_data.py to require Spanish genus and entry text for all 1,025 species.
- Canonical UI in templates/src/org/kyf37/pokedex/PokedexActivity.java:
  "Shiny" in Spanish is "Variocolor" (not "Brillo"/"Brillante"), and the "TEXTO DE OTRO JUEGO" /
  "TEXT FROM ANOTHER GAME" header is removed, so only the entry text is shown.

Run after tools/apply_spanish_ui.py and tools/apply_national_1025.py on a fresh tree; those scripts
still write the earlier wording, which this script replaces. A pair whose new text is already
present is skipped, so this script can be rerun safely. Any other mismatch stops the run before
anything is written.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / 'templates/src/org/kyf37/pokedex/PokedexActivity.java'


def plan(path, pairs):
    text = path.read_text(encoding='utf-8')
    for old, new, count in pairs:
        # Insertions keep their anchor (old is inside new), so "new present" is the applied test.
        if new in text:
            continue
        found = text.count(old)
        if found != count:
            raise SystemExit(f'{path.name}: expected {count} match(es), found {found}: {old[:90]!r}')
        text = text.replace(old, new)
    return text


FETCH = [
    ("names_es=spanish('pokemon_species_names','pokemon_species_id')",
     "# Spanish genus and Pokedex text for species with none in PokeAPI (see tools/scrape_es_wikidex.py).\n"
     "ES_FILL=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8'))['species'] if (CACHE/'es_fill.json').exists() else {}\n"
     "names_es=spanish('pokemon_species_names','pokemon_species_id')", 1),
    ("'genus_es':genera_es.get(sid,'')",
     "'genus_es':genera_es.get(sid) or ES_FILL.get(str(sid),{}).get('genus_es','')", 1),
    ("fb=fl[max(fl)] if fl else ''",
     "fb=fl[max(fl)] if fl else ES_FILL.get(str(sid),{}).get('flavor_es','')", 1),
]

VERIFY = [
    ("assert all(pokemon(i)['name_es'] and pokemon(i)['genus_es'] and pokemon(i)['fallbackText_es'] for i in range(1,899))\n"
     "# Pinned upstream CSVs have Spanish names but no Spanish genus or flavor text for #899-1025; the app shows English there.\n"
     "assert all(pokemon(i)['name_es'] for i in range(1,1026))",
     "assert all(pokemon(i)['name_es'] and pokemon(i)['genus_es'] and pokemon(i)['fallbackText_es'] for i in range(1,1026))\n"
     "# #899-1025 Spanish genus and entry text come from cache/es_fill.json (WikiDex; source URLs stored there).", 1),
]

UI_PAIRS = [
    ('return new String[]{other,"TEXTO DE OTRO JUEGO"};', 'return new String[]{other,""};', 1),
    ('later?tr("TEXT FROM ANOTHER GAME","TEXTO DE OTRO JUEGO"):tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")',
     'later?"":tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")', 1),
    ('"# brillante · * opciones · Clear vuelve"', '"# variocolor · * opciones · Clear vuelve"', 1),
    ('(shiny?tr(" Shiny."," Brillante."):', '(shiny?tr(" Shiny."," Variocolor."):', 1),
    ('tr("SHINY","BRILLANTE")', 'tr("SHINY","VARIOCOLOR")', 1),
    ('screen==1?tr("Shiny","Brillo")', 'screen==1?tr("Shiny","Variocolor")', 1),
]


def main():
    tree = {
        ROOT / 'tools/fetch_data.py': FETCH,
        ROOT / 'tools/verify_data.py': VERIFY,
        UI: UI_PAIRS,
    }
    results = {path: plan(path, pairs) for path, pairs in tree.items()}
    for path, text in results.items():
        path.write_text(text, encoding='utf-8')
        print('patched', path.relative_to(ROOT))


if __name__ == '__main__':
    main()
