#!/usr/bin/env python3
"""Pinned, cached public-data import. Never accesses a phone or ROM files."""
import csv, hashlib, io, json, time, urllib.request, urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'; ASSETS = ROOT / 'app/assets'; CACHE.mkdir(exist_ok=True)
PINS = {'pokeapi':'81d20919845b6a445969b9265aab5cec6b04cece', 'sprites':'ba403973fdf9d0ac59175813861e6a1f8ed5020c', 'cries':'b3a9044bb839b5e3152aaa536c7b463a0fcf0140', 'veekun':'e71bfba357a85c11ef551262ebab76991f81091f'}
BASE = 'https://raw.githubusercontent.com/PokeAPI/'
manifest = {}; missing = []
def get(url, dest, optional=False):
    if dest.exists() and dest.stat().st_size: return dest.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'FlipPokedex-offline-import/1.0'})
            with urllib.request.urlopen(req, timeout=90) as r: data = r.read()
            tmp = dest.with_suffix(dest.suffix+'.tmp'); tmp.write_bytes(data); tmp.replace(dest)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404 and optional: return None
            if attempt == 3: raise
        except (OSError, TimeoutError):
            if attempt == 3: raise
        time.sleep(2**attempt)
def table(name):
    return list(csv.DictReader(io.StringIO(get(BASE+'pokeapi/'+PINS['pokeapi']+'/data/v2/csv/'+name+'.csv', CACHE/(name+'.csv')).decode('utf-8-sig'))))
NAMES = '''pokemon pokemon_species pokemon_species_names pokemon_dex_numbers pokemon_types pokemon_types_past pokemon_stats pokemon_stats_past pokemon_abilities pokemon_abilities_past pokemon_species_flavor_text pokemon_egg_groups egg_group_prose abilities ability_names ability_flavor_text types type_names type_efficacy type_efficacy_past pokemon_evolution evolution_triggers items item_names pokemon_moves moves move_names move_flavor_text move_changelog pokemon_move_methods pokemon_forms pokemon_form_names pokemon_form_generations pokemon_form_types encounters encounter_slots encounter_methods location_areas location_area_prose locations location_names stat_names encounter_condition_value_map encounter_condition_values encounter_condition_value_prose versions version_groups machines'''.split()
T = {}
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(table,n):n for n in NAMES}
    for f in as_completed(futures):
        n=futures[f]; T[n]=f.result(); print('CSV',n,len(T[n]),flush=True)
def idx(n, key='id'): return {r[key]:r for r in T[n]}
def english(n,key,field='name'): return {r[key]:r[field] for r in T[n] if r.get('local_language_id',r.get('language_id'))=='9'}
# Frozen Gen V species metadata avoids later catch-rate/friendship changes.
legacy_species=list(csv.DictReader(io.StringIO(get('https://raw.githubusercontent.com/veekun/pokedex/'+PINS['veekun']+'/pokedex/data/csv/pokemon_species.csv', CACHE/'gen5-species.csv').decode())))
legacy_species={r['id']:r for r in legacy_species}
for r in T['pokemon_species']:
    if r['id'] in legacy_species:
        for key in ['capture_rate','base_happiness','gender_rate','hatch_counter']:
            r[key]=legacy_species[r['id']][key]
