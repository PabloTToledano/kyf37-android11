#!/usr/bin/env python3
"""Offline source-to-asset contract checks, including exclusives and null levels."""
import json
from pathlib import Path
from encounter_data import ROOT,CACHE,rows,build,METHODS,wild_links,parameters
assets=ROOT/'app/assets'; index=json.loads((assets/'data/index.json').read_text());ids={e['id'] for e in index}
result,report,games=build(ids)
assert {v for g in games for v in g['versions']}=={int(r['id']) for r in rows('versions')}
assert len([v for g in games for v in g['versions']])==len(rows('versions'))
for pid,expected in result.items():
    actual=json.loads((assets/f'data/pokemon/{pid}.json').read_text())['encounters']
    assert actual==expected,pid
    tuples={(r['version'],r['area'],r['method'],r['min'],r['max']) for r in actual}
    assert len(tuples)==len(actual),pid
    for r in actual:
        assert r['area_es'] and r['game_es'] and r['method_es']
        assert (r['min'] is None)==(r['max'] is None)
        if r['min'] is not None:assert 0<r['min']<=r['max']<=100,(pid,r)
# Parser must follow explicit aliases, ignore link pipes/nested templates, and
# never turn gifts, evolution or unknown pages into wild encounters.
fixture={'localizacion':'''{{Localización
| rojo = *''' + "'''[[Pokémon salvaje|Salvaje]]:''' [[Bosque Verde]] {{nota|a=b}}." + '''
* ''' + "'''Regalo:''' [[Ciudad Azulona]]." + '''
| azul = rojo
| amarillo = ''' + "'''Evolucionar:''' [[Pichu]]." + '''
}}'''}
assert wild_links(fixture,{'Bosque Verde','Ciudad Azulona','Pichu'})=={1:{('Bosque Verde','wild (unspecified)','Salvaje · método sin especificar')},2:{('Bosque Verde','wild (unspecified)','Salvaje · método sin especificar')}}
assert parameters(fixture['localizacion'])['azul']=='rojo'
# Species-level WikiDex rows must never leak into a regional/alternate form.
assert all(r['min'] is not None for pid,rs in result.items() if pid>1025 for r in rs)
# Known cross-generation/source regressions: old wild tables, Japanese Blue and
# Scarlet/Violet supplementary data must all survive, with honest unknown levels.
assert any(r['version']==1 and 'Bosque Verde' in r['area_es'] for r in result[25])
assert any(r['version']==46 for r in result[25])
assert any(r['version']==40 and r['min'] is None for r in result[25])
assert any(r['version']==42 for r in result[25])
fixture_dlc={'localizacion':"{{Localización\n| escarlata = *'''[[Pokémon salvaje|Salvaje]]:''' [[Monte Ogro]]\n| púrpura = escarlata\n}}"}
assert set(wild_links(fixture_dlc,{'Monte Ogro'},{'Monte Ogro':'noroteo'}))=={42,52}
assert not report['untranslated_locations'],report['untranslated_locations']
print('ENCOUNTER_TEST_OK: exact source rows, version coverage, deduplication, levels, Spanish labels, WikiDex aliases and exclusions')
