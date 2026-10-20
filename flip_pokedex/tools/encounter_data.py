#!/usr/bin/env python3
"""Offline encounter import shared by the generator and rerunnable apply step."""
import csv, json, re, hashlib
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CACHE=ROOT/'cache'
# IDs remain exact versions; UI groups related titles without conflating exclusives.
GAME_ES=['','Rojo','Azul','Amarillo','Oro','Plata','Cristal','Rubí','Zafiro','Esmeralda','Rojo Fuego','Verde Hoja','Diamante','Perla','Platino','Oro HeartGold','Plata SoulSilver','Negro','Blanco','Colosseum','XD','Negro 2','Blanco 2','X','Y','Rubí Omega','Zafiro Alfa','Sol','Luna','Ultrasol','Ultraluna',"Let’s Go, Pikachu!","Let’s Go, Eevee!",'Espada','Escudo','Isla de la Armadura (Espada)','Nieves de la Corona (Espada)','Diamante Brillante','Perla Reluciente','Leyendas: Arceus','Escarlata','Púrpura','La máscara turquesa (Escarlata)','El disco índigo (Escarlata)','Rojo (Japón)','Verde (Japón)','Azul (Japón)','Leyendas: Z-A','Megadimensión','Champions','Isla de la Armadura (Escudo)','Nieves de la Corona (Escudo)','La máscara turquesa (Púrpura)','El disco índigo (Púrpura)']
GAME_ES[36]='Nieves de la Corona (Espada)'
GROUPS=[([1,2],'Rojo y Azul'),([3],'Amarillo'),([4,5],'Oro y Plata'),([6],'Cristal'),([7,8],'Rubí y Zafiro'),([9],'Esmeralda'),([10,11],'Rojo Fuego y Verde Hoja'),([12,13],'Diamante y Perla'),([14],'Platino'),([15,16],'HeartGold y SoulSilver'),([17,18],'Negro y Blanco'),([21,22],'Negro 2 y Blanco 2'),([23,24],'X e Y'),([25,26],'Rubí Omega y Zafiro Alfa'),([27,28],'Sol y Luna'),([29,30],'Ultrasol y Ultraluna'),([31,32],'Let’s Go, Pikachu! y Eevee!'),([33,34],'Espada y Escudo'),([35,50],'Isla de la Armadura'),([36,51],'Nieves de la Corona'),([37,38],'Diamante Brillante y Perla Reluciente'),([39],'Leyendas: Arceus'),([40,41],'Escarlata y Púrpura'),([42,52],'La máscara turquesa'),([43,53],'El disco índigo'),([44,45],'Rojo y Verde (Japón)'),([46],'Azul (Japón)'),([47],'Leyendas: Z-A'),([48],'Megadimensión'),([49],'Champions'),([19],'Colosseum'),([20],'XD')]
WIKI_KEYS={1:'rojo',2:'azul',3:'amarillo',4:'oro',5:'plata',6:'cristal',7:'rubí',8:'zafiro',9:'esmeralda',10:'rojofuego',11:'verdehoja',12:'diamante',13:'perla',14:'platino',15:'oro heartgold',16:'plata soulsilver',17:'negro',18:'blanco',21:'negro 2',22:'blanco 2',23:'x',24:'y',25:'rubí omega',26:'zafiro alfa',27:'sol',28:'luna',29:'ultrasol',30:'ultraluna',31:'lgp',32:'lge',33:'espada',34:'escudo',37:'diamante brillante',38:'perla reluciente',39:'leyendas arceus',40:'escarlata',41:'púrpura',46:'azuljp',47:'leyendas za'}
METHODS=dict(zip(['walk','old-rod','good-rod','super-rod','surf','rock-smash','headbutt','dark-grass','grass-spots','cave-spots','bridge-spots','super-rod-spots','surf-spots','yellow-flowers','purple-flowers','red-flowers','rough-terrain'],['Hierba','Caña vieja','Caña buena','Supercaña','Surf','Golpe Roca','Golpe Cabeza','Hierba oscura','Hierba que se mueve','Polvo de cueva','Sombra de puente','Pesca en burbujas','Surf en burbujas','Flores amarillas','Flores moradas','Flores rojas','Terreno agreste']))
METHODS.update({'static':'Encuentro fijo','pokeflute':'Pokéflauta','headbutt-low':'Golpe Cabeza (bajo)','headbutt-normal':'Golpe Cabeza','headbutt-high':'Golpe Cabeza (alto)','squirt-bottle':'Regadera','wailmer-pail':'Wailmegadera','seaweed':'Algas','roaming-grass':'Errante (hierba)','roaming-water':'Errante (agua)','devon-scope':'Detector Devon','feebas-tile-fishing':'Pesca en casillas de Feebas','island-scan':'Escáner insular','sos':'Refuerzos','bubbling-spots':'Burbujas','berry-trees':'Árboles de bayas','sos-from-bubbling-spot':'Refuerzos en burbujas','overworld':'Visible en el mapa','overworld-water':'Visible en el agua','overworld-flying':'Visible volando','overworld-special':'Visible especial','overworld-flying-special':'Vuelo especial','overworld-water-special':'Agua especial','horde':'Horda','pokespot':'Poké Spot','hidden-grotto':'Gruta oculta','honey-tree':'Árbol de miel','overworld-dirt':'Visible en tierra','wanderer':'Errante','wanderer-water':'Errante acuático','chase-water':'Persecución acuática','dynamax-adventure':'Aventura Dinamax','max-raid':'Incursión Dinamax','trash-can-ambush':'Emboscada en papelera','rustling-bush-ambush':'Emboscada en arbusto','ceiling-ambush':'Emboscada desde el techo','ground-ambush':'Emboscada en tierra','sky-ambush':'Emboscada desde el cielo'})