pokemon=idx('pokemon'); species=idx('pokemon_species'); names=english('pokemon_species_names','pokemon_species_id'); genera=english('pokemon_species_names','pokemon_species_id','genus')
version_groups=idx('version_groups')
gen5_form_ids={r['pokemon_form_id'] for r in T['pokemon_form_generations'] if r['generation_id']=='5'}
era_forms=[r for r in T['pokemon_forms'] if r['id'] in gen5_form_ids and r['introduced_in_version_group_id'] and int(version_groups[r['introduced_in_version_group_id']]['generation_id'])<=5 and int(pokemon[r['pokemon_id']]['species_id'])<=649]
forms={}
for r in sorted(era_forms,key=lambda r:int(r['form_order']),reverse=True): forms[r['pokemon_id']]=r
ids = {str(i) for i in range(1,1026)} | set(forms)
# Only species/forms present by B2W2. Dataset includes regional #000 Victini.
dex = {r['species_id']:int(r['pokedex_number']) for r in T['pokemon_dex_numbers'] if r['pokedex_id']=='9'}
type_names=english('type_names','type_id'); ability_names=english('ability_names','ability_id'); item_names=english('item_names','item_id'); egg_names=english('egg_group_prose','egg_group_id'); move_names=english('move_names','move_id')
# Spanish (language_id 7) strings, carried beside English in every record as *_es fields.
# Upstream has no Spanish text for Black 2 / White 2 (versions 21/22); the Spanish flavor fallback is the newest Spanish entry, which comes from a later game.
# Upstream also has no Spanish names for Unova locations or encounter conditions, so those stay English unless translated below.
def spanish(n,key,field='name'): return {r[key]:r[field] for r in T[n] if r.get('local_language_id',r.get('language_id'))=='7' and r[field]}
# Upstream PokeAPI has no Spanish method or condition prose, so these short encounter labels are curated here.
METHOD_ES={'walk':'Caminar','surf':'Surf','old rod':'Caña vieja','good rod':'Caña buena','super rod':'Caña superior','rock smash':'Romper rocas','headbutt':'Cabezazo','dark grass':'Hierba oscura','grass spots':'Manchas de hierba','cave spots':'Manchas de cueva','bridge spots':'Manchas de puente','super rod spots':'Manchas de caña superior','surf spots':'Manchas de surf','hidden grotto':'Gruta oculta','npc trade':'Intercambio','static':'Estático','gift':'Regalo','gift egg':'Huevo regalo'}
CONDITION_ES={'Captured Reshiram or Zekrom previously':'Capturado antes Reshiram o Zekrom','During Autumn':'Durante el otoño','During Spring':'Durante la primavera','During Summer':'Durante el verano','During Winter':'Durante el invierno','Obtained Quake Badge':'Obtenida la Medalla Temblor','Spoke to Professor Juniper in the Cave of Being':'Hablar con la Profesora Encina en la Cueva del Ser','Have Regirock, Regice and Registeel in the party':'Tener Regirock, Regice y Registeel en el equipo','This special Pokémon couldn’t be captured in previous encounters (either fainted or ran from battle)':'Este Pokémon especial no pudo capturarse antes (se debilitó o huyó del combate)'}
for _sp in ['Cottonee','Ditto','Emolga','Excadrill','Hippowdon','Mantine','Petilil']: CONDITION_ES[f'Give {_sp} in a Trade']=f'Dar {_sp} en un intercambio'
for _item,_es in [('Armor Fossil','Fósil Coraza'),('Claw Fossil','Fósil Garra'),('Cover Fossil','Fósil Cubierta'),('Dark Stone','Piedra Oscura'),('Dome Fossil','Fósil Domo'),('Helix Fossil','Fósil Hélix'),('Ice Key','Llave Hielo'),('Iron Key','Llave Hierro'),('Light Stone','Piedra Luz'),('Lunar Wing','Ala Lunar'),('Old Amber','Ámbar Viejo'),('Plume Fossil','Fósil Pluma'),('Root Fossil','Fósil Raíz'),('Skull Fossil','Fósil Cráneo')]: CONDITION_ES[f'Have {_item} in bag']=f'Tener {_es} en la mochila'
# Spanish genus and Pokedex text for species with none in PokeAPI (see tools/scrape_es_wikidex.py).
ES_FILL=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8'))['species'] if (CACHE/'es_fill.json').exists() else {}
names_es=spanish('pokemon_species_names','pokemon_species_id'); genera_es=spanish('pokemon_species_names','pokemon_species_id','genus')
type_es=spanish('type_names','type_id'); ability_es=spanish('ability_names','ability_id'); item_es=spanish('item_names','item_id'); egg_es=spanish('egg_group_prose','egg_group_id'); move_es=spanish('move_names','move_id'); stat_es=spanish('stat_names','stat_id'); loc_es=spanish('location_names','location_id')
form_names=english('pokemon_form_names','pokemon_form_id','form_name'); form_names_es=spanish('pokemon_form_names','pokemon_form_id','form_name')
def disp_name(base,fn,base_en):
    return (fn if base_en.lower() in fn.lower() else base+' ('+fn+')') if fn else base
types=defaultdict(list); stats=defaultdict(dict); abilities=defaultdict(list)
for r in T['pokemon_types']: types[r['pokemon_id']].append(r)
for r in T['pokemon_stats']: stats[r['pokemon_id']][r['stat_id']]=int(r['base_stat'])
for r in T['pokemon_abilities']: abilities[r['pokemon_id']].append(r)
# Past rows define the last generation to which the old value applies.
groups=defaultdict(lambda:defaultdict(list))
for r in T['pokemon_types_past']:
    if int(r['generation_id'])>=5 and int(pokemon[r['pokemon_id']]['species_id'])<=649: groups[r['pokemon_id']][int(r['generation_id'])].append(r)
