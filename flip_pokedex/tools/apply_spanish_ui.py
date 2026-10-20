#!/usr/bin/env python3
"""Rerunnable patch: adds Spanish (es) UI and data lookups to the canonical Java sources in templates/src.

Each replacement is exact. A replacement whose new text is already present is skipped,
so the script can be rerun safely. Anything else that does not match exactly stops the run.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'templates/src/org/kyf37/pokedex'

DEXLOGIC = [
    ('import java.util.*;\n\n/** Android-free',
     'import java.text.Normalizer;\nimport java.util.*;\n\n/** Android-free', 1),
    ('''    public static String t9(String name) {
        StringBuilder out = new StringBuilder();
        for (char c : name.toLowerCase(Locale.ROOT).toCharArray()) {''',
     '''    /** Lowercase letters with accents removed, so Spanish names such as Ñ and É match T9 keys. */
    public static String fold(String name) {
        return Normalizer.normalize(name, Normalizer.Form.NFD).replaceAll("\\\\p{M}+", "").toLowerCase(Locale.ROOT);
    }
    /** True for the Spanish locale language code. */
    public static boolean spanish(String language) { return "es".equals(language); }
    public static String t9(String name) {
        StringBuilder out = new StringBuilder();
        for (char c : fold(name).toCharArray()) {''', 1),
]

POKEDEX = [
    # Entry: Spanish name from index.json
    ('int id, species, unova, national; String name, form, sprite; JSONArray types;',
     'int id, species, unova, national; String name, nameEs, form, sprite; JSONArray types;', 1),
    ('name=o.getString("name"); form=o.getString("form");',
     'name=o.getString("name"); nameEs=o.optString("name_es",""); form=o.getString("form");', 1),
    # DexView state
    ('String query="", status="Loading offline records…", error="", toast="";',
     'String query="", status="", error="", toast="";', 1),
    ('final String[] tabs={"ENTRY","STATS","MOVES","AREA","EVOLVE"};',
     'final String[] tabs; final boolean es; final HashMap<String,String> typesEs=new HashMap<>();', 1),
    ('super(a); activity=a; setFocusable(true); setFocusableInTouchMode(true);',
     'super(a); activity=a; setFocusable(true); setFocusableInTouchMode(true);\n'
     '            es=DexLogic.spanish(Locale.getDefault().getLanguage());\n'
     '            tabs=es?new String[]{"FICHA","STATS","MOVIM.","ZONA","EVOLUC."}:new String[]{"ENTRY","STATS","MOVES","AREA","EVOLVE"};\n'
     '            status=tr("Loading offline records…","Cargando registros sin conexión…");\n'
     '            if(es)loadTypesEs(a);', 1),
    ('error="Offline data could not be loaded. Reinstall the complete APK.";',
     'error=tr("Offline data could not be loaded. Reinstall the complete APK.","No se pudieron cargar los datos sin conexión. Reinstale el APK completo.");', 1),
    # Helpers, placed after entry()
    ('        Entry entry(){return filtered.isEmpty()?null:filtered.get(DexLogic.clamp(selection,filtered.size()));}',
     '''        Entry entry(){return filtered.isEmpty()?null:filtered.get(DexLogic.clamp(selection,filtered.size()));}
        String tr(String en,String spanish){return es?spanish:en;}
        String nm(Entry e){return es&&!e.nameEs.isEmpty()?e.nameEs:e.name;}
        String tn(String type){return es&&typesEs.containsKey(type)?typesEs.get(type):type;}
        String tOpt(int i){return i==0?tr("All types","Todos los tipos"):tn(typeOptions[i]);}
        void loadTypesEs(Activity a){
            try{JSONObject map=new JSONObject(read(a.getAssets().open("data/i18n_es.json"))).getJSONObject("types");
                for(Iterator<String> it=map.keys();it.hasNext();){String k=it.next();typesEs.put(k,map.getString(k));}
            }catch(Exception ignored){}
        }
        String dstr(JSONObject o,String key){if(es){String v=o.optString(key+"_es","");if(!v.isEmpty())return v;}return o.optString(key);}
        JSONArray dstrs(JSONObject o,String key){
            if(es){JSONArray v=o.optJSONArray(key+"_es");if(v!=null&&v.length()>0)return v;}
            JSONArray v=o.optJSONArray(key);return v==null?new JSONArray():v;
        }
        String methodLabel(String m){
            if(!es)return m;
            switch(m){case "level-up":return "nivel";case "machine":return "MT/MO";case "egg":return "huevo";case "tutor":return "tutor";default:return m;}
        }
        String catLabel(String c){
            if(!es)return c;
            switch(c){case "Physical":return "Físico";case "Special":return "Especial";case "Status":return "Estado";default:return c;}
        }
        String[] flavorText(){
            String key=whiteText?"white2":"black2";
            String record=tr(whiteText?"WHITE 2 RECORD":"BLACK 2 RECORD",whiteText?"REGISTRO BLANCO 2":"REGISTRO NEGRO 2");
            if(es){
                String own=detail.optString(key+"_es","");if(!own.isEmpty())return new String[]{own,record};
                String other=detail.optString("fallbackText_es","");if(!other.isEmpty())return new String[]{other,"TEXTO DE OTRO JUEGO"};
            }
            String en=detail.optString(key,"");if(!en.isEmpty())return new String[]{en,record};
            return new String[]{detail.optString("fallbackText"),tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")};
        }
        String[] helpEs(){return new String[]{"D-pad mueve; OK abre una ficha.","Izq/Der cambia pestañas o páginas.","0 busca por número; * busca por nombre T9.","T9: 2 ABC · 3 DEF · 4 GHI · 5 JKL","6 MNO · 7 PQRS · 8 TUV · 9 WXYZ","Clear/# borra; OK abre un resultado.","1 favorito · 5 capturado · 2/8 ant./sig.","Ficha: 3 forma · 7 espalda · 9 hembra","6 reproduce el grito clásico","# brillante · * opciones · Clear vuelve","","Registros sin conexión: PokéAPI / Veekun","Sprites: PokeAPI/sprites (Gen V)","Pokémon © Nintendo / Creatures /","GAME FREAK. Proyecto de fans no oficial.","Sprites Gen V compartidos B/N;","las animaciones de B2W2 pueden variar.","9 en lista: identificar foto offline"};}''', 1),
    # Filters and sorting use the displayed name, with English as a fallback for T9.
    ('if(!DexLogic.matches(e.name,national?e.national:e.unova,query,searchName))continue;',
     'if(!DexLogic.matches(nm(e),national?e.national:e.unova,query,searchName)&&!DexLogic.matches(e.name,national?e.national:e.unova,query,searchName))continue;', 1),
    ('sort==1?a.name.compareTo(b.name):', 'sort==1?nm(a).compareTo(nm(b)):', 1),
    # Notices
    ('notice("Cry unavailable");', 'notice(tr("Cry unavailable","Grito no disponible"));', 1),
    ('notice("No legacy cry for this form");', 'notice(tr("No legacy cry for this form","Esta forma no tiene grito clásico"));', 1),
    ('void toggle(Set<String> set,String label){', 'void toggle(Set<String> set,String label,String labelEs){', 1),
    ('notice(label+(add?" added":" removed"));', 'notice((es?labelEs:label)+(add?tr(" added"," añadido"):tr(" removed"," quitado")));', 1),
    ('toggle(caught,"Caught");', 'toggle(caught,"Caught","Capturado");', 2),
    ('toggle(favorites,"Favorite");', 'toggle(favorites,"Favorite","Favorito");', 2),
    ('notice("No alternate forms in Gen V");', 'notice(tr("No alternate forms in Gen V","No hay formas alternativas en Gen V"));', 1),
    # Hero badges
    ('text(c,shiny?"SHINY":"NORMAL",32,y+24,13,muted);', 'text(c,shiny?tr("SHINY","BRILLANTE"):"NORMAL",32,y+24,13,muted);', 1),
    ('if(rear)text(c,"BACK",32,y+44,13,muted);', 'if(rear)text(c,tr("BACK","ESPALDA"),32,y+44,13,muted);', 1),
    ('text(c,"♀ / DEFAULT",32,y+64,13,muted);', 'text(c,tr("♀ / DEFAULT","♀ / PREDET."),32,y+64,13,muted);', 1),
    # List screen
    ('String mode=national?"NATIONAL / 649":"UNOVA / B2·W2";',
     'String mode=national?tr("NATIONAL / 649","NACIONAL / 649"):"UNOVA / B2·W2";', 1),
    ('subhead(c,screen==3?(searchName?"NAME / T9":"NUMBER SEARCH"):mode,filtered.size()+" entries");',
     'subhead(c,screen==3?(searchName?tr("NAME / T9","NOMBRE / T9"):tr("NUMBER SEARCH","BUSCAR NÚMERO")):mode,filtered.size()+tr(" entries"," entradas"));', 1),
    ('text(c,query.isEmpty()?(searchName?"Type name: 2 ABC · 3 DEF…":"Enter Pokédex number…"):query,34,178,23,query.isEmpty()?muted:ink);text(c,"* mode   # erase   OK open   Clear return",24,227,17,muted);',
     'text(c,query.isEmpty()?(searchName?tr("Type name: 2 ABC · 3 DEF…","Escribe nombre: 2 ABC · 3 DEF…"):tr("Enter Pokédex number…","Escribe el número…")):query,34,178,23,query.isEmpty()?muted:ink);text(c,tr("* mode   # erase   OK open   Clear return","* modo   # borra   OK abre   Clear vuelve"),24,227,17,muted);', 1),
    ('text(c,"No. "+number(e),30,387,19,muted);text(c,fit(e.name,25,305),145,388,25,ink);',
     'text(c,tr("No. ","Nº ")+number(e),30,387,19,muted);text(c,fit(nm(e),25,305),145,388,25,ink);', 1),
    ('text(c,collection==1?"FAVORITES":collection==2?"CAUGHT":typeFilter>0?typeOptions[typeFilter].toUpperCase(Locale.ROOT):"SEEN IN YOUR JOURNEY",24,422,13,muted);',
     'text(c,collection==1?tr("FAVORITES","FAVORITOS"):collection==2?tr("CAUGHT","CAPTURADOS"):typeFilter>0?tOpt(typeFilter).toUpperCase(Locale.ROOT):tr("SEEN IN YOUR JOURNEY","VISTOS EN TU DIARIO"),24,422,13,muted);', 1),
    ('if(e==null){center(c,"No matching Pokémon",240,365,24,ink);center(c,screen==3?"Clear erases / returns to the journal":"* Options → Reset filters",240,405,19,muted);return;}',
     'if(e==null){center(c,tr("No matching Pokémon","Ningún Pokémon coincide"),240,365,24,ink);center(c,screen==3?tr("Clear erases / returns to the journal","Clear borra / vuelve al diario"):tr("* Options → Reset filters","* Opciones → Borrar filtros"),240,405,19,muted);return;}', 1),
    ('text(c,fit(row.name,20,267),121,y+33,20,fg);', 'text(c,fit(nm(row),20,267),121,y+33,20,fg);', 1),
    ('text(c,"1 ★   5 caught   9 Identify",208,screen==3?749:756,14,muted);',
     'text(c,tr("1 ★   5 caught   9 Identify","1 ★   5 capturado   9 Identificar"),208,screen==3?749:756,14,muted);', 1),
    # Type names: keys stay English, labels are localized
    ('round(c,start+i*114,y,start+i*114+106,y+27,3,typeColor(t));center(c,t.toUpperCase(Locale.ROOT),',
     'round(c,start+i*114,y,start+i*114+106,y+27,3,typeColor(t));center(c,tn(t).toUpperCase(Locale.ROOT),', 1),
    # Detail screen
    ('subhead(c,fit("No. "+number(e)+"  "+e.name,18,318),national?"NATIONAL":"UNOVA");',
     'subhead(c,fit(tr("No. ","Nº ")+number(e)+"  "+nm(e),18,318),national?tr("NATIONAL","NACIONAL"):"UNOVA");', 1),
    ('center(c,"No selected entry",240,400,23,ink);', 'center(c,tr("No selected entry","Ninguna ficha seleccionada"),240,400,23,ink);', 1),
    ('center(c,"Loading entry…",240,550,20,muted);', 'center(c,tr("Loading entry…","Cargando ficha…"),240,550,20,muted);', 1),
    ('text(c,"▲ ▼ "+(page+1)+"/"+detailPages()+"   ◀ ▶ tabs",24,759,15,muted);text(c,"2/8 prev/next",324,759,14,muted);',
     'text(c,"▲ ▼ "+(page+1)+"/"+detailPages()+tr("   ◀ ▶ tabs","   ◀ ▶ pestañas"),24,759,15,muted);text(c,tr("2/8 prev/next","2/8 ant./sig."),324,759,14,muted);', 1),
    # Entry page
    ('text(c,detail.optString("genus"),32,474,20,ink);', 'text(c,dstr(detail,"genus"),32,474,20,ink);', 1),
    ('"HT  %.1f m       WT  %.1f kg"', '(es?"Alt. %.1f m     Peso %.1f kg":"HT  %.1f m       WT  %.1f kg")', 1),
    ('String flavor=detail.optString(whiteText?"white2":"black2");boolean fallback=flavor.isEmpty();if(fallback)flavor=detail.optString("fallbackText");',
     'String[] ft=flavorText();String flavor=ft[0];', 1),
    ('text(c,fallback?"EARLIER DEX RECORD":whiteText?"WHITE 2 RECORD":"BLACK 2 RECORD",32,548,13,accent);',
     'text(c,ft[1],32,548,13,accent);', 1),
    ('text(c,"OK: Black 2 / White 2 text",32,718,14,muted);', 'text(c,tr("OK: Black 2 / White 2 text","OK: texto Negro 2 / Blanco 2"),32,718,14,muted);', 1),
    ('text(c,"ABILITIES",32,474,15,accent);', 'text(c,tr("ABILITIES","HABILIDADES"),32,474,15,accent);', 1),
    ('text(c,a.optString("name")+(a.optBoolean("hidden")?"  [hidden]":""),32,y,20,ink);int lines=wrapText(c,a.optString("text"),32,y+25,412,16,21,muted,2);',
     'text(c,dstr(a,"name")+(a.optBoolean("hidden")?tr("  [hidden]","  [oculta]"):""),32,y,20,ink);int lines=wrapText(c,dstr(a,"text"),32,y+25,412,16,21,muted,2);', 1),
    ('text(c,"BREEDING & FIELD NOTES",32,474,15,accent);', 'text(c,tr("BREEDING & FIELD NOTES","CRIANZA Y NOTAS DE CAMPO"),32,474,15,accent);', 1),
    ('text(c,"Egg groups: "+join(array("eggGroups")),32,515,18,ink);',
     'text(c,tr("Egg groups: ","Grupos huevo: ")+join(dstrs(detail,"eggGroups")),32,515,18,ink);', 1),
    ('text(c,"Gender: "+(gender<0?"Genderless":String.format(Locale.ROOT,"%.1f%% female",gender*12.5)),32,552,18,ink);',
     'text(c,tr("Gender: ","Género: ")+(gender<0?tr("Genderless","Sin género"):String.format(Locale.ROOT,"%.1f%% "+tr("female","hembra"),gender*12.5)),32,552,18,ink);', 1),
    ('text(c,"Catch rate: "+detail.optInt("captureRate")+" / 255",32,589,18,ink);',
     'text(c,tr("Catch rate: ","Ratio de captura: ")+detail.optInt("captureRate")+" / 255",32,589,18,ink);', 1),
    ('text(c,"Base friendship: "+detail.optInt("friendship"),32,626,18,ink);',
     'text(c,tr("Base friendship: ","Amistad base: ")+detail.optInt("friendship"),32,626,18,ink);', 1),
    ('text(c,"Egg cycles: "+detail.optInt("hatchCounter"),32,663,18,ink);',
     'text(c,tr("Egg cycles: ","Ciclos de huevo: ")+detail.optInt("hatchCounter"),32,663,18,ink);', 1),
    ('text(c,"3 forms · 6 cry · 7 back · 9 female",32,710,15,muted);',
     'text(c,tr("3 forms · 6 cry · 7 back · 9 female","3 formas · 6 grito · 7 espalda · 9 hembra"),32,710,15,muted);', 1),
    # Stats
    ('String[] labels={"HP","ATTACK","DEFENSE","SP. ATK","SP. DEF","SPEED"};',
     'String[] labels=es?new String[]{"PS","ATAQUE","DEFENSA","AT. ESP.","DEF. ESP.","VELOCIDAD"}:new String[]{"HP","ATTACK","DEFENSE","SP. ATK","SP. DEF","SPEED"};', 1),
    ('text(c,"BASE STAT TOTAL",32,713,14,muted);', 'text(c,tr("BASE STAT TOTAL","TOTAL BASE"),32,713,14,muted);', 1),
    ('text(c,"DEFENSIVE TYPE MATCHUPS / GEN V",32,473,14,accent);',
     'text(c,tr("DEFENSIVE TYPE MATCHUPS / GEN V","DEBILIDADES Y RESISTENCIAS / GEN V"),32,473,14,accent);', 1),
    ('text(c,t.optString("type"),x,y,17,ink);', 'text(c,tn(t.optString("type")),x,y,17,ink);', 1),
    ('text(c,"Steel retains Ghost / Dark resistance.",32,718,14,muted);',
     'text(c,tr("Steel retains Ghost / Dark resistance.","Acero conserva resistencia a Fantasma / Siniestro."),32,718,14,muted);', 1),
    # Moves
    ('text(c,"B2·W2 LEARNSET · "+moves.length()+" RECORDS",32,474,14,accent);',
     'text(c,tr("B2·W2 LEARNSET · ","APRENDIZAJE B2·W2 · ")+moves.length()+tr(" RECORDS"," MOVIMIENTOS"),32,474,14,accent);', 1),
    ('wrapText(c,"No B2W2 learnset is recorded for this form in the source dataset.",32,525,405,19,28,ink,5);',
     'wrapText(c,tr("No B2W2 learnset is recorded for this form in the source dataset.","No hay aprendizaje B2W2 registrado para esta forma en el conjunto de datos."),32,525,405,19,28,ink,5);', 1),
    ('text(c,fit(m.optString("name"),20,255),32,y,20,ink);', 'text(c,fit(dstr(m,"name"),20,255),32,y,20,ink);', 1),
    ('String badge=method.equals("level-up")?"Lv. "+m.optInt("level"):method.equals("machine")?(m.optInt("machine")>=100?"HM"+(m.optInt("machine")-100):"TM"+m.optString("machine")):method.equals("egg")?"EGG":method.equals("tutor")?"TUTOR":method.toUpperCase(Locale.ROOT);',
     'String badge=method.equals("level-up")?tr("Lv. ","Nv. ")+m.optInt("level"):method.equals("machine")?(m.optInt("machine")>=100?tr("HM","MO")+(m.optInt("machine")-100):tr("TM","MT")+m.optString("machine")):method.equals("egg")?tr("EGG","HUEVO"):method.equals("tutor")?"TUTOR":method.toUpperCase(Locale.ROOT);', 1),
    ('text(c,m.optString("type")+" / "+m.optString("category")+"   PWR "+m.optString("power")+"  PP "+m.optString("pp"),32,y+23,14,muted);',
     'text(c,tn(m.optString("type"))+" / "+catLabel(m.optString("category"))+tr("   PWR ","   POT ")+m.optString("power")+"  PP "+m.optString("pp"),32,y+23,14,muted);', 1),
    ('subhead(c,"MOVE RECORD",(moveIndex+1)+" / "+array("moves").length());',
     'subhead(c,tr("MOVE RECORD","MOVIMIENTO"),(moveIndex+1)+" / "+array("moves").length());', 1),
    ('round(c,18,146,462,732,6,panel);text(c,fit(m.optString("name"),30,410),32,197,30,ink);',
     'round(c,18,146,462,732,6,panel);text(c,fit(dstr(m,"name"),30,410),32,197,30,ink);', 1),
    ('text(c,m.optString("type")+" / "+m.optString("category"),32,240,21,accent);',
     'text(c,tn(m.optString("type"))+" / "+catLabel(m.optString("category")),32,240,21,accent);', 1),
    ('text(c,"Power: "+m.optString("power")+"     Accuracy: "+m.optString("accuracy"),32,302,20,ink);',
     'text(c,tr("Power: ","Potencia: ")+m.optString("power")+tr("     Accuracy: ","     Precisión: ")+m.optString("accuracy"),32,302,20,ink);', 1),
    ('text(c,"Learn: "+m.optString("method")+" / Lv. "+m.optInt("level"),32,395,18,muted);',
     'text(c,tr("Learn: ","Aprende: ")+methodLabel(m.optString("method"))+tr(" / Lv. "," / Nv. ")+m.optInt("level"),32,395,18,muted);', 1),
    ('text(c,"Machine number: "+m.optString("machine"),32,432,18,muted);',
     'text(c,tr("Machine number: ","Número de MT/MO: ")+m.optString("machine"),32,432,18,muted);', 1),
    ('wrapText(c,m.optString("text"),32,495,410,22,32,ink,6);', 'wrapText(c,dstr(m,"text"),32,495,410,22,32,ink,6);', 1),
    ('text(c,"◀ ▶ previous / next move · Clear back",32,705,16,muted);',
     'text(c,tr("◀ ▶ previous / next move · Clear back","◀ ▶ movimiento anterior / siguiente · Clear atrás"),32,705,16,muted);', 1),
    # Areas
    ('text(c,"WILD ENCOUNTERS / BLACK 2 & WHITE 2",32,474,14,accent);',
     'text(c,tr("WILD ENCOUNTERS / BLACK 2 & WHITE 2","ENCUENTROS SALVAJES / NEGRO 2 Y BLANCO 2"),32,474,14,accent);', 1),
    ('wrapText(c,"No wild encounter is recorded. This Pokémon may require evolution, a gift, an event, a trade or transfer.",32,520,410,20,29,ink,5);text(c,"Dataset coverage is incomplete for gifts.",32,708,15,muted);',
     'wrapText(c,tr("No wild encounter is recorded. This Pokémon may require evolution, a gift, an event, a trade or transfer.","No hay encuentro salvaje registrado. Este Pokémon puede requerir evolución, un regalo, un evento, un intercambio o una transferencia."),32,520,410,20,29,ink,5);text(c,tr("Dataset coverage is incomplete for gifts.","La cobertura de regalos del conjunto de datos está incompleta."),32,708,15,muted);', 1),
    ('wrapText(c,area.optString("area"),32,y,412,17,22,ink,2);', 'wrapText(c,dstr(area,"area"),32,y,412,17,22,ink,2);', 1),
    ('text(c,area.optString("game")+" · Lv "+area.optInt("min")+"–"+area.optInt("max")+" · "+area.optString("chance")+"% slot",32,y+43,14,accent);',
     'text(c,area.optString("game")+" · "+tr("Lv ","Nv ")+area.optInt("min")+"–"+area.optInt("max")+" · "+area.optString("chance")+"%"+tr(" slot"," ranura"),32,y+43,14,accent);', 1),
    ('String cond=join(area.optJSONArray("conditions")==null?new JSONArray():area.optJSONArray("conditions"));text(c,fit(area.optString("method")+(cond.isEmpty()?"":" · "+cond),13,410),32,y+61,13,muted);',
     'String method=es&&!area.optString("method_es").isEmpty()?area.optString("method_es"):area.optString("method");String cond=join(dstrs(area,"conditions"));text(c,fit(method+(cond.isEmpty()?"":" · "+cond),13,410),32,y+61,13,muted);', 1),
    # Evolution
    ('text(c,"EVOLUTION FAMILY / GEN V",32,474,14,accent);', 'text(c,tr("EVOLUTION FAMILY / GEN V","FAMILIA EVOLUTIVA / GEN V"),32,474,14,accent);', 1),
    ('text(c,e.optString("name"),89,y,19,ink);', 'text(c,dstr(e,"name"),89,y,19,ink);', 1),
    ('JSONArray conditions=e.optJSONArray("conditions");String condition=conditions==null||conditions.length()==0?"Base stage":join(conditions);',
     'JSONArray conditions=dstrs(e,"conditions");String condition=conditions.length()==0?tr("Base stage","Etapa base"):join(conditions);', 1),
    ('if(e.optInt("from")>0){for(Entry from:all)if(from.id==e.optInt("from")){condition="From "+from.name+": "+condition;break;}}',
     'if(e.optInt("from")>0){for(Entry from:all)if(from.id==e.optInt("from")){condition=tr("From ","Desde ")+nm(from)+": "+condition;break;}}', 1),
    ('text(c,"3 cycles alternate forms on this entry.",32,721,14,muted);',
     'text(c,tr("3 cycles alternate forms on this entry.","3 cambia formas alternativas en esta ficha."),32,721,14,muted);', 1),
    # Options
    ('subhead(c,"JOURNAL OPTIONS","◀ ▶ change");String[] values={national?"National · 649":"Unova · B2W2",collection==0?"All Pokémon":collection==1?"Favorites":"Caught",typeOptions[typeFilter],sort==0?"Pokédex number":"A → Z",theme==0?"Diamond":theme==1?"Platinum":"White",animate?"On":"Off",whiteText?"White 2":"Black 2","Reset","Read","Return","Open"};',
     'subhead(c,tr("JOURNAL OPTIONS","OPCIONES DEL DIARIO"),tr("◀ ▶ change","◀ ▶ cambiar"));String[] values={national?tr("National · 649","Nacional · 649"):"Unova · B2W2",collection==0?tr("All Pokémon","Todos"):collection==1?tr("Favorites","Favoritos"):tr("Caught","Capturados"),tOpt(typeFilter),sort==0?tr("Pokédex number","Nº Pokédex"):"A → Z",theme==0?tr("Diamond","Diamante"):theme==1?tr("Platinum","Platino"):tr("White","Blanco"),animate?tr("On","Sí"):tr("Off","No"),whiteText?tr("White 2","Blanco 2"):tr("Black 2","Negro 2"),tr("Reset","Borrar"),tr("Read","Leer"),tr("Return","Volver"),tr("Open","Abrir")};', 1),
    ('String[] labels={"Pokédex","Collection","Type filter","Order","Shell theme","Animations","Entry text","Clear filters","Keys & credits","Back to journal","Identify (AI)"};',
     'String[] labels=es?new String[]{"Pokédex","Colección","Filtro de tipo","Orden","Tema de carcasa","Animaciones","Texto de ficha","Borrar filtros","Teclas y créditos","Volver al diario","Identificar (IA)"}:new String[]{"Pokédex","Collection","Type filter","Order","Shell theme","Animations","Entry text","Clear filters","Keys & credits","Back to journal","Identify (AI)"};', 1),
    # Help
    ('subhead(c,"TRAINER\'S GUIDE","Clear: return");', 'subhead(c,tr("TRAINER\'S GUIDE","GUÍA DEL ENTRENADOR"),tr("Clear: return","Clear: volver"));', 1),
    ('String[] lines={"D-pad moves;', 'String[] lines=es?helpEs():new String[]{"D-pad moves;', 1),
    # Footer and titles
    ('String left=screen==0?"Search":screen==3?"Erase":"Back";String right=screen==0?"Options":screen==1?"Shiny":screen==3?"T9 / No.":"Change";',
     'String left=screen==0?tr("Search","Buscar"):screen==3?tr("Erase","Borrar"):tr("Back","Atrás");String right=screen==0?tr("Options","Opciones"):screen==1?tr("Shiny","Brillo"):screen==3?tr("T9 / No.","T9 / Nº"):tr("Change","Cambiar");', 1),
    ('if(screen==4||screen==5){left="Back";right="Back";}', 'if(screen==4||screen==5){left=tr("Back","Atrás");right=left;}', 1),
    ('center(c,screen==1?(tab==2?"MOVE":tab==0?"TEXT":"TOP"):screen==4||screen==5?"BACK":"OK",240,833,16,accent);',
     'center(c,screen==1?(tab==2?tr("MOVE","MOVER"):tab==0?tr("TEXT","TEXTO"):tr("TOP","INICIO")):screen==4||screen==5?tr("BACK","ATRÁS"):"OK",240,833,16,accent);', 1),
    ('text(c,"FIELD JOURNAL / B2·W2",270,59,13,0xfff5dce0);', 'text(c,tr("FIELD JOURNAL / B2·W2","DIARIO DE CAMPO / B2·W2"),270,59,13,0xfff5dce0);', 1),
    ('center(c,error.isEmpty()?status:"Data unavailable",240,365,23,ink);',
     'center(c,error.isEmpty()?status:tr("Data unavailable","Datos no disponibles"),240,365,23,ink);', 1),
    # Accessibility description, read by TalkBack
    ('''String desc="Flip Pokédex. "+mode+". "+(e==null?"No matching Pokémon":e.name+", number "+(national?e.national:e.unova)+", "+e.types.toString())+". "+(national?"National":"Unova")+". "+filtered.size()+" results. Page "+(page+1)+". Type filter "+typeOptions[typeFilter]+". Collection "+collection+". Theme "+theme+". "+(animate?"Animation on.":"Animation off.")+(shiny?" Shiny.":" Normal sprite.")+(rear?" Back sprite.":" Front sprite.")+(e!=null&&caught.contains(""+e.species)?" Caught.":"")+(e!=null&&favorites.contains(""+e.species)?" Favorite.":"")+" Up/down choose or scroll. Left/right page or tabs. OK opens. Clear returns. 0 searches. Star opens options.";''',
     '''String desc="Flip Pokédex. "+mode+". "+(e==null?tr("No matching Pokémon","Ningún Pokémon coincide"):nm(e)+tr(", number ",", número ")+(national?e.national:e.unova)+", "+e.types.toString())+". "+(national?tr("National","Nacional"):"Unova")+". "+filtered.size()+tr(" results. Page "," resultados. Página ")+(page+1)+tr(". Type filter ",". Filtro de tipo ")+tOpt(typeFilter)+tr(". Collection ",". Colección ")+collection+tr(". Theme ",". Tema ")+theme+". "+(animate?tr("Animation on.","Animación activada."):tr("Animation off.","Animación desactivada."))+(shiny?tr(" Shiny."," Brillante."):tr(" Normal sprite."," Sprite normal."))+(rear?tr(" Back sprite."," Sprite de espalda."):tr(" Front sprite."," Sprite de frente."))+(e!=null&&caught.contains(""+e.species)?tr(" Caught."," Capturado."):"")+(e!=null&&favorites.contains(""+e.species)?tr(" Favorite."," Favorito."):"")+tr(" Up/down choose or scroll. Left/right page or tabs. OK opens. Clear returns. 0 searches. Star opens options."," Arriba/abajo elige o desplaza. Izq/der página o pestañas. OK abre. Clear vuelve. 0 busca. Asterisco abre opciones.");''', 1),
    # Filter in list: list stores English identifiers; only labels changed above.
]

IDENTIFY = [
    ('    private float centerX=.5f,centerY=.5f,cropSize=1;',
     '    private float centerX=.5f,centerY=.5f,cropSize=1;\n    private final boolean es=DexLogic.spanish(java.util.Locale.getDefault().getLanguage());\n    private String tr(String en,String spanish){return es?spanish:en;}', 1),
    ('showCrop("Scan cancelled. Press OK to try again.");', 'showCrop(tr("Scan cancelled. Press OK to try again.","Análisis cancelado. Pulsa OK para intentarlo de nuevo."));', 1),
    ('layout("IDENTIFY","F1 / Clear  Back       OK  Select\\n1  Camera       2  Choose image");',
     'layout(tr("IDENTIFY","IDENTIFICAR"),tr("F1 / Clear  Back       OK  Select\\n1  Camera       2  Choose image","F1 / Clear  Atrás       OK  Elegir\\n1  Cámara       2  Elegir imagen"));', 1),
    ('note("Find one Pokémon in a photo or artwork. Identification runs offline.");',
     'note(tr("Find one Pokémon in a photo or artwork. Identification runs offline.","Busca un Pokémon en una foto o ilustración. La identificación funciona sin conexión."));', 1),
    ('Button camera=button("1  Take photo",this::camera);button("2  Choose image",this::choose);',
     'Button camera=button(tr("1  Take photo","1  Hacer foto"),this::camera);button(tr("2  Choose image","2  Elegir imagen"),this::choose);', 1),
    ('note("Experimental • 649 species\\nResults are suggestions. Crop one Pokémon clearly and confirm the match yourself.");',
     'note(tr("Experimental • 649 species\\nResults are suggestions. Crop one Pokémon clearly and confirm the match yourself.","Experimental • 649 especies\\nLos resultados son sugerencias. Recorta un Pokémon con claridad y confirma tú la coincidencia."));', 1),
    ('note("Photos stay on this device. This feature does not change caught or favorite marks.");root.setContentDescription("Identify. SOURCE. Experimental 649-species offline classifier.");',
     'note(tr("Photos stay on this device. This feature does not change caught or favorite marks.","Las fotos se quedan en este dispositivo. Esta función no cambia las marcas de capturados ni favoritos."));root.setContentDescription(tr("Identify. SOURCE. Experimental 649-species offline classifier.","Identificar. ORIGEN. Clasificador experimental sin conexión de 649 especies."));', 1),
    ('message("Camera unavailable","Choose an existing image instead.");',
     'message(tr("Camera unavailable","Cámara no disponible"),tr("Choose an existing image instead.","Elige una imagen existente en su lugar."));', 1),
    ('message("Image picker unavailable","No document picker is installed on this device.");',
     'message(tr("Image picker unavailable","Selector de imágenes no disponible"),tr("No document picker is installed on this device.","No hay ningún selector de documentos instalado en este dispositivo."));', 1),
    ('private void message(String title,String text){state=RESULTS;layout(title,"F1 / Clear  Back       OK  Retry");note(text);Button b=button("Try another image",this::showSource);root.setContentDescription("Identify. ERROR. "+text);b.requestFocus();}',
     'private void message(String title,String text){state=RESULTS;layout(title,tr("F1 / Clear  Back       OK  Retry","F1 / Clear  Atrás       OK  Reintentar"));note(text);Button b=button(tr("Try another image","Probar otra imagen"),this::showSource);root.setContentDescription(tr("Identify. ERROR. ","Identificar. ERROR. ")+text);b.requestFocus();}', 1),
    ('layout("LOADING IMAGE","Clear  Cancel");note("Preparing image…");root.setContentDescription("Identify. LOADING.");',
     'layout(tr("LOADING IMAGE","CARGANDO IMAGEN"),tr("Clear  Cancel","Clear  Cancelar"));note(tr("Preparing image…","Preparando imagen…"));root.setContentDescription(tr("Identify. LOADING.","Identificar. CARGANDO."));', 1),
    ('throw new IOException("Image cannot be read");', 'throw new IOException(tr("Image cannot be read","No se puede leer la imagen"));', 1),
    ('throw new IOException("Cancelled");', 'throw new IOException(tr("Cancelled","Cancelado"));', 1),
    ('throw new IOException("Image file exceeds 32 MB");', 'throw new IOException(tr("Image file exceeds 32 MB","El archivo de imagen supera los 32 MB"));', 1),
    ('throw new IOException("Cannot prepare private image copy");', 'throw new IOException(tr("Cannot prepare private image copy","No se puede preparar la copia privada de la imagen"));', 1),
    ('throw new IOException("Unsupported image dimensions");', 'throw new IOException(tr("Unsupported image dimensions","Dimensiones de imagen no compatibles"));', 1),
    ('throw new IOException("Image decoder could not read this file");', 'throw new IOException(tr("Image decoder could not read this file","El decodificador no pudo leer este archivo"));', 1),
    ('failure=e instanceof OutOfMemoryError?"Not enough memory for this image.":e.getMessage();',
     'failure=e instanceof OutOfMemoryError?tr("Not enough memory for this image.","No hay memoria suficiente para esta imagen."):e.getMessage();', 1),
    ('message("Image unavailable",error==null?"Try a smaller JPEG or PNG.":error);',
     'message(tr("Image unavailable","Imagen no disponible"),error==null?tr("Try a smaller JPEG or PNG.","Prueba con un JPEG o PNG más pequeño."):error);', 1),
    ('showCrop("Frame one Pokémon, then press OK.")', 'showCrop(tr("Frame one Pokémon, then press OK.","Encuadra un Pokémon y pulsa OK."))', 2),
    ('layout("FRAME POKÉMON","D-pad  Move crop       2 / 8  Zoom\\n5  Reset       OK  Analyze       Clear  Back");',
     'layout(tr("FRAME POKÉMON","ENCUADRAR POKÉMON"),tr("D-pad  Move crop       2 / 8  Zoom\\n5  Reset       OK  Analyze       Clear  Back","D-pad  Mover recorte       2 / 8  Zoom\\n5  Reiniciar       OK  Analizar       Clear  Atrás"));', 1),
    ('note("2 zooms in • 8 zooms out • 5 resets");button("OK  Analyze image",this::analyze);',
     'note(tr("2 zooms in • 8 zooms out • 5 resets","2 acerca • 8 aleja • 5 reinicia"));button(tr("OK  Analyze image","OK  Analizar imagen"),this::analyze);', 1),
    ('state=BUSY;layout("IDENTIFYING","Clear  Cancel       Photos stay on device");note("Looking for possible matches…");',
     'state=BUSY;layout(tr("IDENTIFYING","IDENTIFICANDO"),tr("Clear  Cancel       Photos stay on device","Clear  Cancelar       Las fotos se quedan en el dispositivo"));note(tr("Looking for possible matches…","Buscando posibles coincidencias…"));', 1),
    ('note("Experimental recognition. No result is selected automatically.");root.setContentDescription("Identify. CHECKING.");',
     'note(tr("Experimental recognition. No result is selected automatically.","Reconocimiento experimental. Ningún resultado se elige automáticamente."));root.setContentDescription(tr("Identify. CHECKING.","Identificar. COMPROBANDO."));', 1),
    ('failure=e instanceof OutOfMemoryError?"Not enough memory. Try again after closing other apps.":"The offline model could not run on this device.";',
     'failure=e instanceof OutOfMemoryError?tr("Not enough memory. Try again after closing other apps.","No hay memoria suficiente. Vuelve a intentarlo tras cerrar otras apps."):tr("The offline model could not run on this device.","El modelo sin conexión no puede ejecutarse en este dispositivo.");', 1),
    ('state=RESULTS;layout("POSSIBLE MATCHES","D-pad  Choose       OK  Open entry\\nF1 / Clear  Crop       1  New image");',
     'state=RESULTS;layout(tr("POSSIBLE MATCHES","POSIBLES COINCIDENCIAS"),tr("D-pad  Choose       OK  Open entry\\nF1 / Clear  Crop       1  New image","D-pad  Elegir       OK  Abrir ficha\\nF1 / Clear  Recortar       1  Nueva imagen"));', 1),
    ('note(result.unknown?"Cannot identify this image. Try a clearer crop or another photo.":result.confident?"Likely matches — please confirm.":"Uncertain — compare these suggestions.");',
     'note(result.unknown?tr("Cannot identify this image. Try a clearer crop or another photo.","No se puede identificar esta imagen. Prueba con un recorte más claro u otra foto."):result.confident?tr("Likely matches — please confirm.","Coincidencias probables: confírmalo tú."):tr("Uncertain — compare these suggestions.","Incierto: compara estas sugerencias."));', 1),
    ('String.format(java.util.Locale.ROOT,"No. %03d  %s",match.id,match.name)',
     'String.format(java.util.Locale.ROOT,tr("No. %03d  %s","Nº %03d  %s"),match.id,match.name)', 1),
    ('Button retry=button("Adjust crop and retry",()->showCrop(', 'Button retry=button(tr("Adjust crop and retry","Ajustar recorte y reintentar"),()->showCrop(', 1),
    ('button("1  Choose another image",this::showSource);', 'button(tr("1  Choose another image","1  Elegir otra imagen"),this::showSource);', 1),
    ('note("Experimental • results can be wrong.\\nInference: "+result.milliseconds+" ms on this device.");',
     'note(tr("Experimental • results can be wrong.\\nInference: ","Experimental • los resultados pueden fallar.\\nInferencia: ")+result.milliseconds+tr(" ms on this device."," ms en este dispositivo."));', 1),
    ('root.setContentDescription("Identify. RESULTS. "+(result.unknown?"Cannot identify.":result.confident?"Likely matches.":"Uncertain suggestions.")+" Inference "+result.milliseconds+" ms.");',
     'root.setContentDescription(tr("Identify. RESULTS. ","Identificar. RESULTADOS. ")+(result.unknown?tr("Cannot identify.","No se puede identificar."):result.confident?tr("Likely matches.","Coincidencias probables."):tr("Uncertain suggestions.","Sugerencias inciertas."))+tr(" Inference "," Inferencia ")+result.milliseconds+" ms.");', 1),
    ('showCrop("Adjust the crop or press Clear for a new image.");', 'showCrop(tr("Adjust the crop or press Clear for a new image.","Ajusta el recorte o pulsa Clear para una imagen nueva."));', 1),
    ('"Identify. CROP. Center %.2f %.2f. Size %.2f."', 'tr("Identify. CROP. Center %.2f %.2f. Size %.2f.","Identificar. RECORTE. Centro %.2f %.2f. Tamaño %.2f.")', 1),
]

# Coordinator edits to the list screen (F2 opens identify; list corner label reads Scan).
COORDINATOR = [
    ('else if(k==KeyEvent.KEYCODE_F2||k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_MENU){screen=2;menu=0;}',
     'else if(k==KeyEvent.KEYCODE_F2){identify();}\n                else if(k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_MENU){screen=2;menu=0;}', 1),
    ('String right=screen==0?tr("Options","Opciones")', 'String right=screen==0?tr("Scan","Escanear")', 1),
]


def apply(path, pairs):
    text = path.read_text(encoding='utf-8')
    changed = 0
    for old, new, count in pairs:
        if new in text:
            continue  # already applied; new text never occurs in an unpatched file
        found = text.count(old)
        if found != count:
            raise SystemExit(f'{path.name}: expected {count} match(es), found {found}: {old[:90]!r}')
        text = text.replace(old, new)
        changed += 1
    path.write_text(text, encoding='utf-8')
    print(f'{path.name}: {changed} replacement group(s) applied')


if __name__ == '__main__':
    apply(SRC / 'DexLogic.java', DEXLOGIC)
    apply(SRC / 'PokedexActivity.java', POKEDEX)
    apply(SRC / 'PokedexActivity.java', COORDINATOR)
    apply(SRC / 'IdentifyActivity.java', IDENTIFY)
