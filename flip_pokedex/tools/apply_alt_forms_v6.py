#!/usr/bin/env python3
"""Rerunnable patch: adds Gen VI-IX alternate forms (regional, battle, size, mode and mask forms).

Edits exact text in tools/fetch_data.py and tools/verify_data.py. The new forms reuse the existing
pokemon-id form mechanism (ids 10001-10024 for Gen V): one record per form with id = its PokeAPI
pokemon id, its own types, base stats, abilities, height and weight, and static sprites under
sprites/pokemon/<id>.png (shiny, back and back-shiny when present). Their cries use the form's
legacy or latest cry, or the species cry when PokeAPI has none.

Rules: species #1-1025 only; Mega, Gigantamax, Eternamax and Let's Go starter forms are skipped;
a form is kept only when its types or base stats differ from its species (cosmetic-only forms such
as Furfrou trims, Vivillon patterns and Alcremie decorations are skipped). Forms that share a pokemon
id with their species (for example Silvally types) are not added here and are listed in the report.

A pair whose new text is already present is skipped, so the script can be rerun safely. Any other
mismatch stops the run before anything is written.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FETCH = ROOT / 'tools/fetch_data.py'
VERIFY = ROOT / 'tools/verify_data.py'

FETCH_PAIRS = [
    ("(ASSETS/'data/pokemon').mkdir(parents=True,exist_ok=True)",
     """# Gen VI-IX alternate forms with their own types or base stats (regional, battle, size, mode and mask forms).
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
(ASSETS/'data/pokemon').mkdir(parents=True,exist_ok=True)"""),
    ("fn=form_names.get(form['id'],'') if form else ''",
     "fn=(form_names.get(form['id']) or (form['form_identifier'].replace('-',' ').title() if pid!=sid else '')) if form else ''"),
    ("chart,attackers=(efficacy_modern,19) if int(sid)>649 else (efficacy,18)",
     "chart,attackers=(efficacy_modern,19) if int(sid)>649 or pid in alt6_pids else (efficacy,18)"),
    ("selected_paths={dest for _,dest in selected}",
     """for pid in sorted(alt6_pids,key=int):
    for sub in ['','shiny/','back/','back/shiny/']:
        url=BASE+'sprites/'+PINS['sprites']+'/sprites/pokemon/'+sub+pid+'.png'; OPTIONAL_URLS.add(url)
        selected.append((url,ASSETS/'sprites'/(sub+pid+'.png')))
selected_paths={dest for _,dest in selected}"""),
    ("futures={ex.submit(get,url,dest):(url,dest) for url,dest in selected}",
     "futures={ex.submit(get_opt if url in OPTIONAL_URLS else get,url,dest):(url,dest) for url,dest in selected}"),
    ("with ThreadPoolExecutor(max_workers=6) as ex:",
     """for pid in sorted(alt6_pids,key=int):
    if pid+'.ogg' in cry_paths: cries.append((BASE+'cries/'+PINS['cries']+'/cries/pokemon/legacy/'+pid+'.ogg',ASSETS/'cries'/(pid+'.ogg')))
    else:
        url=BASE+'cries/'+PINS['cries']+'/cries/pokemon/latest/'+pid+'.ogg'; OPTIONAL_URLS.add(url)
        cries.append((url,ASSETS/'cries'/(pid+'.ogg')))
with ThreadPoolExecutor(max_workers=6) as ex:"""),
    ("ex.map(lambda pair:get(*pair),cries)",
     "ex.map(lambda pair:(get_opt if pair[0] in OPTIONAL_URLS else get)(*pair),cries)"),
    ("# Content manifest makes cached imports independently checkable",
     """# A form without its own cry uses its species cry (the Rotom rule).
for pid in sorted(alt6_pids,key=int):
    dest=ASSETS/'cries'/(pid+'.ogg'); src=ASSETS/'cries'/(pokemon[pid]['species_id']+'.ogg')
    if not dest.exists() and src.exists(): dest.write_bytes(src.read_bytes())
# Content manifest makes cached imports independently checkable"""),
]

VERIFY_PAIRS = [
    ("assert len(entries)==1109",
     """assert len(entries)==1219 # 1109 Gen I-V dex entries/forms plus 110 Gen VI-IX alternate forms
# Gen VI-IX alternate forms: own record, sprite files and a cry (Gen V form rules are unchanged).
alt6=[e for e in entries if 10025<=e['id']<200000]
assert len(alt6)==110 and all((r/f"sprites/{e['id']}.png").exists() and (r/f"cries/{e['id']}.ogg").exists() for e in alt6)"""),
]


def plan(path, pairs):
    text = path.read_text(encoding='utf-8')
    for old, new in pairs:
        if new in text:
            continue
        found = text.count(old)
        if found != 1:
            raise SystemExit(f'{path.name}: expected 1 match, found {found}: {old[:90]!r}')
        text = text.replace(old, new)
    return text


if __name__ == '__main__':
    out = {FETCH: plan(FETCH, FETCH_PAIRS), VERIFY: plan(VERIFY, VERIFY_PAIRS)}
    for path, text in out.items():
        path.write_text(text, encoding='utf-8')
    print('patched', FETCH.name, VERIFY.name)