for pid,gens in groups.items(): types[pid]=gens[min(gens)]
ability_history=defaultdict(list)
for r in T['pokemon_abilities_past']:
    if int(r['generation_id'])>=5 and int(pokemon[r['pokemon_id']]['species_id'])<=649: ability_history[r['pokemon_id'],r['slot']].append(r)
for (pid,slot),rows in ability_history.items():
    old=min(rows,key=lambda r:int(r['generation_id']))
    abilities[pid]=[r for r in abilities[pid] if r['slot']!=slot]
    if old['ability_id']: abilities[pid].append(old)
for pid in [p for p in ids if int(pokemon[p]['species_id'])<=649]:
    past=defaultdict(list)
    for r in T['pokemon_stats_past']:
        if r['pokemon_id']==pid and int(r['generation_id'])>=5: past[r['stat_id']].append(r)
    for stat,rows in past.items(): stats[pid][stat]=int(min(rows,key=lambda r:int(r['generation_id']))['base_stat'])
flavors=defaultdict(dict)
for r in T['pokemon_species_flavor_text']:
    if r['language_id']=='9' and (int(r['version_id'])<=22 or int(r['species_id'])>649): flavors[r['species_id']][r['version_id']]=' '.join(r['flavor_text'].split())
flavors_es=defaultdict(dict)
for r in T['pokemon_species_flavor_text']:
    if r['language_id']=='7': flavors_es[r['species_id']][int(r['version_id'])]=' '.join(r['flavor_text'].split())
ability_text={}
ability_text_es={}
for r in sorted(T['ability_flavor_text'],key=lambda r:int(r['version_group_id'])):
    if r['language_id']=='7': ability_text_es[r['ability_id']]=' '.join(r['flavor_text'].split())
for r in T['ability_flavor_text']:
    if r['language_id']=='9' and int(r['version_group_id'])<=14: ability_text[r['ability_id']]=' '.join(r['flavor_text'].split())
ability_text_latest={}
for r in sorted(T['ability_flavor_text'],key=lambda r:int(r['version_group_id'])):
    if r['language_id']=='9': ability_text_latest[r['ability_id']]=' '.join(r['flavor_text'].split())
# Gen IX abilities: official WikiDex Spanish name and text (cache/es_fill.json, status "wikidex") fill PokeAPI gaps.
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
# Spanish gaps from WikiDex (cache/es_fill.json; see tools/apply_wikidex_es_gaps.py for what each key feeds).
_ES_FILL_ALL=json.loads((CACHE/'es_fill.json').read_text(encoding='utf-8')) if (CACHE/'es_fill.json').exists() else {}
ES_AREA=_ES_FILL_ALL.get('areas',{}); ES_LOC=_ES_FILL_ALL.get('locations',{}); ES_COND=_ES_FILL_ALL.get('conditions',{}); ES_MOVES=_ES_FILL_ALL.get('moves',{})
eggs=defaultdict(list); eggs_es=defaultdict(list)
for r in T['pokemon_egg_groups']: eggs[r['species_id']].append(egg_names[r['egg_group_id']]); eggs_es[r['species_id']].append(egg_es.get(r['egg_group_id'],egg_names[r['egg_group_id']]))
move_data=idx('moves'); move_text={}; move_text_es={}
for r in sorted(T['move_flavor_text'],key=lambda r:int(r['version_group_id'])):
    if r['language_id']=='7': move_text_es[r['move_id']]=' '.join(r['flavor_text'].split())
for r in T['move_flavor_text']:
    if r['language_id']=='9' and int(r['version_group_id'])<=14: move_text[r['move_id']]=' '.join(r['flavor_text'].split())
move_current={k:dict(v) for k,v in move_data.items()}
for mid,r in move_data.items():
    changes=[c for c in T['move_changelog'] if c['move_id']==mid and int(c['changed_in_version_group_id'])>14]
    for k in ['type_id','power','pp','accuracy','priority','effect_id','effect_chance']:
        rows=[c for c in changes if c.get(k)]
        if rows: r[k]=min(rows,key=lambda c:int(c['changed_in_version_group_id']))[k]
# Gen IX moves with no Spanish flavor text upstream: translated descriptions (cache key "moves").
for _mid,_rec in ES_MOVES.items():
    if _rec.get('text_es') and not move_text_es.get(_mid): move_text_es[_mid]=_rec['text_es']
methods=idx('pokemon_move_methods'); learnsets=defaultdict(list)
move_text_latest={}
for r in sorted(T['move_flavor_text'],key=lambda r:int(r['version_group_id'])):
    if r['language_id']=='9': move_text_latest[r['move_id']]=' '.join(r['flavor_text'].split())