def rows(name):
    with (CACHE/(name+'.csv')).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def parameters(text):
    # Only top-level named parameters: pipes inside links/templates are not delimiters.
    text=text[text.find('\n')+1:-2];parts=[];start=0;depth=links=0;i=0
    while i<len(text):
        pair=text[i:i+2]
        if pair=='{{':depth+=1;i+=2;continue
        if pair=='}}':depth-=1;i+=2;continue
        if pair=='[[':links+=1;i+=2;continue
        if pair==']]':links-=1;i+=2;continue
        if text[i]=='|' and depth==0 and links==0:parts.append(text[start:i]);start=i+1
        i+=1
    parts.append(text[start:]);return {k.strip().lower():v.strip() for p in parts if '=' in p for k,v in [p.split('=',1)]}

def wild_links(record,valid,dlc_locations=None):
    out={}; params=parameters(record['localizacion'])
    for vid,key in WIKI_KEYS.items():
        val=params.get(key,'');seen=set()
        while val.lower() in params and val.lower() not in seen:
            seen.add(val.lower());val=params[val.lower()]
        # Plain wild bullets only. Never import evolution, transfer, gifts, or raid-event prose.
        for bullet in re.split(r'\n\s*\*',val):
            m=re.search(r"'''(.*?)'''",bullet,re.S)
            if not m:continue
            label=re.sub(r'\[\[([^]|]+)(?:\|([^]]+))?\]\]',lambda x:x.group(2) or x.group(1),m.group(1)).lower()
            supported=[('horda','horde','Horda'),('dexnav','dexnav','DexNav'),('golpe roca','rock smash','Golpe Roca'),('buce','dive','Buceo'),('teraincursi','tera raid','Teraincursión'),('salvaje','wild (unspecified)','Salvaje · método sin especificar'),('pesc','fishing','Pesca'),('surf','surf','Surf'),('pokéradar','poke radar','Pokéradar'),('alfa','alpha','Alfa'),('grutas del subsuelo','underground','Grutas del Subsuelo'),('gran caverna subterránea','underground','Gran Caverna Subterránea'),('manada','swarm','Manada'),('aparición','outbreak','Aparición masiva'),('incursión dinamax','max raid','Incursión Dinamax'),('incursiones dinamax','max raid','Incursión Dinamax'),('aventura dinamax','dynamax adventure','Aventura Dinamax'),('escáner insular','island scan','Escáner insular')]
            match=next(((method,es) for token,method,es in supported if token in label),None)
            tail=bullet[m.end():]
            if not match and 'especial' in label and re.search(r'captur',tail,re.I) and not re.search(r'regalo|inicial|recibid|entregad|intercambi',tail,re.I):match=('special capture','Especial (capturable)')
            if not match:continue
            tail=';'.join(part for part in tail.split(';') if not re.search(r'evento',part,re.I))
            if not tail.strip():continue
            # A species page can combine regional forms. Do not assign ambiguous forms to a default.
            if re.search(r'\bformas?\b',tail,re.I) or (record.get('title') and re.search(r'\[\['+re.escape(record['title'])+r' de (?:Alola|Galar|Hisui|Paldea)(?:\||\]\])',tail,re.I)):continue
            added=False
            for target,label in re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',tail):
                title=target.split('#')[0].strip()
                if title in valid:
                    exact=vid;dlc=(dlc_locations or {}).get(title)
                    if dlc=='noroteo' and vid in (40,41):exact=42 if vid==40 else 52
                    elif dlc=='biodomo' and vid in (40,41):exact=43 if vid==40 else 53
                    elif vid==47 and (dlc=='megadimension' or 'dimensional' in title.lower()):exact=48
                    out.setdefault(exact,set()).add((title,*match));added=True
            # Explicit region-wide habitat prose is still source data. Retain it
            # verbatim as an area description; do not invent concrete place names.
            if not added and '[[' not in tail:
                prose=re.sub(r'\{\{[^{}]*\}\}|<[^>]*>','',tail).replace("'''",'')
                prose=' '.join(prose.strip(' :.*').split())
                if len(prose)<=180 and re.search(r'\b(región|zonas?|costas?|océanos?|lagos?|ríos?|mares?|bosques?|cuevas?|lugares?)\b',prose,re.I):out.setdefault(vid,set()).add((prose,*match))
            if not added and match[0]=='tera raid' and tail.strip():
                out.setdefault(vid,set()).add(('Ubicación no especificada',*match))
    return out

