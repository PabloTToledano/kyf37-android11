#!/usr/bin/env python3
"""Rerunnable patch: extends the Pokedex from 649 to 1025 National species (Gen VI-IX).

Edits exact text in tools/fetch_data.py, tools/verify_data.py, tools/DexLogicTest.java and
templates/src/org/kyf37/pokedex/PokedexActivity.java. A pair whose new text is already present
(and whose old text is gone) is skipped, so the script can be rerun safely. Any other mismatch
stops the run before anything is written. Gen V (1-649) rules and the B2W2 dex stay unchanged.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'templates/src/org/kyf37/pokedex'


def plan(path, pairs):
    """Return the patched text, or raise if a pair does not match exactly once."""
    text = path.read_text(encoding='utf-8')
    for old, new, count in pairs:
        # Insertions keep their anchor (old is inside new), so "new present" is the applied test.
        if new in text:
            continue
        found = text.count(old)
        if count is None:
            if found < 1:
                raise SystemExit(f'{path.name}: no match for {old[:90]!r}')
        elif found != count:
            raise SystemExit(f'{path.name}: expected {count} match(es), found {found}: {old[:90]!r}')
        text = text.replace(old, new)
    return text


FETCH = [
    ("ids = {str(i) for i in range(1,650)} | set(forms)",
     "ids = {str(i) for i in range(1,1026)} | set(forms)", 1),
    # Past-generation rows only describe Gen V-era species; species 650+ use current data.
    ("for r in T['pokemon_types_past']:\n    if int(r['generation_id'])>=5: groups[r['pokemon_id']][int(r['generation_id'])].append(r)",
     "for r in T['pokemon_types_past']:\n    if int(r['generation_id'])>=5 and int(pokemon[r['pokemon_id']]['species_id'])<=649: groups[r['pokemon_id']][int(r['generation_id'])].append(r)", 1),
    ("for r in T['pokemon_abilities_past']:\n    if int(r['generation_id'])>=5: ability_history[r['pokemon_id'],r['slot']].append(r)",
     "for r in T['pokemon_abilities_past']:\n    if int(r['generation_id'])>=5 and int(pokemon[r['pokemon_id']]['species_id'])<=649: ability_history[r['pokemon_id'],r['slot']].append(r)", 1),
    ("for pid in ids:\n    past=defaultdict(list)",
     "for pid in [p for p in ids if int(pokemon[p]['species_id'])<=649]:\n    past=defaultdict(list)", 1),
    # English flavor text: species 650+ take their newest English entry, whatever the version.
    ("    if r['language_id']=='9' and int(r['version_id'])<=22: flavors[r['species_id']][r['version_id']]=' '.join(r['flavor_text'].split())",
     "    if r['language_id']=='9' and (int(r['version_id'])<=22 or int(r['species_id'])>649): flavors[r['species_id']][r['version_id']]=' '.join(r['flavor_text'].split())", 1),
    ("    if r['language_id']=='9' and int(r['version_group_id'])<=14: ability_text[r['ability_id']]=' '.join(r['flavor_text'].split())",
     "    if r['language_id']=='9' and int(r['version_group_id'])<=14: ability_text[r['ability_id']]=' '.join(r['flavor_text'].split())\n"
     "ability_text_latest={}\nfor r in sorted(T['ability_flavor_text'],key=lambda r:int(r['version_group_id'])):\n"
     "    if r['language_id']=='9': ability_text_latest[r['ability_id']]=' '.join(r['flavor_text'].split())", 1),
    ("'text':ability_text.get(r['ability_id'],'')} for r in abilities[pid]",
     "'text':(ability_text_latest if int(sid)>649 else ability_text).get(r['ability_id'],'')} for r in abilities[pid]", 1),
    ("'fallbackText':next(reversed(flavors[sid].values()),'') if flavors[sid] else ''",
     "'fallbackText':(flavors[sid][max(flavors[sid],key=int)] if int(sid)>649 and flavors[sid] else (next(reversed(flavors[sid].values()),'') if flavors[sid] else ''))", 1),
    # Moves: keep the pre-change snapshot so species 650+ get current type/power/accuracy.
    ("for mid,r in move_data.items():\n    changes=",
     "move_current={k:dict(v) for k,v in move_data.items()}\nfor mid,r in move_data.items():\n    changes=", 1),
    ("machines={r['move_id']:r['machine_number'] for r in T['machines'] if r['version_group_id']=='14'}\n"
     "for r in T['pokemon_moves']:\n    if r['version_group_id']=='14' and r['pokemon_id'] in ids:\n"
     "        m=move_data[r['move_id']]; method=methods[r['pokemon_move_method_id']]['identifier']",
     "move_text_latest={}\nfor r in sorted(T['move_flavor_text'],key=lambda r:int(r['version_group_id'])):\n"
     "    if r['language_id']=='9': move_text_latest[r['move_id']]=' '.join(r['flavor_text'].split())\n"
     "machines_by_vg=defaultdict(dict)\nfor r in T['machines']: machines_by_vg[r['version_group_id']][r['move_id']]=r['machine_number']\n"
     "# Species 650+ have no B2W2 learnset: use the newest version group that records their moves.\n"
     "newest_vg={}\nfor r in T['pokemon_moves']:\n    if r['pokemon_id'] in ids and int(pokemon[r['pokemon_id']]['species_id'])>649:\n"
     "        newest_vg[r['pokemon_id']]=max(newest_vg.get(r['pokemon_id'],0),int(r['version_group_id']))\n"
     "for r in T['pokemon_moves']:\n    pid=r['pokemon_id']\n    if pid not in ids: continue\n"
     "    late=int(pokemon[pid]['species_id'])>649; vg=str(newest_vg[pid]) if late else '14'\n"
     "    if r['version_group_id']==vg:\n"
     "        m=(move_current if late else move_data)[r['move_id']]; method=methods[r['pokemon_move_method_id']]['identifier']", 1),
    ("'machine':machines.get(r['move_id'],'')", "'machine':machines_by_vg[vg].get(r['move_id'],'')", 1),
    ("'text':move_text.get(r['move_id'],'')", "'text':(move_text_latest if late else move_text).get(r['move_id'],'')", 1),
    # Evolutions: species 650+ keep current rules; Gen V filters apply only to species 1-649.
    ("    sid=r['evolved_species_id']\n"
     "    if int(sid)>649 or int(version_groups[r['version_group_id']]['generation_id'])>5: continue\n"
     "    if r.get('region_id') and r['region_id']!='5': continue\n"
     "    if r.get('evolved_pokemon_form_id') and r['evolved_pokemon_form_id'] not in {f['id'] for f in era_forms}: continue\n"
     "    # Later evolution methods for old species are not part of Gen V.\n"
     "    if r.get('trigger_item_id') and int(idx('items')[r['trigger_item_id']]['id'])>700: continue",
     "    sid=r['evolved_species_id']\n"
     "    if int(sid)>1025: continue\n"
     "    gen5_row=int(sid)<=649\n"
     "    if gen5_row and int(version_groups[r['version_group_id']]['generation_id'])>5: continue\n"
     "    if gen5_row and r.get('region_id') and r['region_id']!='5': continue\n"
     "    if gen5_row and r.get('evolved_pokemon_form_id') and r['evolved_pokemon_form_id'] not in {f['id'] for f in era_forms}: continue\n"
     "    # Later evolution methods for old species are not part of Gen V.\n"
     "    if gen5_row and r.get('trigger_item_id') and int(idx('items')[r['trigger_item_id']]['id'])>700: continue", 1),
    ("bits.append(L[key]+('220' if k=='minimum_happiness' else r[k]))",
     "bits.append(L[key]+('220' if k=='minimum_happiness' and int(sid)<=649 else r[k]))", 1),
    ("for qid,q in species.items() if int(qid)<=649 and q['evolution_chain_id']==s['evolution_chain_id']]",
     "for qid,q in species.items() if int(qid)<=(1025 if int(sid)>649 else 649) and q['evolution_chain_id']==s['evolution_chain_id']]", 1),
    # Type chart: Gen VI+ (with Fairy) for species 650+; the Gen V chart stays for 1-649.
    ("(ASSETS/'data/pokemon').mkdir(parents=True,exist_ok=True)",
     "efficacy_modern={(r['damage_type_id'],r['target_type_id']):int(r['damage_factor']) for r in T['type_efficacy'] if int(r['damage_type_id'])<=18 and int(r['target_type_id'])<=18}\n"
     "(ASSETS/'data/pokemon').mkdir(parents=True,exist_ok=True)", 1),
    ("    weak=[]\n    for atk in range(1,18):\n        mult=1\n        for t in ts: mult*=efficacy.get((str(atk),t['type_id']),100)/100",
     "    weak=[]\n    chart,attackers=(efficacy_modern,19) if int(sid)>649 else (efficacy,18)\n    for atk in range(1,attackers):\n        mult=1\n        for t in ts: mult*=chart.get((str(atk),t['type_id']),100)/100", 1),
    ("'types':{type_names[k]:type_es[k] for k in type_names if k in type_es and int(k)<=17}",
     "'types':{type_names[k]:type_es[k] for k in type_names if k in type_es and int(k)<=18}", 1),
    # Static front and shiny sprites for 650+ (no Gen V animation, back or female sets exist for them).
    ("selected_paths={dest for _,dest in selected}",
     "for n in range(650,1026):\n    for sub in ['','shiny/']:\n"
     "        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+str(n)+'.png',ASSETS/'sprites'/(sub+str(n)+'.png')))\n"
     "selected_paths={dest for _,dest in selected}", 1),
    # Latest cries (not the legacy set) for 650+.
    ("with ThreadPoolExecutor(max_workers=6) as ex:",
     "cries+=[(BASE+'cries/'+PINS['cries']+'/cries/pokemon/latest/'+str(n)+'.ogg',ASSETS/'cries'/(str(n)+'.ogg')) for n in range(650,1026)]\n"
     "with ThreadPoolExecutor(max_workers=6) as ex:", 1),
    # The pinned Gen V tree also holds animated, female and back files for some 650+ numbers. Species 650+
    # must use only static front/back sprites (the app falls back from missing animations to static).
    ("    if r['type']=='blob' and stem in ids|extra_stems and Path(path).suffix in ['.png','.gif']:",
     "    if r['type']=='blob' and stem in ids|extra_stems and not (stem.isdigit() and 650<=int(stem)<=1025) and Path(path).suffix in ['.png','.gif']:", 1),
    ("    for sub in ['','shiny/']:\n        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+str(n)+'.png',ASSETS/'sprites'/(sub+str(n)+'.png')))",
     "    for sub in ['','shiny/','back/','back/shiny/']:\n        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+str(n)+'.png',ASSETS/'sprites'/(sub+str(n)+'.png')))", 1),
    ("'notes':['Gen V B2W2 version group 14; Black 2 version 21 / White 2 version 22.',",
     "'notes':['Species 650-1025 (Gen VI-IX): newest recorded version group, current stats/types/moves/abilities, latest flavor text, static sprites and latest cries.', 'Gen V B2W2 version group 14; Black 2 version 21 / White 2 version 22.',", 1),
]

VERIFY = [
    ("assert {e['id'] for e in default}==set(range(1,650))",
     "assert {e['id'] for e in default}==set(range(1,1026))", 1),
    ("assert len(entries)==733", "assert len(entries)==1109", 1),
    ("for i in range(1,650))\nassert all(a['name_es']",
     "for i in range(1,1026))\nassert all(a['name_es']", None),
    ("assert len(i18n['types'])==17 and i18n['types']['Dark']=='Siniestro'",
     "assert len(i18n['types'])==18 and i18n['types']['Dark']=='Siniestro' and i18n['types']['Fairy']=='Hada'", 1),
    ("assert all(pokemon(i)['name_es'] and pokemon(i)['genus_es'] and pokemon(i)['fallbackText_es'] for i in range(1,1026))",
     "assert all(pokemon(i)['name_es'] and pokemon(i)['genus_es'] and pokemon(i)['fallbackText_es'] for i in range(1,899))\n"
     "# Pinned upstream CSVs have Spanish names but no Spanish genus or flavor text for #899-1025; the app shows English there.\n"
     "assert all(pokemon(i)['name_es'] for i in range(1,1026))", 1),
    ("assert all(a['name_es'] and a['text_es'] for e in entries for a in pokemon(e['id'])['abilities'])",
     "assert all(a['name_es'] and (a['text_es'] or e['species']>649) for e in entries for a in pokemon(e['id'])['abilities'])\n"
     "# Pinned upstream has no Spanish text for some Gen IX abilities; those fall back to English text.\n"
     "assert all(a['text'] for e in entries if e['species']>649 for a in pokemon(e['id'])['abilities'])", 1),
    ("print(f\"DATA_OK:",
     "# Gen VI+ additions: Fairy typing and chart; species 650+ use the Gen VI+ chart, Gen V species do not.\n"
     "assert pokemon(700)['types']==['Fairy'] and any(x['type']=='Dragon' and x['factor']==0 for x in pokemon(700)['matchups'])\n"
     "assert not any(x['type']=='Fairy' for x in pokemon(35)['matchups'])\n"
     "late=[e for e in default if e['id']>649]; assert len(late)==376 and all(e['unova']==-1 for e in late)\n"
     "assert all(not pokemon(i)['black2'] and not pokemon(i)['white2'] and pokemon(i)['fallbackText'] for i in range(650,1026))\n"
     "assert all(pokemon(i)['moves'] for i in range(650,1026))\n"
     "assert all((r/f'cries/{i}.ogg').exists() and (r/f'sprites/shiny/{i}.png').exists() for i in range(650,1026))\n"
     "assert pokemon(1025)['name']=='Pecharunt' and pokemon(1025)['national']==1025\n"
     "print(f\"DATA_OK:", 1),
]

TESTS = [
    ('check(!DexLogic.matches("Pikachu",25,"999999999999",false));',
     'check(!DexLogic.matches("Pikachu",25,"999999999999",false));\n'
     '        check(DexLogic.matches("Pecharunt",1025,"1025",false));\n'
     '        check(!DexLogic.matches("Pecharunt",1025,"102",false));', 1),
]

POKEDEX = [
    ('final String[] typeOptions={"All types","Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark"};',
     'final String[] typeOptions={"All types","Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark","Fairy"};', 1),
    ('String[] names={"Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark"};',
     'String[] names={"Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark","Fairy"};', 1),
    ('0xff7163af,0xff625954};', '0xff7163af,0xff625954,0xffbd6f8f};', 1),
    ('if(query.length()<12){query+=(k-KeyEvent.KEYCODE_0);rebuild(selectedId());}',
     'if(query.length()<(searchName?12:4)){query+=(k-KeyEvent.KEYCODE_0);rebuild(selectedId());}', 1),
    ('tr("NATIONAL / 649","NACIONAL / 649")', 'tr("NATIONAL / 1025","NACIONAL / 1025")', 1),
    ('tr("National · 649","Nacional · 649")', 'tr("National · 1025","Nacional · 1025")', 1),
    ('text(c,tr("DEFENSIVE TYPE MATCHUPS / GEN V","DEBILIDADES Y RESISTENCIAS / GEN V"),32,473,14,accent);',
     'boolean later=detail.optInt("species")>649;text(c,later?tr("DEFENSIVE TYPE MATCHUPS / GEN VI+","DEBILIDADES Y RESISTENCIAS / GEN VI+"):tr("DEFENSIVE TYPE MATCHUPS / GEN V","DEBILIDADES Y RESISTENCIAS / GEN V"),32,473,14,accent);', 1),
    ('text(c,tr("Steel retains Ghost / Dark resistance.","Acero conserva resistencia a Fantasma / Siniestro."),32,718,14,muted);',
     'if(!later)text(c,tr("Steel retains Ghost / Dark resistance.","Acero conserva resistencia a Fantasma / Siniestro."),32,718,14,muted);', 1),
    ('text(c,tr("B2·W2 LEARNSET · ","APRENDIZAJE B2·W2 · ")+moves.length()+tr(" RECORDS"," MOVIMIENTOS"),32,474,14,accent);',
     'text(c,(detail.optInt("species")>649?tr("NEWEST GAMES LEARNSET · ","APRENDIZAJE DE JUEGOS RECIENTES · "):tr("B2·W2 LEARNSET · ","APRENDIZAJE B2·W2 · "))+moves.length()+tr(" RECORDS"," MOVIMIENTOS"),32,474,14,accent);', 1),
    ('tr("EVOLUTION FAMILY / GEN V","FAMILIA EVOLUTIVA / GEN V")',
     '(detail.optInt("species")>649?tr("EVOLUTION FAMILY / GEN VI+","FAMILIA EVOLUTIVA / GEN VI+"):tr("EVOLUTION FAMILY / GEN V","FAMILIA EVOLUTIVA / GEN V"))', 1),
    ('return new String[]{detail.optString("fallbackText"),tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")};',
     'boolean later=detail.optInt("species")>649;return new String[]{detail.optString("fallbackText"),later?tr("TEXT FROM ANOTHER GAME","TEXTO DE OTRO JUEGO"):tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")};', 1),
    ('"Sprites: PokeAPI/sprites (Gen V)"', '"Sprites: PokeAPI/sprites (Gen V; Gen VI-IX static)"', None),
]


def main():
    tree = {
        ROOT / 'tools/fetch_data.py': FETCH,
        ROOT / 'tools/verify_data.py': VERIFY,
        ROOT / 'tools/DexLogicTest.java': TESTS,
        SRC / 'PokedexActivity.java': POKEDEX,
    }
    # Compute every result first, so a mismatch leaves all files untouched.
    results = {path: plan(path, pairs) for path, pairs in tree.items()}
    for path, text in results.items():
        path.write_text(text, encoding='utf-8')
        print('patched', path.relative_to(ROOT))


if __name__ == '__main__':
    main()
