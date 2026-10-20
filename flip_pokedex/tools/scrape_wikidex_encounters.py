#!/usr/bin/env python3
"""Resumable WikiDex raw API cache. Offline runs never access the network.
Category/interlanguage names are region-qualified; species localisation templates
are retained as evidence, never expanded into invented methods or levels.
"""
import argparse, csv, hashlib, json, re, time, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CACHE=ROOT/'cache'; RAW=CACHE/'wikidex-encounters/raw'
REGIONS={1:'Kanto',2:'Johto',3:'Hoenn',4:'Sinnoh',5:'Teselia',6:'Kalos',7:'Alola',8:'Galar',9:'Paldea',10:'Hisui',11:'Noroteo',12:'Biodomo',13:'Archi7',14:'Luminalia Dimensional'}
UA='FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'
SITE='https://www.wikidex.net/wiki/'; last=0

def rows(name):
    with (CACHE/(name+'.csv')).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def api(fetch, **params):
    global last
    params.update(action='query',format='json'); query=urllib.parse.urlencode(sorted(params.items()))
    path=RAW/(hashlib.sha256(query.encode()).hexdigest()+'.json')
    if path.exists():return json.loads(path.read_text())['response']
    if not fetch:raise RuntimeError('Uncached WikiDex request: '+query[:160])
    RAW.mkdir(parents=True,exist_ok=True)
    for attempt in range(6):
        time.sleep(1.5); last=time.monotonic()
        try:
            req=urllib.request.Request('https://www.wikidex.net/api.php?'+query,headers={'User-Agent':UA})
            with urllib.request.urlopen(req,timeout=120) as f:d=json.load(f)
            if 'error' in d:raise RuntimeError(str(d['error']))
            path.write_text(json.dumps({'query':params,'response':d},ensure_ascii=False));return d
        except Exception:
            if attempt==5:raise
            time.sleep(3*(attempt+1))