def build(entry_ids):
    wiki=json.loads((CACHE/'wikidex-encounters/index.json').read_text())
    legacy=json.loads((CACHE/'es_fill.json').read_text());locations={r['id']:r for r in rows('locations')}
    loc_en={r['location_id']:r['name'] for r in rows('location_names') if r['local_language_id']=='9'}
    loc_es={r['location_id']:r['name'] for r in rows('location_names') if r['local_language_id']=='7'}
    area_en={r['location_area_id']:r['name'] for r in rows('location_area_prose') if r['local_language_id']=='9'}
    areas={r['id']:r for r in rows('location_areas')};slots={r['id']:r for r in rows('encounter_slots')};methods={r['id']:r['identifier'] for r in rows('encounter_methods')}
    versions={int(r['id']):r for r in rows('versions')}; name_records={}; area_records={};unknown=set()
    extra_path=CACHE/'wikidex-encounters/translations.json'; extra=json.loads(extra_path.read_text()) if extra_path.exists() else {}
    def spanish_location(lid):
        loc=locations[lid]; en=loc_en.get(lid,loc['identifier']);rid=loc['region_id'];key=rid+':'+en
        rec=wiki['names'].get(key) or wiki.get('candidate_names',{}).get(en)
        if not rec:
            norm=lambda x:re.sub(r'[^a-z0-9]','',re.sub(r'^(Sea |Kanto |Johto |Hoenn |Sinnoh |Unova |Kalos |Alola |Galar )','',x).lower())
            matches=[v for k,v in wiki['names'].items() if k.split(':',1)[0]==rid and norm(re.sub(r' \([^()]+\)$','',k.split(':',1)[1]).replace('Mount ','Mt. '))==norm(en)]
            if matches:rec=matches[0]
        if not rec and en in legacy.get('locations',{}) and rid=='5':rec=legacy['locations'][en]
        if not rec:
            trans=loc_es.get(lid) or extra.get(en)
            if not trans and re.fullmatch(r'(Sea )?Route \d+',en):trans='Ruta '+en.split()[-1]
            if not trans:unknown.add(en);trans='Lugar sin traducción ('+lid+')'
            rec={'name_es':trans,'status':'translated','note':'PokeAPI Spanish or curated fallback; no WikiDex English-link match'}
        name_records[lid]=dict(rec,english=en,region=rid)
        return en,rec['name_es']
    def spanish_area(aid):
        a=areas[aid];en,es=spanish_location(a['location_id']);prose=area_en.get(aid,'');area=en+(' / '+prose if prose and prose!=en else '')
        old=legacy.get('areas',{}).get(en+(' / '+prose if prose else '')) if locations[a['location_id']]['region_id']=='5' else None
        if old:out=old['area_es'];status=old.get('status','translated')
        else:
            # Keep only the actual subarea suffix; omit repeated English location prose.
            suffix='';matched=not prose
            variants={en,en.replace('Mt. ','Mount ').replace('Pokémon','Pokemon'),re.sub(r'^(Sea )?Route ', 'Road ',en),en.replace("'",'').replace('’','')}
            for variant in sorted(variants,key=len,reverse=True):
                m=re.match(re.escape(variant)+r'(?=$|[ (])',prose,re.I)
                if m:suffix=prose[m.end():].strip();matched=True;break
            if extra.get('area:'+prose):suffix=extra['area:'+prose];matched=True
            if not matched:
                suffix=extra.get('area:'+prose,'')
                matched=bool(suffix)
            if not matched:suffix='(sector '+aid+')'
            if suffix:
                suffix=re.sub(r'B(\d+)F',r'Sótano \1',suffix);suffix=re.sub(r'(\d+)F',r'Planta \1',suffix)
                for src,dst in [('Max Den','Nido Dinamax'),('unknown area','zona desconocida'),('entrance','entrada'),('outside','exterior'),('inside','interior'),('inner','interior'),('outer','exterior'),('roof','azotea'),('north','norte'),('south','sur'),('east','este'),('west','oeste'),('Hidden Grotto','Gruta oculta'),('Gym','Gimnasio')]:suffix=suffix.replace(src,dst)
                for src,dst in [("Zygarde's Chamber","Cámara de Zygarde"),('Heatran Chamber','Cámara de Heatran'),('Tower Summit','cumbre de la torre'),('North East of','al noreste de'),('South East of','al sureste de'),('North West of','al noroeste de'),('South West of','al suroeste de'),('North of','al norte de'),('South of','al sur de'),('East of','al este de'),('West Of','al oeste de'),('West of','al oeste de'),('Route','Ruta'),('Dewford Town','Pueblo Azuliza'),('Pacifidlog','Pueblo Oromar'),('Lilycove','Ciudad Calagua'),('Mossdeep','Ciudad Algaria'),('Fallarbor','Pueblo Pardal'),('Fortree','Ciudad Arborada'),('Rustboro','Ciudad Férrica'),('Deep','zona profunda'),('North','norte'),('South','sur'),('East','este'),('West','oeste'),('Lower','inferior'),('Upper','superior'),('Room','sala'),('Area','zona'),('area','zona'),('Road','Ruta'),('Square','plaza'),('exterior snowfall','exterior nevado'),('exterior blizzard','exterior con ventisca'),('small room','sala pequeña'),('private room','habitación privada'),('dining room','comedor'),('leftmost room','habitación del extremo izquierdo'),('rightmost room','habitación del extremo derecho'),('left room','habitación izquierda'),('right room','habitación derecha'),('middle room','habitación central'),('from exterior','desde el exterior'),('Lower Cave','cueva inferior'),('Upper Cave','cueva superior'),('mountainside','ladera'),('top','cima'),('cave gate','entrada de la cueva'),('inside cave','interior de la cueva'),('back/small room','fondo / sala pequeña'),('small room','sala pequeña'),('entrance','entrada'),('towards','hacia'),('Jubilife City','Ciudad Jubileo'),('Floaroma Town','Pueblo Aromaflor'),('Eterna City','Ciudad Vetusta'),('Solaceon Town','Pueblo Sosiego'),('Celestic Town','Pueblo Caelestis'),('Hearthome City','Ciudad Corazón'),('Pastoria City','Ciudad Pradera'),('Viridian City','Ciudad Verde'),('Pewter City','Ciudad Plateada')]:suffix=suffix.replace(src,dst)
                for src,dst in [('inferior Cave','cueva inferior'),('superior Cave','cueva superior'),('interior cave','interior de la cueva'),('cave behind team rocket','cueva detrás del Team Rocket'),('cave','cueva'),('room','sala'),('Victory Road gate','entrada de Calle Victoria'),('Kyogre’s','de Kyogre'),('Groudon’s','de Groudon'),('Rayquaza’s','de Rayquaza'),('Wilds Water World','Salvaje: mundo acuático'),('Wilds Cave World','Salvaje: mundo de cuevas'),('Shoal Cave','Cueva Cardumen'),('Water','Agua'),('Grass','Planta'),('Dark','Siniestro'),('Lake','lago'),('Near Station','cerca de la estación')]:suffix=suffix.replace(src,dst)
                # Never hide an untranslated qualifier: retain the stable area ID instead.
                if re.search(r'\b(area|gate|room|near|forest|floor|lake|small|large|cave|stairs|dark|pond|water|grass|island|surfing|fishing)\b',suffix,re.I):suffix='(sector '+aid+')'

            out=es+(' / '+suffix if suffix else '');status='translated' if suffix else name_records[a['location_id']]['status']
        area_records[aid]={'english':area,'area_es':out,'status':status,'location_id':a['location_id']}
        return area,out
    result=defaultdict(list);seen=defaultdict(set);raw_count=0
    for r in rows('encounters'):
        pid=int(r['pokemon_id']);vid=int(r['version_id']);method=methods[slots[r['encounter_slot_id']]['encounter_method_id']]
        if pid not in entry_ids or method not in METHODS:continue
        key=(vid,r['location_area_id'],method,int(r['min_level']),int(r['max_level']))
        if key in seen[pid]:continue
        seen[pid].add(key);raw_count+=1;en,es=spanish_area(r['location_area_id'])
        result[pid].append({'version':vid,'game':versions[vid]['identifier'].replace('-',' ').title(),'game_es':GAME_ES[vid],'area':en,'area_es':es,'method':method.replace('-',' '),'method_es':METHODS[method],'min':key[3],'max':key[4]})
    # Different upstream area IDs can describe the same visible area/method/level
    # row. Deduplicate the actual retained fields as well as source slot rows.
    for pid in result:
        result[pid]=list({json.dumps(r,ensure_ascii=False,sort_keys=True):r for r in result[pid]}.values())
    raw_count=sum(len(rs) for rs in result.values())
    valid={x for a in wiki['regions'].values() for x in a}|set(wiki.get('validated_place_aliases',{}))
    # WikiDex uses combined regional-language page titles, while species pages link
    # their individual aliases. Both aliases are documented on the same page.
    for title in list(valid):
        for alias in title.split('/'):
            valid.add(alias)
            qualifier=re.search(r' (\([^()]+\))$',title)
            if qualifier and '(' not in alias:valid.add(alias+' '+qualifier.group(1))
    dlc_locations={}
    for rid,kind in [('11','noroteo'),('12','biodomo'),('14','megadimension')]:
        for title in wiki['regions'].get(rid,[]):
            dlc_locations[title]=kind
            for alias in title.split('/'):dlc_locations[alias]=kind
    # Supplement only games with no CSV wild records for this species. A page does not
    # promise encounter levels/methods: leave them null and label them unspecified.
    wiki_count=0; evidence={};wiki_extra_names=set()
    for sid,rec in wiki['species'].items():
        pid=int(sid)
        if pid not in entry_ids:continue
        have={r['version'] for r in result[pid]}
        for vid,titles in wild_links(rec,valid,dlc_locations).items():
            if vid in have:continue
            for title,method,method_es in sorted(titles):
                result[pid].append({'version':vid,'game':versions[vid]['identifier'].replace('-',' ').title(),'game_es':GAME_ES[vid],'area':title,'area_es':title,'method':method,'method_es':method_es,'min':None,'max':None})
                wiki_count+=1;wiki_extra_names.add(title)
            evidence[str(pid)+':'+str(vid)]={'url':rec['url'],'revision':rec['revision'],'areas':[title for title,method,method_es in sorted(titles)]}
    for pid in result:result[pid].sort(key=lambda r:(r['version'],r['area_es'],r['method'],r['min'] or 0,r['max'] or 0))
    stats=[]
    for vid,v in versions.items():
        selected=[(pid,r) for pid,rs in result.items() for r in rs if r['version']==vid]
        stats.append({'version':vid,'name':GAME_ES[vid],'species':len({pid for pid,r in selected if pid<=1025}),'forms':len({pid for pid,r in selected if pid>1025}),'areas':len({r['area_es'] for pid,r in selected}),'rows':len(selected)})
    report={'games':stats,'location_names':dict(Counter(r['status'] for r in name_records.values())),'area_names':dict(Counter(r['status'] for r in area_records.values())),'csv_rows_after_dedup':raw_count,'wikidex_rows':wiki_count,'wikidex_supplement_area_names':len(wiki_extra_names),'untranslated_locations':sorted(unknown),'notes':['Exact version IDs retained. Slot probabilities/conditions omitted: rows are a location index, not unconditional availability.','WikiDex supplements have no invented level/method. Forms are not inferred from species pages.','WikiDex Noroteo/Biodomo categories identify Scarlet/Violet DLC locations; explicit dimensional Z-A locations identify Mega Dimension. Other ambiguous clauses are not inferred.']}
    (CACHE/'wikidex-encounters/resolved-names.json').write_text(json.dumps({'locations':name_records,'areas':area_records,'evidence':evidence},ensure_ascii=False,indent=1))
    return result,report,[{'versions':ids,'name_es':name,'name':' / '.join(versions[v]['identifier'].replace('-',' ').title() for v in ids)} for ids,name in GROUPS]

def apply(assets):
    index=json.loads((assets/'data/index.json').read_text());result,report,games=build({e['id'] for e in index})
    for e in index:
        p=assets/f"data/pokemon/{e['id']}.json";d=json.loads(p.read_text());d['encounters']=result[e['id']];p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
    (assets/'data/encounter-games.json').write_text(json.dumps(games,ensure_ascii=False,separators=(',',':')))
    (CACHE/'wikidex-encounters/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    manifest=assets/'data/manifest.json';d=json.loads(manifest.read_text())
    for p in sorted((assets/'data').rglob('*.json')):
        if p!=manifest:d['files'][str(p.relative_to(assets))]=hashlib.sha256(p.read_bytes()).hexdigest()
    d['encounters']={'source':'PokeAPI CSV + WikiDex cached Localización templates','report':'cache/wikidex-encounters/report.json','rows':report['csv_rows_after_dedup']+report['wikidex_rows']}
    manifest.write_text(json.dumps(d,ensure_ascii=False,indent=2))
    print('ENCOUNTERS_OK',d['encounters']['rows'],'rows;',report['location_names'],'location names;',len(report['untranslated_locations']),'unresolved')
    return report