machines_by_vg=defaultdict(dict)
for r in T['machines']: machines_by_vg[r['version_group_id']][r['move_id']]=r['machine_number']
# Species 650+ have no B2W2 learnset: use the newest version group that records their moves.
newest_vg={}
for r in T['pokemon_moves']:
    if r['pokemon_id'] in ids and int(pokemon[r['pokemon_id']]['species_id'])>649:
        newest_vg[r['pokemon_id']]=max(newest_vg.get(r['pokemon_id'],0),int(r['version_group_id']))
for r in T['pokemon_moves']:
    pid=r['pokemon_id']
    if pid not in ids: continue
    late=int(pokemon[pid]['species_id'])>649; vg=str(newest_vg[pid]) if late else '14'
    if r['version_group_id']==vg:
        m=(move_current if late else move_data)[r['move_id']]; method=methods[r['pokemon_move_method_id']]['identifier']
        learnsets[r['pokemon_id']].append({'id':int(r['move_id']),'name':move_names[r['move_id']], 'method':method,'level':int(r['level']), 'machine':machines_by_vg[vg].get(r['move_id'],''), 'type':type_names[m['type_id']], 'power':m['power'] or '—','accuracy':m['accuracy'] or '—','pp':m['pp'],'category':{'1':'Status','2':'Physical','3':'Special'}[m['damage_class_id']],'text':(move_text_latest if late else move_text).get(r['move_id'],''),'name_es':move_es.get(r['move_id'],''),'text_es':move_text_es.get(r['move_id'],'')})
locations=idx('locations'); areas=idx('location_areas'); locnames=english('location_names','location_id'); areanames=english('location_area_prose','location_area_id'); slots=idx('encounter_slots'); emethods=idx('encounter_methods'); conditions=english('encounter_condition_value_prose','encounter_condition_value_id'); cmap=defaultdict(list)
for r in T['encounter_condition_value_map']: cmap[r['encounter_id']].append(conditions.get(r['encounter_condition_value_id'],''))
encounters=defaultdict(list)
for r in T['encounters']:
    if r['version_id'] in ['21','22'] and r['pokemon_id'] in ids:
        area=areas[r['location_area_id']]; slot=slots[r['encounter_slot_id']]
        loc_label_es=loc_es.get(area['location_id'],''); encounters[r['pokemon_id']].append({'area_es':ES_AREA.get(locnames.get(area['location_id'],locations[area['location_id']]['identifier'])+(' / '+areanames[area['id']] if areanames.get(area['id']) else ''),{}).get('area_es',''),'game':'Black 2' if r['version_id']=='21' else 'White 2','area':locnames.get(area['location_id'],locations[area['location_id']]['identifier']) + (' / '+areanames[area['id']] if areanames.get(area['id']) else ''),'method':emethods[slot['encounter_method_id']]['identifier'].replace('-',' '),'method_es':METHOD_ES.get(emethods[slot['encounter_method_id']]['identifier'].replace('-',' '),''),'min':int(r['min_level']),'max':int(r['max_level']),'chance':slot['rarity'],'conditions':cmap[r['id']],'conditions_es':[CONDITION_ES.get(c,c) for c in cmap[r['id']]]})
