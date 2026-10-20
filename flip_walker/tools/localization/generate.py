#!/usr/bin/env python3
"""Generate es-ES UI/catalogs from reviewed UI text and pinned PokeAPI CSVs."""
from pathlib import Path
import csv,json,re,hashlib
r=Path(__file__).resolve().parents[2];out=r/'templates/src/org/kyf37/walker';ref=r/'references/pokeapi-localization'
for file,digest in json.loads((ref/'provenance.json').read_text())['files'].items():
 if hashlib.sha256((ref/file).read_bytes()).hexdigest()!=digest:raise ValueError('Pinned localization data changed: '+file)
def rows(n):return list(csv.DictReader((ref/n).open()))
def names(file,idkey):return {int(x[idkey]):x['name'] for x in rows(file) if x['local_language_id']=='7'}
ui=json.loads((r/'tools/localization/es-ES.json').read_text())
for k,v in list(ui.items()):ui.setdefault(k.upper(),v)
source=(out/'WalkerCatalog.java').read_text();original={}
for key in ['ITEM','MOVE','ABILITY','POKE']:
 original[key]=json.loads('['+re.search(r'String\[\] '+key+r'=\{(.*?)\};',source,re.S).group(1)+']')
items=names('item_names.csv','item_id');indices={int(x['game_index']):int(x['item_id']) for x in rows('item_game_indices.csv') if x['generation_id']=='4'}
translated={}
for key,file,idkey in [('ITEM','item_names.csv','item_id'),('MOVE','move_names.csv','move_id'),('ABILITY','ability_names.csv','ability_id')]:
 mapping=names(file,idkey);values=[]
 for i,name in enumerate(original[key]):
  target=indices.get(i,-1) if key=='ITEM' else i
  value='Ninguno' if i==0 else mapping.get(target)
  if value is None:
   if key=='ITEM' and name.startswith('GlitchItm'):value='Objeto reservado '+str(i)
   else:raise ValueError((key,i,name))
  values.append(value)
 translated[key]=values
