#!/usr/bin/env python3
"""Rerunnable source fix + offline cached encounter asset generation.
Run after older apply_* source fixes, then stage/build. No downloads or phone I/O.
"""
from pathlib import Path
from encounter_data import apply
ROOT=Path(__file__).resolve().parents[1]

def patch():
    p=ROOT/'tools/fetch_data.py';s=p.read_text()
    marker='# All-game encounter index (offline WikiDex cache; idempotent final generation step).'
    if marker not in s:s+='\n'+marker+'\nfrom encounter_data import apply as apply_all_encounters\napply_all_encounters(ASSETS)\n'
    # Preserve existing generated files/cache even when regenerating a subset.
    s=s.replace("if obsolete.stem not in record_ids: obsolete.unlink()","if obsolete.stem not in record_ids: pass # Preserved by owner request.")
    s=s.replace("if obsolete.is_file() and obsolete not in selected_paths: obsolete.unlink()","if obsolete.is_file() and obsolete not in selected_paths: pass # Preserved by owner request.")
    p.write_text(s)
    p=ROOT/'templates/src/org/kyf37/pokedex/PokedexActivity.java';s=p.read_text()
    s=s.replace('int screen=0, selection=0, tab=0, page=0, menu=0,','int areaGame=11; JSONArray encounterGames=new JSONArray();\n        int screen=0, selection=0, tab=0, page=0, menu=0,') if 'JSONArray encounterGames=' not in s else s
    anchor='JSONArray array=new JSONArray(read(a.getAssets().open("data/index.json")));'
    if 'final JSONArray gameChoices=' not in s:
        s=s.replace(anchor,'final JSONArray gameChoices=new JSONArray(read(a.getAssets().open("data/encounter-games.json")));\n                '+anchor)
        s=s.replace('all.addAll(entries); loaded=true;','all.addAll(entries); encounterGames=gameChoices; loaded=true;')
    s=s.replace('else if(tab==4 && evoRows().length()>0)', 'else if(tab==3){areaGame=DexLogic.wrap(areaGame+1,encounterGames.length());page=0;}else if(tab==4 && evoRows().length()>0)') if 'areaGame+1' not in s else s
    # 0 was unused on detail screens: previous game, OK next; arrows keep their existing paging/tab roles.
    anchor='if(k==KeyEvent.KEYCODE_DPAD_LEFT){tab='
    if 'KEYCODE_0&&tab==3' not in s:s=s.replace(anchor,'if(k==KeyEvent.KEYCODE_0&&tab==3){areaGame=DexLogic.wrap(areaGame-1,encounterGames.length());page=0;}\n                else '+anchor)
    s=s.replace('tab==3?array("encounters"):evoRows()','tab==3?areaRows():evoRows()')
    start=s.index('        JSONArray areaRowsCache=') if '        JSONArray areaRowsCache=' in s else s.index('        JSONObject areaGameChoice(){') if '        JSONObject areaGameChoice(){' in s else s.index('        void drawArea(Canvas c){');end=s.index('        void drawEvolve(Canvas c){',start)
    s=s[:start]+'''        JSONArray areaRowsCache=new JSONArray();JSONObject areaRowsDetail;int areaRowsGame=-1;
        JSONObject areaGameChoice(){JSONObject g=encounterGames.optJSONObject(DexLogic.wrap(areaGame,encounterGames.length()));return g==null?new JSONObject():g;}
        JSONArray areaRows(){
            if(areaRowsDetail==detail&&areaRowsGame==areaGame)return areaRowsCache;
            areaRowsDetail=detail;areaRowsGame=areaGame;
            JSONArray out=new JSONArray(), versions=areaGameChoice().optJSONArray("versions"), rows=array("encounters");
            if(versions==null){areaRowsCache=out;return out;}
            for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;
                for(int j=0;j<versions.length();j++)if(r.optInt("version")==versions.optInt(j)){out.put(r);break;}}
            areaRowsCache=out;return out;
        }
        void drawArea(Canvas c){
            JSONArray a=areaRows();JSONObject g=areaGameChoice();
            text(c,fit(dstr(g,"name"),16,410),32,470,16,accent);
            text(c,tr("0 previous game · OK next · ↑↓ areas","0 juego anterior · OK siguiente · ↑↓ zonas"),32,492,13,muted);
            if(a.length()==0){wrapText(c,tr("No data for this game","Sin datos para este juego"),32,536,410,20,29,ink,3);
                wrapText(c,tr("No wild encounter is recorded in the cached sources for this species or form. Evolution, gifts and transfers are not listed.","Las fuentes guardadas no registran encuentros salvajes para esta especie o forma. No se incluyen evoluciones, regalos ni transferencias."),32,603,410,16,24,muted,5);return;}
            for(int n=0;n<3&&page*3+n<a.length();n++){
                JSONObject area=a.optJSONObject(page*3+n);if(area==null)continue;float y=517+n*65;
                wrapText(c,dstr(area,"area"),32,y,412,16,19,ink,2);
                String levels=area.isNull("min")?tr("Level unspecified","Nivel sin especificar"):tr("Lv ","Nv ")+area.optInt("min")+"–"+area.optInt("max");
                text(c,fit(dstr(area,"game")+" · "+levels,12,410),32,y+35,12,accent);
                text(c,fit(dstr(area,"method"),12,410),32,y+51,12,muted);
            }
            text(c,tr("Location index · conditions may apply","Índice de lugares · puede haber condiciones"),32,728,12,muted);
        }
''' +s[end:]
    s='\n'.join(line for line in s.split('\n') if not line.lstrip().startswith('if(screen==1&&tab==3)desc'))
    s=s.replace('if(!desc.contentEquals(', 'if(screen==1&&tab==3)desc=desc.replace(tr("0 searches.","0 busca."),tr("0 previous game.","0 juego anterior."))+" "+dstr(areaGameChoice(),"name")+tr(". 0 previous game, OK next game, up/down areas.",". 0 juego anterior, OK siguiente juego, arriba/abajo zonas.");\n            if(!desc.contentEquals(')
    if '.putInt("areaGame",areaGame)' not in s:
        s=s.replace('.putInt("selected",selectedId())','.putInt("selected",selectedId()).putInt("areaGame",areaGame)')
        s=s.replace('restoreId=prefs.getInt("selected",494);','areaGame=prefs.getInt("areaGame",11);restoreId=prefs.getInt("selected",494);')
    s=s.replace('if(screen==1&&tab==3)desc+=" "+dstr', 'if(screen==1&&tab==3)desc=desc.replace(tr("0 searches.","0 busca."),tr("0 previous game.","0 juego anterior."))+" "+dstr')
    s=s.replace('tab==0?tr("TEXT","TEXTO"):tr("TOP","INICIO")','tab==0?tr("TEXT","TEXTO"):tab==3?tr("GAME","JUEGO"):tr("TOP","INICIO")')
    s=s.replace('"Registros sin conexión: PokéAPI / Veekun"','"Registros: PokéAPI / Veekun / WikiDex"')
    s=s.replace('"Offline records: PokéAPI / Veekun"','"Records: PokéAPI / Veekun / WikiDex"')
    s=s.replace('"6 reproduce el grito clásico"','"ZONA: 0 juego anterior; OK siguiente","6 reproduce el grito clásico"') if '"ZONA: 0 juego anterior;' not in s else s
    s=s.replace('"6 plays the original legacy cry"','"AREA: 0 previous game; OK next game", "6 plays the original legacy cry"') if '"AREA: 0 previous game;' not in s else s
    p.write_text(s)
    p=ROOT/'tools/verify_data.py' ;s=p.read_text()
    s=s.replace('# Black 2 / White 2 encounter areas: every row has a Spanish area that is not the English string.', '# All-game encounter rows retain their exact version and Spanish area/method labels.')
    s=s.replace("assert enc['area_es'] and enc['area_es'] != enc['area'],", "assert enc['area_es'] and enc['version'] > 0 and enc['method_es'],")
    p.write_text(s)

if __name__=='__main__':
    patch();apply(ROOT/'app/assets')