# Unova and other place names with no PokeAPI Spanish: WikiDex names keyed by the English location name.
loc_es.update({_lid:ES_LOC[_en]['name_es'] for _lid,_en in locnames.items() if _en in ES_LOC and ES_LOC[_en].get('name_es') and not loc_es.get(_lid)})
triggers=idx('evolution_triggers'); evolutions=defaultdict(list); evolutions_es=defaultdict(list)
for r in T['pokemon_evolution']:
    sid=r['evolved_species_id']
    if int(sid)>1025: continue
    gen5_row=int(sid)<=649
    if gen5_row and int(version_groups[r['version_group_id']]['generation_id'])>5: continue
    if gen5_row and r.get('region_id') and r['region_id']!='5': continue
    if gen5_row and r.get('evolved_pokemon_form_id') and r['evolved_pokemon_form_id'] not in {f['id'] for f in era_forms}: continue
    # Later evolution methods for old species are not part of Gen V.
    if gen5_row and r.get('trigger_item_id') and int(idx('items')[r['trigger_item_id']]['id'])>700: continue
    def build(es):
        L={'level':'Nivel ','happy':'Amistad ≥ ','beauty':'Belleza ≥ ','affection':'Afecto ≥ ','hold':'Sostiene ','female':'hembra','male':'macho','know':'Conoce ','moss':'Cerca de Roca Musgo','ice':'Cerca de Roca Helada','special':'Lugar especial','trade':'Intercambio por ','party':' en el equipo','lt':'Ataque < Defensa','eq':'Ataque = Defensa','gt':'Ataque > Defensa'} if es else {'level':'Level ','happy':'Friendship ≥ ','beauty':'Beauty ≥ ','affection':'Affection ≥ ','hold':'Hold ','female':'female','male':'male','know':'Know ','moss':'Near Moss Rock','ice':'Near Ice Rock','special':'Special location','trade':'Trade for ','party':' in party','lt':'Attack < Defense','eq':'Attack = Defense','gt':'Attack > Defense'}
        nm=(lambda i:names_es.get(i,names[i])) if es else (lambda i:names[i]); it=(lambda i:item_es.get(i,item_names[i])) if es else (lambda i:item_names[i]); mv=(lambda i:move_es.get(i,move_names[i])) if es else (lambda i:move_names[i])
        bits=[]
        for k,key in [('minimum_level','level'),('minimum_happiness','happy'),('minimum_beauty','beauty'),('minimum_affection','affection')]:
            if r.get(k): bits.append(L[key]+('220' if k=='minimum_happiness' and int(sid)<=649 else r[k]))
        for k in ['trigger_item_id','held_item_id']:
            if r.get(k): bits.append((L['hold'] if k=='held_item_id' else '')+it(r[k]))
        if r.get('time_of_day'): bits.append({'day':'día','night':'noche'}.get(r['time_of_day'],r['time_of_day']) if es else r['time_of_day'])
        if r.get('gender_id'): bits.append(L['female'] if r['gender_id']=='1' else L['male'])
        if r.get('known_move_id'): bits.append(L['know']+mv(r['known_move_id']))
        if r.get('near_special_rock')=='1': bits.append(L['moss'] if sid=='470' else L['ice'])
        elif r.get('location_id'): bits.append((loc_es.get(r['location_id']) if es else None) or locnames.get(r['location_id'],L['special']))
        if r.get('trade_species_id'): bits.append(L['trade']+nm(r['trade_species_id']))
        if r.get('relative_physical_stats'): bits.append(L[{'-1':'lt','0':'eq','1':'gt'}[r['relative_physical_stats']]])
        if r.get('party_species_id'): bits.append(nm(r['party_species_id'])+L['party'])
        trigger=triggers[r['evolution_trigger_id']]['identifier'].replace('-',' ')
        if es: label={'trade':'Intercambio','shed':'Muda','other':'Otro','take damage':'Recibir daño','three critical hits':'Tres golpes críticos','spin':'Girar','tower of darkness':'Torre Oscura','tower of waters':'Torre Agua','agile style move':'Movimiento ágil','strong style move':'Movimiento fuerte','recoil damage':'Daño de retroceso'}.get(trigger,trigger.title())
        else: label=trigger.title()
        if trigger not in ['level up','use item']: bits.insert(0,label)
        return ' · '.join(bits) or (label if trigger not in ['level up','use item'] else trigger.title() if not es else {'level up':'Subir de nivel','use item':'Usar objeto'}[trigger])
    evolutions[sid].append(build(False)); _cond_es=build(True); evolutions_es[sid].append(ES_COND.get(_cond_es,{}).get('condition_es',_cond_es))
# Pre-Fairy type chart, including the old Steel resistances.
efficacy={(r['damage_type_id'],r['target_type_id']):int(r['damage_factor']) for r in T['type_efficacy'] if int(r['damage_type_id'])<=17 and int(r['target_type_id'])<=17}
for r in T['type_efficacy_past']:
    if int(r['generation_id'])>=5: efficacy[r['damage_type_id'],r['target_type_id']]=int(r['damage_factor'])
efficacy_modern={(r['damage_type_id'],r['target_type_id']):int(r['damage_factor']) for r in T['type_efficacy'] if int(r['damage_type_id'])<=18 and int(r['target_type_id'])<=18}
# Gen VI-IX alternate forms with their own types or base stats (regional, battle, size, mode and mask forms).
# Mega, Gigantamax, Eternamax and Let's Go starter forms are skipped; cosmetic-only forms (same types and stats) too.
def get_opt(url, dest):
    try: return get(url, dest)
    except urllib.error.HTTPError as e:
        if e.code == 404: return None
        raise