def categories(region,fetch):
    seen=set(); pages=set(); todo=[{'Biodomo':'Categoría:Lugares de la Academia Arándano','Archi7':'Categoría:Archi7'}.get(region,'Categoría:Lugares de '+region)]
    while todo:
        cat=todo.pop()
        if cat in seen:continue
        seen.add(cat); cont={}
        while True:
            d=api(fetch,list='categorymembers',cmtitle=cat,cmlimit=500,**cont)
            for p in d['query']['categorymembers']:
                t=p['title']
                if re.search(r'anime|Special|Pokopia|Mapas|Introducciones|Imágenes|Manga',t,re.I):continue
                if p['ns']==14:todo.append(t)
                elif p['ns']==0:pages.add(t)
            if 'continue' not in d:break
            cont=d['continue']
    return sorted(pages)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fetch',action='store_true');args=ap.parse_args()
    out={'regions':{},'names':{},'species':{},'source':SITE,'delay_seconds':1.5}
    for rid,region in REGIONS.items():
        titles=categories(region,args.fetch);out['regions'][str(rid)]=titles
        for i in range(0,len(titles),50):
            cont={}
            while True:
                d=api(args.fetch,prop='langlinks',lllang='en',lllimit=500,titles='|'.join(titles[i:i+50]),**cont)
                for p in d['query']['pages'].values():
                    for link in p.get('langlinks',[]):
                        en=link['*'];en=re.sub(r'^(Kanto|Johto|Hoenn|Sinnoh|Unova|Kalos|Alola|Galar|Paldea|Hisui) ','',en)
                        en=en.replace(' (Pokémon)','')
                        out['names'][str({11:9,12:9,13:1,14:6}.get(rid,rid))+':'+en]={'name_es':p['title'],'status':'wikidex','url':SITE+urllib.parse.quote(p['title'].replace(' ','_'))}
                if 'continue' not in d:break
                cont=d['continue']
        print('REGION',region,len(titles),flush=True)
        (CACHE/'wikidex-encounters/names-progress.json').write_text(json.dumps(out,ensure_ascii=False))
    out['candidate_names']={}
    translations=json.loads((CACHE/'wikidex-encounters/translations.json').read_text())
    candidates=sorted({v for k,v in translations.items() if not k.startswith('area:')})
    found={}
    for i in range(0,len(candidates),50):
        d=api(args.fetch,titles='|'.join(candidates[i:i+50]),redirects=1)
        aliases={x['from']:x['to'] for x in d['query'].get('redirects',[])}
        aliases.update({x['from']:x['to'] for x in d['query'].get('normalized',[])})
        pages={p['title']:p for p in d['query']['pages'].values() if 'missing' not in p}
        for title in candidates[i:i+50]:
            resolved=aliases.get(title,title)
            if resolved in pages:found[title]=resolved
    for en,title in translations.items():
        if not en.startswith('area:') and title in found:
            title=found[title]
            out['candidate_names'][en]={'name_es':title,'status':'wikidex','url':SITE+urllib.parse.quote(title.replace(' ','_')),'note':'Verified Spanish candidate title; no English interlanguage match'}
    names={int(r['pokemon_species_id']):r['name'] for r in rows('pokemon_species_names') if r['local_language_id']=='7'}
    for start in range(1,1026,20):
        ids=list(range(start,min(start+20,1026))); titles=[names[i] for i in ids]
        d=api(args.fetch,prop='revisions',rvprop='content|ids',rvslots='main',redirects=1,titles='|'.join(titles))
        by_title={p['title']:p for p in d['query']['pages'].values()}
        redirects={p['from']:p['to'] for p in d['query'].get('redirects',[])}
        redirects.update({p['from']:p['to'] for p in d['query'].get('normalized',[])})
        for sid,title in zip(ids,titles):
            resolved=title
            for _ in range(5):resolved=redirects.get(resolved,resolved)
            p=by_title.get(resolved,{}); rev=p.get('revisions',[{}])[0]; text=rev.get('slots',{}).get('main',{}).get('*','')
            m=re.search(r'\{\{\s*Localización\s*\n',text,re.I)
            if m:
                pos=m.start();depth=0;end=None
                for tok in re.finditer(r'\{\{|\}\}',text[pos:]):
                    depth+=1 if tok.group()=='{{' else -1
                    if depth==0:end=pos+tok.end();break
                if end:out['species'][str(sid)]={'title':p['title'],'revision':rev.get('revid'),'localizacion':text[pos:end],'url':SITE+urllib.parse.quote(p['title'].replace(' ','_'))}
        print('SPECIES',start,len(out['species']),flush=True)
    # Verify place-link aliases missed by the category walk (redirects and pages
    # categorised under a different geographic root). Pokemon/mechanics links
    # never become encounter areas just because they occur in a wild bullet.
    from encounter_data import wild_links
    class AnyTitle:
        def __contains__(self,title):return True
    known={t for ts in out['regions'].values() for t in ts}
    targets=sorted({t for rec in out['species'].values() for vals in wild_links(rec,AnyTitle()).values() for t,method,es in vals if t not in known})
    out['validated_place_aliases']={}
    for start in range(0,len(targets),50):
        batch=targets[start:start+50];cont={};found={};aliases={}
        while True:
            d=api(args.fetch,prop='categories',cllimit=500,redirects=1,titles='|'.join(batch),**cont)
            for key in ['redirects','normalized']:
                aliases.update({p['from']:p['to'] for p in d['query'].get(key,[])})
            for p in d['query']['pages'].values():
                if any(re.search(r'^Categoría:(Lugares|Rutas|Ciudades|Pueblos|Bosques|Cuevas|Montañas|Mares|Lagos|Islas|Edificios|Áreas) (de|del)',c['title']) for c in p.get('categories',[])):found[p['title']]=p['title']
            if 'continue' not in d:break
            cont=d['continue']
        for title in batch:
            resolved=title
            for _ in range(5):resolved=aliases.get(resolved,resolved)
            if resolved in found:out['validated_place_aliases'][title]=resolved
        print('PLACE_ALIASES',start,len(targets),len(out['validated_place_aliases']),flush=True)
    (CACHE/'wikidex-encounters/index.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
    print('WIKIDEX_CACHE_OK',len(out['names']),len(out['species']))
if __name__=='__main__':main()