s='''package org.kyf37.walker;
import java.util.*;
import java.util.regex.*;
/** es-ES (Spain), alongside English. Catalogs: pinned PokeAPI, BSD-3-Clause. */
final class UiText {
 static volatile boolean spanish;
 private static final Map<String,String> CACHE=new LinkedHashMap<String,String>(64,.75f,true){protected boolean removeEldestEntry(Map.Entry<String,String> e){return size()>512;}};
 static String defaultLanguage(String locale){return locale.toLowerCase(Locale.ROOT).startsWith("es")?"es-ES":"en";}
 static synchronized void choose(String language){if(!language.equals("en")&&!language.equals("es-ES"))throw new IllegalArgumentException("Unsupported language");spanish=language.equals("es-ES");CACHE.clear();}
 static String language(){return spanish?"es-ES":"en";}
 private static final Map<String,String> UI=new HashMap<>(),NAMES=new HashMap<>();
'''
for key,values in translated.items():s+='private static final String[] ES_'+key+'='+json.dumps(values,ensure_ascii=False).replace('[','{',1)[:-1]+'};\n'
s+='static {\n'
for key,value in ui.items():s+='UI.put('+json.dumps(key,ensure_ascii=False)+','+json.dumps(value,ensure_ascii=False)+');\n'
s+='for(int i=0;i<ES_ITEM.length;i++)NAMES.put(WalkerCatalog.ITEM[i],ES_ITEM[i]);\nfor(int i=0;i<ES_MOVE.length;i++)NAMES.put(WalkerCatalog.MOVE[i],ES_MOVE[i]);\nfor(int i=0;i<ES_ABILITY.length;i++)NAMES.put(WalkerCatalog.ABILITY[i],ES_ABILITY[i]);\n}\n'
s+='''static String catalog(String[] catalog,int index){if(!spanish)return catalog[index];if(index==0)return "Ninguno";return catalog==WalkerCatalog.ITEM?ES_ITEM[index]:catalog==WalkerCatalog.MOVE?ES_MOVE[index]:catalog==WalkerCatalog.ABILITY?ES_ABILITY[index]:catalog[index];}
 static synchronized String tr(String text){
  if(!spanish||text==null||text.isEmpty())return text;
  String cached=CACHE.get(text);if(cached!=null)return cached;
  String translated=translate(text);CACHE.put(text,translated);return translated;
 }
 private static String translate(String text){
  if(!spanish||text==null||text.isEmpty())return text;
  String exact=UI.get(text);if(exact!=null)return exact;
  Matcher m;
  // Structured placeholders: trainer names are never translated as UI words.
  m=Pattern.compile("^(Trainer|Trainer ID|Secret ID|Steps today|Paired|Has Pokemon|Last sync \\(raw\\)|Today|Watts|Pokemon|Held item|Move [1-4]|Level|Gender|Shiny|Ability|Item|Watts to add|Today steps \\(0=keep\\)|Max total steps): (.*)$").matcher(text);
  if(m.matches()){
   String key=m.group(1),value=m.group(2),label=UI.get(key);
   if(label==null)label=key.equals("Trainer")?"Entrenador":key.equals("Trainer ID")?"ID entrenador":key.equals("Secret ID")?"ID secreto":key.equals("Steps today")?"Pasos hoy":key.equals("Paired")?"Vinculado":key.equals("Has Pokemon")?"Tiene Pokémon":key.startsWith("Last sync")?"Última conexión (valor)":key.equals("Today")?"Hoy":key.equals("Watts")?"Vatios":key;
   if(!key.equals("Trainer"))value=value.equals("true")?"Sí":value.equals("false")?"No":tr(value);
   return label+": "+value;
  }
  m=Pattern.compile("^(ID [0-9]+ · .* · )([0-9]+) steps$").matcher(text);if(m.matches())return m.group(1)+m.group(2)+" pasos";
  m=Pattern.compile("^([0-9]+) steps     ([0-9]+) W$").matcher(text);if(m.matches())return m.group(1)+" pasos     "+m.group(2)+" W";
  m=Pattern.compile("^([0-9]+) (steps|watts|WATTS|chances left|/ 3 items)$").matcher(text);if(m.matches())return m.group(1)+" "+(m.group(2).equals("steps")?"pasos":m.group(2).equals("WATTS")?"VATIOS":m.group(2).equals("watts")?"vatios":m.group(2).equals("chances left")?"intentos restantes":"/ 3 objetos");
  m=Pattern.compile("^Wild Pokémon #([0-9]+) appeared!$").matcher(text);if(m.matches())return "¡Ha aparecido un Pokémon salvaje #"+m.group(1)+"!";
  m=Pattern.compile("^Wild Pokémon #([0-9]+) · HP ([0-9]+) / 4$").matcher(text);if(m.matches())return "Pokémon salvaje #"+m.group(1)+" · PS "+m.group(2)+" / 4";
  m=Pattern.compile("^(Found item|Caught Pokémon) #([0-9]+)!$").matcher(text);if(m.matches())return (m.group(1).equals("Found item")?"¡Objeto encontrado #":"¡Pokémon capturado #")+m.group(2)+"!";
  m=Pattern.compile("^(Reading device backup: |Reading ROM: |Saving backup first: )([0-9]+)% · F2 (cancels|stops)$").matcher(text);if(m.matches())return (m.group(1).startsWith("Reading ROM")?"Leyendo ROM: ":m.group(1).startsWith("Saving")?"Guardando copia previa: ":"Leyendo copia: ")+m.group(2)+"% · F2 para parar";
  m=Pattern.compile("^ENTER VALUE / ID: (.*) · OK DONE$").matcher(text);if(m.matches())return "VALOR / ID: "+m.group(1)+" · OK TERMINAR";
  m=Pattern.compile("^([0-9]+ / [0-9]+)  < > CHANGE · DIGITS: ID$").matcher(text);if(m.matches())return m.group(1)+"  < > CAMBIAR · NÚMEROS: ID";
  for(String suffix:new String[]{". Changes may be partial; pre-change backup retained.",". Earlier captures preserved."})if(text.endsWith(suffix))return tr(text.substring(0,text.length()-suffix.length()))+UI.get(suffix);
  for(String prefix:new String[]{"Could not save: ","Simulator error: "})if(text.startsWith(prefix))return (prefix.startsWith("Could")?"No se pudo guardar: ":"Error de simulación: ")+tr(text.substring(prefix.length()));
  m=Pattern.compile("^([0-9]+) (.*)$").matcher(text);if(m.matches())return m.group(1)+" "+tr(m.group(2));
  String name=NAMES.get(text);return name==null?text:name;
 }
}
'''
# Java string literal escaping for regex backslashes.
s=s.replace('\\(', '\\\\(').replace('\\)', '\\\\)')
(out/'UiText.java').write_text(s)
(r/'tools/localization/catalog-coverage.json').write_text(json.dumps({'locale':'es-ES','pokeapi_language_id':7,'iso3166':'es','counts':{k:len(v) for k,v in translated.items()},'ui_keys':len(ui),'generation':4},indent=2))
print('es-ES UI and generation-four catalogs generated')