OPTIONAL_URLS=set()
# Compare current (latest) types and stats: species #1-649 use Gen V historical values in types/stats above.
RAW_TYPES=defaultdict(list); RAW_STATS=defaultdict(dict)
for r in T['pokemon_types']: RAW_TYPES[r['pokemon_id']].append(r)
for r in T['pokemon_stats']: RAW_STATS[r['pokemon_id']][r['stat_id']]=r['base_stat']
def _type_ids(pid): return [r['type_id'] for r in sorted(RAW_TYPES[pid],key=lambda r:int(r['slot']))]
alt6_pids=set(); _seen_alt=set()
for r in T['pokemon_forms']:
    pid=r['pokemon_id']; sid=pokemon[pid]['species_id']
    if r['is_mega']=='1' or not r['introduced_in_version_group_id'] or pid==sid or pid in forms or int(sid)>1025: continue
    if int(version_groups[r['introduced_in_version_group_id']]['generation_id'])<6: continue
    if any(k in r['form_identifier'] for k in ('gmax','eternamax','starter')): continue
    if _type_ids(pid)==_type_ids(sid) and RAW_STATS[pid]==RAW_STATS[sid]: continue
    key=(sid, form_names.get(r['id']) or r['form_identifier'])
    if key in _seen_alt: continue
    _seen_alt.add(key); alt6_pids.add(pid); forms[pid]=r
ids |= alt6_pids
(ASSETS/'data/pokemon').mkdir(parents=True,exist_ok=True)
summary=[]
for pid in sorted(ids,key=int):
    p=pokemon[pid]; s=species[p['species_id']]; sid=p['species_id']; form=forms.get(pid); fn=(form_names.get(form['id']) or (form['form_identifier'].replace('-',' ').title() if pid!=sid else '')) if form else ''
    name=(fn if names[sid].lower() in fn.lower() else names[sid]+' ('+fn+')') if fn and pid!=sid else names[sid]
    ts=sorted(types[pid],key=lambda r:int(r['slot']))
    family=[{'name_es':names_es.get(qid,''),'conditions_es':list(dict.fromkeys(evolutions_es[qid])),'id':int(qid),'name':names[qid], 'from':int(q['evolves_from_species_id'] or 0), 'conditions':list(dict.fromkeys(evolutions[qid]))} for qid,q in species.items() if int(qid)<=(1025 if int(sid)>649 else 649) and q['evolution_chain_id']==s['evolution_chain_id']]
    weak=[]
    chart,attackers=(efficacy_modern,19) if int(sid)>649 or pid in alt6_pids else (efficacy,18)
    for atk in range(1,attackers):
        mult=1
        for t in ts: mult*=chart.get((str(atk),t['type_id']),100)/100
        if mult!=1: weak.append({'type':type_names[str(atk)],'factor':mult})
    fes=(form_names_es.get(form['id']) or ES_FILL_FORMS.get(str(form['id']),{}).get('form_es') or fn) if form else ''
    name_es=(names_es.get(sid,'') and ((fes if names_es[sid].lower() in fes.lower() else names_es[sid]+' ('+fes+')') if fn and pid!=sid else names_es[sid])) or ''
    fl=flavors_es.get(sid,{}); fb=fl[max(fl)] if fl else ES_FILL.get(str(sid),{}).get('flavor_es','')
    record={'name_es':name_es,'genus_es':genera_es.get(sid) or ES_FILL.get(str(sid),{}).get('genus_es',''),'black2_es':b2w2_es(sid,'black2_es') or fl.get(21,''),'white2_es':b2w2_es(sid,'white2_es') or fl.get(22,''),'fallbackText_es':fb,'eggGroups_es':eggs_es[sid],'id':int(pid),'species':int(sid),'name':name,'national':int(sid),'unova':dex.get(sid,-1),'form':fn,'sprite':pid,'types':[type_names[r['type_id']] for r in ts], 'genus':genera[sid], 'height':int(p['height'])/10,'weight':int(p['weight'])/10,'stats':[stats[pid][str(i)] for i in range(1,7)],'abilities':[{'name_es':ability_es.get(r['ability_id'],''),'text_es':ability_text_es.get(r['ability_id'],''),'name':ability_names[r['ability_id']], 'hidden':r['is_hidden']=='1','text':(ability_text_latest if int(sid)>649 else ability_text).get(r['ability_id'],'')} for r in abilities[pid] if r['ability_id']], 'black2':flavors[sid].get('21',''),'white2':flavors[sid].get('22',''), 'fallbackText':(flavors[sid][max(flavors[sid],key=int)] if int(sid)>649 and flavors[sid] else (next(reversed(flavors[sid].values()),'') if flavors[sid] else '')), 'captureRate':int(s['capture_rate']), 'friendship':int(s['base_happiness']), 'genderRate':int(s['gender_rate']), 'hatchCounter':int(s['hatch_counter']), 'eggGroups':eggs[sid], 'moves':sorted(learnsets[pid],key=lambda r:(r['method']!='level-up',r['method'],r['level'],r['name'])), 'encounters':encounters[pid], 'evolution':family,'matchups':weak}
    (ASSETS/'data/pokemon'/f'{pid}.json').write_text(json.dumps(record,ensure_ascii=False,separators=(',',':')))
    summary.append({k:record[k] for k in ['id','species','name','name_es','national','unova','form','sprite','types']})
(ASSETS/'data/index.json').write_text(json.dumps(summary,ensure_ascii=False,separators=(',',':')))
# Enumerate the pinned sprite directory once, avoiding thousands of speculative requests.
api='https://api.github.com/repos/PokeAPI/sprites/contents/sprites/pokemon/versions/generation-v?ref='+PINS['sprites']
listing=json.loads(get(api,CACHE/'sprite-directory.json'))
sha=next(r['sha'] for r in listing if r['name']=='black-white')
tree=json.loads(get('https://api.github.com/repos/PokeAPI/sprites/git/trees/'+sha+'?recursive=1', CACHE/'sprite-tree.json'))
available={r['path'] for r in tree['tree'] if r['type']=='blob'}
extra_stems=set()
for form in era_forms:
    pid=form['pokemon_id']; sid=pokemon[pid]['species_id']; label=form['form_identifier']
    if not label or form['id']==forms[pid]['id']: continue
    stem=sid+'-'+label
    if stem+'.png' not in available and 'animated/'+stem+'.gif' not in available: continue
    data=json.loads((ASSETS/'data/pokemon'/f'{pid}.json').read_text())
    form_types=sorted([r for r in T['pokemon_form_types'] if r['pokemon_form_id']==form['id']],key=lambda r:int(r['slot']))
    if form_types:
        data['types']=[type_names[r['type_id']] for r in form_types]
        data['matchups']=[]
        for atk in range(1,18):
            mult=1
            for t in form_types: mult*=efficacy.get((str(atk),t['type_id']),100)/100
            if mult!=1: data['matchups'].append({'type':type_names[str(atk)],'factor':mult})
    data['id']=200000+int(form['id']); data['sprite']=stem; data['form']=form_names.get(form['id'],label.title()); data['name']=data['form'] if names[sid].lower() in data['form'].lower() else names[sid]+' ('+data['form']+')'
    fes=form_names_es.get(form['id'],data['form']); data['name_es']=(fes if names_es[sid].lower() in fes.lower() else names_es[sid]+' ('+fes+')') if sid in names_es else ''
    (ASSETS/'data/pokemon'/f"{data['id']}.json").write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
    summary.append({k:data[k] for k in ['id','species','name','name_es','national','unova','form','sprite','types']})
    extra_stems.add(stem)
(ASSETS/'data/index.json').write_text(json.dumps(summary,ensure_ascii=False,separators=(',',':')))
# Spanish lookup tables for English keys that the app still uses as identifiers (types, stats, egg groups).
i18n_es={'types':{type_names[k]:type_es[k] for k in type_names if k in type_es and int(k)<=18},'eggGroups':{egg_names[k]:egg_es[k] for k in egg_names if k in egg_es},'stats':{english('stat_names','stat_id')[k]:stat_es[k] for k in stat_es if k in english('stat_names','stat_id')}}
(ASSETS/'data/i18n_es.json').write_text(json.dumps(i18n_es,ensure_ascii=False,indent=1))
selected=[]
for r in tree['tree']:
    path=r['path']; stem=Path(path).stem
    if r['type']=='blob' and stem in ids|extra_stems and not (stem.isdigit() and 650<=int(stem)<=1025) and Path(path).suffix in ['.png','.gif']:
        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/versions/generation-v/black-white/'+path,ASSETS/'sprites'/path))
# Remove only obsolete generated records/sprites belonging to this importer.
record_ids={str(r['id']) for r in summary}
for obsolete in (ASSETS/'data/pokemon').glob('*.json'):
    if obsolete.stem not in record_ids: pass # Preserved by owner request.
for n in range(650,1026):
    for sub in ['','shiny/','back/','back/shiny/']:
        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+str(n)+'.png',ASSETS/'sprites'/(sub+str(n)+'.png')))
for n in range(650,1026):
    for sub in ['','shiny/']:
        selected.append((BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+str(n)+'.png',ASSETS/'sprites'/(sub+str(n)+'.png')))
for pid in sorted(alt6_pids,key=int):
    for sub in ['','shiny/','back/','back/shiny/']:
        url=BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+pid+'.png'; OPTIONAL_URLS.add(url)
        selected.append((url,ASSETS/'sprites'/(sub+pid+'.png')))
selected_paths={dest for _,dest in selected}
for obsolete in (ASSETS/'sprites').rglob('*'):
    if obsolete.is_file() and obsolete not in selected_paths: pass # Preserved by owner request.
print('Downloading',len(selected),'Gen V sprites for',len(summary),'entries',flush=True)
with ThreadPoolExecutor(max_workers=8) as ex:
    futures={ex.submit(get_opt if url in OPTIONAL_URLS else get,url,dest):(url,dest) for url,dest in selected}
    for i,f in enumerate(as_completed(futures),1):
        f.result()
        if i%100==0: print('Sprites',i,'/',len(selected),flush=True)
# The legacy cry set preserves the pre-Gen VI sounds.
cry_listing=json.loads(get('https://api.github.com/repos/PokeAPI/cries/contents/cries/pokemon/legacy?ref='+PINS['cries'],CACHE/'cry-directory.json'))
cry_paths={r['name'] for r in cry_listing}
cries=[(BASE+'cries/'+PINS['cries']+'/cries/pokemon/legacy/'+pid+'.ogg',ASSETS/'cries'/(pid+'.ogg')) for pid in ids if pid+'.ogg' in cry_paths]
cries+=[(BASE+'cries/'+PINS['cries']+'/cries/pokemon/latest/'+str(n)+'.ogg',ASSETS/'cries'/(str(n)+'.ogg')) for n in range(650,1026)]
for pid in sorted(alt6_pids,key=int):
    if pid+'.ogg' in cry_paths: cries.append((BASE+'cries/'+PINS['cries']+'/cries/pokemon/legacy/'+pid+'.ogg',ASSETS/'cries'/(pid+'.ogg')))
    else:
        url=BASE+'cries/'+PINS['cries']+'/cries/pokemon/latest/'+pid+'.ogg'; OPTIONAL_URLS.add(url)
        cries.append((url,ASSETS/'cries'/(pid+'.ogg')))
with ThreadPoolExecutor(max_workers=6) as ex:
    for i,_ in enumerate(ex.map(lambda pair:(get_opt if pair[0] in OPTIONAL_URLS else get)(*pair),cries),1):
        if i%100==0: print('Cries',i,'/',len(cries),flush=True)
# A form without its own cry uses its species cry (the Rotom rule).
for pid in sorted(alt6_pids,key=int):
    dest=ASSETS/'cries'/(pid+'.ogg'); src=ASSETS/'cries'/(pokemon[pid]['species_id']+'.ogg')
    if not dest.exists() and src.exists(): dest.write_bytes(src.read_bytes())
# Content manifest makes cached imports independently checkable, including every source CSV.
for path in sorted((ASSETS).rglob('*')):
    if path.is_file() and path.name!='manifest.json': manifest[str(path.relative_to(ASSETS))]=hashlib.sha256(path.read_bytes()).hexdigest()
report={'sources':PINS,'species':1025,'entries':len(summary),'regionalSpecies':len(dex),'sprites':len(selected),'cries':len(cries),'files':manifest,'csv':{n:hashlib.sha256((CACHE/(n+'.csv')).read_bytes()).hexdigest() for n in NAMES},'gen5SpeciesSha256':hashlib.sha256((CACHE/'gen5-species.csv').read_bytes()).hexdigest(),'notes':['Species 650-1025 (Gen VI-IX): newest recorded version group, current stats/types/moves/abilities, latest flavor text, static sprites and latest cries.', 'Gen V B2W2 version group 14; Black 2 version 21 / White 2 version 22.', 'B2W2 entries fall back explicitly to earlier English text when absent.', 'Wild encounters are public dataset records, not an exhaustive gift/event/trade guide.', 'Gen V sprites are shared Black/White assets; B2W2-specific animation differences are not represented upstream.']}
(ASSETS/'data/manifest.json').write_text(json.dumps(report,indent=2))
print('DONE',len(manifest),'asset files',flush=True)

# All-game encounter index (offline WikiDex cache; idempotent final generation step).
from encounter_data import apply as apply_all_encounters
apply_all_encounters(ASSETS)
