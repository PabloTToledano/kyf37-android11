package org.kyf37.pokedex;

import android.app.Activity;
import android.os.*;
import android.content.*;
import android.graphics.*;
import android.view.*;
import android.util.LruCache;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

/** Offline, dependency-free Pokédex for the KYF37's D-pad and four corner keys. */
public final class PokedexActivity extends Activity {
    private DexView view;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        view = new DexView(this); setContentView(view); view.requestFocus();
        loadSounds();
        if (state != null) view.restoreId = state.getInt("selected", 494);
    }
    @Override public void onSaveInstanceState(Bundle b) { super.onSaveInstanceState(b); b.putInt("selected", view.selectedId()); }
    @Override public void onResume() { super.onResume(); if(view != null) view.running(true); }
    @Override public void onPause() { if(view != null) view.running(false); super.onPause(); }
    @Override public void onDestroy() { if(view != null) view.close(); if (sounds != null) sounds.release(); super.onDestroy(); }
    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if (view != null) { // interface sounds follow what the key changed
            int sc = view.screen, tb = view.tab, sel = view.selection;
            boolean used = view.key(event);
            if (used && event.getAction() == KeyEvent.ACTION_DOWN) {
                if (view.screen == 1 && sc != 1) ui(R.raw.ui_decision);
                else if (view.screen == 2 && sc != 2) ui(R.raw.ui_menu_open);
                else if (sc == 2 && view.screen != 2) ui(R.raw.ui_menu_close);
                else if (view.screen < sc || (sc != 0 && view.screen == 0)) ui(R.raw.ui_cancel);
                else if (view.tab != tb) ui(R.raw.ui_page);
                else if (view.selection != sel) ui(R.raw.ui_cursor);
            }
            if (used) return true;
        }
        return super.dispatchKeyEvent(event);
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request==70&&result==RESULT_OK&&data!=null){int id=data.getIntExtra("national",0);if(id>=1&&id<=649&&view!=null){view.national=true;view.query="";view.collection=0;view.typeFilter=0;view.rebuild(id);view.screen=1;view.tab=0;view.save();view.invalidate();}}
    }
    @Override public void onBackPressed() { if (view != null && view.screen != 0) view.back(); else super.onBackPressed(); }

    private static final class Entry {
        int id, species, unova, national; String name, nameEs, form, sprite; JSONArray types;
        Entry(JSONObject o) throws JSONException {
            id=o.getInt("id"); species=o.getInt("species"); unova=o.getInt("unova"); national=o.getInt("national");
            name=o.getString("name"); nameEs=o.optString("name_es",""); form=o.getString("form"); sprite=o.optString("sprite", ""+id); types=o.getJSONArray("types");
        }
    }
    private static String read(InputStream in) throws IOException {
        try(InputStream stream=in; ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] b=new byte[8192]; int n; while((n=stream.read(b))!=-1) out.write(b,0,n); return out.toString("UTF-8");
        }
    }
    private static final class Media {
        Movie movie; Bitmap bitmap;
    }
    private android.media.SoundPool sounds;
    private final java.util.HashMap<Integer, Integer> soundIds = new java.util.HashMap<>();
    private void ui(int res) {
        if (sounds == null) return;
        Integer id = soundIds.get(res);
        if (id != null) sounds.play(id, 0.55f, 0.55f, 1, 0, 1f);
    }
    private void loadSounds() {
        sounds = new android.media.SoundPool.Builder().setMaxStreams(2).setAudioAttributes(new android.media.AudioAttributes.Builder()
                .setUsage(android.media.AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION).build()).build();
        for (int r : new int[] {R.raw.ui_cursor, R.raw.ui_decision, R.raw.ui_cancel, R.raw.ui_open, R.raw.ui_menu_open,
                R.raw.ui_menu_close, R.raw.ui_page, R.raw.ui_buzzer}) soundIds.put(r, sounds.load(this, r, 1));
        sounds.setOnLoadCompleteListener((sp, id, st) -> { if (soundIds.get(R.raw.ui_open) != null && id == soundIds.get(R.raw.ui_open)) sp.play(id, 0.6f, 0.6f, 1, 0, 1f); });
    }

    private static final class DexView extends View {
        final Activity activity; final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG); final Handler ui=new Handler(Looper.getMainLooper());
        final ExecutorService worker=Executors.newSingleThreadExecutor(); final android.content.SharedPreferences prefs;
        final ArrayList<Entry> all=new ArrayList<>(), filtered=new ArrayList<>();
        final Set<String> caught=new HashSet<>(), favorites=new HashSet<>();
        final LruCache<Integer,Bitmap> icons=new LruCache<Integer,Bitmap>(2*1024*1024) {
            @Override protected int sizeOf(Integer key, Bitmap value) { return value.getByteCount(); }
        };
        final Set<Integer> pendingIcons=new HashSet<>(), absentIcons=new HashSet<>();
        final String[] tabs; final boolean es; final HashMap<String,String> typesEs=new HashMap<>();
        final String[] typeOptions={"All types","Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark","Fairy"};
        int areaGame=11; JSONArray encounterGames=new JSONArray();
        int screen=0, selection=0, tab=0, page=0, menu=0, theme=0, typeFilter=0, collection=0, sort=0, restoreId=494;
        boolean national=false, shiny=false, rear=false, female=false, animate=true, active=false, loaded=false, destroyed=false, searchName=false, whiteText=false;
        String query="", status="", error="", toast=""; long toastUntil=0, changed=0;
        android.media.MediaPlayer player;
        JSONObject detail; int detailId=-1, mediaId=-1, generation=0, moveIndex=0; Media media; float scale=1, offsetX=0, offsetY=0;
        int ink=0xff263e43, muted=0xff657b7d, accent=0xffbf3844, paper=0xffeef3e7, panel=0xfffbfcf6;
        final Runnable frame=new Runnable(){public void run(){
            if(active && animate && loaded){
                boolean visible=screen!=2 && screen!=4 && screen!=5;
                if(visible)invalidate();
                // Keep the clock alive across modal pages; redraw only the animated screens.
                ui.postDelayed(this,visible?66:250);
            }
        }};
        final Runnable selectMedia=new Runnable(){public void run(){loadSelected();}};
        DexView(Activity a) {
            super(a); activity=a; setFocusable(true); setFocusableInTouchMode(true);
            es=DexLogic.spanish(Locale.getDefault().getLanguage());
            tabs=es?new String[]{"FICHA","STATS","MOVIM.","ZONA","EVOLUC."}:new String[]{"ENTRY","STATS","MOVES","AREA","EVOLVE"};
            status=tr("Loading offline records…","Cargando registros sin conexión…");
            if(es)loadTypesEs(a);
            prefs=a.getSharedPreferences("field-journal", Context.MODE_PRIVATE);
            caught.addAll(prefs.getStringSet("caught",Collections.<String>emptySet())); favorites.addAll(prefs.getStringSet("favorites",Collections.<String>emptySet()));
            national=prefs.getBoolean("national",false); theme=DexLogic.wrap(prefs.getInt("theme",0),3); animate=prefs.getBoolean("animate",true);
            areaGame=prefs.getInt("areaGame",11);restoreId=prefs.getInt("selected",494); whiteText=prefs.getBoolean("whiteText",false);
            worker.execute(()->{ try {
                final JSONArray gameChoices=new JSONArray(read(a.getAssets().open("data/encounter-games.json")));
                JSONArray array=new JSONArray(read(a.getAssets().open("data/index.json"))); final ArrayList<Entry> entries=new ArrayList<>();
                for(int i=0;i<array.length();i++) entries.add(new Entry(array.getJSONObject(i)));
                ui.post(()->{if(destroyed)return; all.addAll(entries); encounterGames=gameChoices; loaded=true; rebuild(restoreId); running(active);});
            } catch(Exception e){ui.post(()->{error=tr("Offline data could not be loaded. Reinstall the complete APK.","No se pudieron cargar los datos sin conexión. Reinstale el APK completo."); invalidate();});} });
        }
        void running(boolean value){active=value;if(!value){stopCry();if(loaded)save();} ui.removeCallbacks(frame); if(value){invalidate(); if(animate)ui.post(frame);}}
        void close(){stopCry();destroyed=true; active=false; ui.removeCallbacksAndMessages(null); worker.shutdownNow(); icons.evictAll(); media=null;}
        int selectedId(){Entry e=entry();return e==null?restoreId:e.id;}
        Entry entry(){return filtered.isEmpty()?null:filtered.get(DexLogic.clamp(selection,filtered.size()));}
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
                String other=detail.optString("fallbackText_es","");if(!other.isEmpty())return new String[]{other,""};
            }
            String en=detail.optString(key,"");if(!en.isEmpty())return new String[]{en,record};
            boolean later=detail.optInt("species")>649;return new String[]{detail.optString("fallbackText"),later?"":tr("EARLIER DEX RECORD","REGISTRO ANTERIOR")};
        }
        String[] helpEs(){return new String[]{"D-pad mueve; OK abre una ficha.","Izq/Der cambia pestañas o páginas.","0 busca por número; * busca por nombre T9.","T9: 2 ABC · 3 DEF · 4 GHI · 5 JKL","6 MNO · 7 PQRS · 8 TUV · 9 WXYZ","Clear/# borra; OK abre un resultado.","1 favorito · 5 capturado · 2/8 ant./sig.","Ficha: 3 forma · 7 espalda · 9 hembra","ZONA: 0 juego anterior; OK siguiente","6 reproduce el grito clásico","# variocolor · * opciones · Clear vuelve","","Registros: PokéAPI / Veekun / WikiDex","Sprites: PokeAPI/sprites (Gen V; Gen VI-IX static)","Pokémon © Nintendo / Creatures /","GAME FREAK. Proyecto de fans no oficial.","Sprites Gen V compartidos B/N;","las animaciones de B2W2 pueden variar.","9 en lista: identificar foto offline"};}
        void save(){prefs.edit().putStringSet("caught",new HashSet<>(caught)).putStringSet("favorites",new HashSet<>(favorites)).putBoolean("national",national).putInt("theme",theme).putBoolean("animate",animate).putBoolean("whiteText",whiteText).putInt("selected",selectedId()).putInt("areaGame",areaGame).apply();}
        void rebuild(int keep) {
            int keepSpecies=keep;for(Entry saved:all)if(saved.id==keep){keepSpecies=saved.species;break;}
            filtered.clear();
            for(Entry e:all){
                if(e.id!=e.species)continue;
                if(!national && e.unova<0)continue;
                if(collection==1 && !favorites.contains(""+e.species))continue;
                if(collection==2 && !caught.contains(""+e.species))continue;
                if(typeFilter>0 && !e.types.toString().contains("\""+typeOptions[typeFilter]+"\""))continue;
                if(!DexLogic.matches(nm(e),national?e.national:e.unova,query,searchName)&&!DexLogic.matches(e.name,national?e.national:e.unova,query,searchName))continue;
                filtered.add(e);
            }
            Collections.sort(filtered,(a,b)->sort==1?nm(a).compareTo(nm(b)):Integer.compare(national?a.national:a.unova,national?b.national:b.unova));
            selection=0;for(int i=0;i<filtered.size();i++)if(filtered.get(i).id==keepSpecies)selection=i;
            page=0;moveIndex=0; changed=SystemClock.uptimeMillis(); queueSelection(); invalidate();
        }
        void queueSelection(){stopCry();ui.removeCallbacks(selectMedia); generation++; detail=null; detailId=-1; media=null; mediaId=-1; ui.postDelayed(selectMedia,75); updateDescription();}
        void move(int delta){ if(filtered.isEmpty())return; selection=DexLogic.wrap(selection+delta,filtered.size()); page=0;moveIndex=0; changed=SystemClock.uptimeMillis(); queueSelection(); invalidate();}
        void loadSelected(){
            Entry e=entry();if(e==null || destroyed)return;final int id=e.id, request=generation; final String sprite=e.sprite;
            final boolean s=shiny, b=rear, f=female;
            worker.execute(()->{
                JSONObject d=null; Media m=new Media();
                try{d=new JSONObject(read(activity.getAssets().open("data/pokemon/"+id+".json")));}catch(Exception ignored){}
                String variant=(b?"back/":"")+(s?"shiny/":"")+(f?"female/":"");
                // A missing female variant falls back to the matching male/default variant.
                String fallback=(b?"back/":"")+(s?"shiny/":"");
                for(String v:new String[]{variant,fallback}){
                    try(InputStream in=activity.getAssets().open("sprites/animated/"+v+sprite+".gif")){m.movie=Movie.decodeStream(in);}catch(IOException ignored){}
                    if(m.movie!=null)break;
                }
                if(m.movie==null)for(String v:new String[]{variant,fallback}){
                    try(InputStream in=activity.getAssets().open("sprites/"+v+sprite+".png")){m.bitmap=BitmapFactory.decodeStream(in);}catch(IOException ignored){}
                    if(m.bitmap!=null)break;
                }
                final JSONObject data=d;
                ui.post(()->{if(destroyed || request!=generation)return; detail=data;detailId=id;media=m;mediaId=id;updateDescription();invalidate();});
            });
        }
        Bitmap icon(int id){
            Bitmap image=icons.get(id); if(image!=null||absentIcons.contains(id)||pendingIcons.contains(id)||destroyed)return image;
            pendingIcons.add(id);
            worker.execute(()->{
                String stem=""+id;for(Entry candidate:all)if(candidate.id==id){stem=candidate.sprite;break;}
                Bitmap bmp=null; try(InputStream in=activity.getAssets().open("sprites/"+stem+".png")){bmp=BitmapFactory.decodeStream(in);}catch(IOException ignored){}
                final Bitmap result=bmp; ui.post(()->{if(destroyed)return;pendingIcons.remove(id);if(result!=null)icons.put(id,result);else absentIcons.add(id);invalidate();});
            });return null;
        }
        void updateDescription(){
            Entry e=entry();String mode=screen==1?tabs[tab]:screen==2?"JOURNAL OPTIONS":screen==3?"SEARCH "+(searchName?"T9":"NUMBER")+" "+query:screen==4?"TRAINER GUIDE":screen==5?"MOVE RECORD":"LIST";
            String desc="Flip Pokédex. "+mode+". "+(e==null?tr("No matching Pokémon","Ningún Pokémon coincide"):nm(e)+tr(", number ",", número ")+(national?e.national:e.unova)+", "+e.types.toString())+". "+(national?tr("National","Nacional"):"Unova")+". "+filtered.size()+tr(" results. Page "," resultados. Página ")+(page+1)+tr(". Type filter ",". Filtro de tipo ")+tOpt(typeFilter)+tr(". Collection ",". Colección ")+collection+tr(". Theme ",". Tema ")+theme+". "+(animate?tr("Animation on.","Animación activada."):tr("Animation off.","Animación desactivada."))+(shiny?tr(" Shiny."," Variocolor."):tr(" Normal sprite."," Sprite normal."))+(rear?tr(" Back sprite."," Sprite de espalda."):tr(" Front sprite."," Sprite de frente."))+(e!=null&&caught.contains(""+e.species)?tr(" Caught."," Capturado."):"")+(e!=null&&favorites.contains(""+e.species)?tr(" Favorite."," Favorito."):"")+tr(" Up/down choose or scroll. Left/right page or tabs. OK opens. Clear returns. 0 searches. Star opens options."," Arriba/abajo elige o desplaza. Izq/der página o pestañas. OK abre. Clear vuelve. 0 busca. Asterisco abre opciones.");
            if(screen==1&&tab==3)desc=desc.replace(tr("0 searches.","0 busca."),tr("0 previous game.","0 juego anterior."))+" "+dstr(areaGameChoice(),"name")+tr(". 0 previous game, OK next game, up/down areas.",". 0 juego anterior, OK siguiente juego, arriba/abajo zonas.");
            if(!desc.contentEquals(getContentDescription()==null?"":getContentDescription()))setContentDescription(desc);
        }
        void stopCry(){if(player!=null){player.release();player=null;}}
        void cry(){
            Entry e=entry();if(e==null)return;stopCry();
            try(android.content.res.AssetFileDescriptor fd=activity.getAssets().openFd("cries/"+(e.id<200000?e.id:e.species)+".ogg")){
                android.media.MediaPlayer sound=new android.media.MediaPlayer();player=sound;
                sound.setAudioAttributes(new android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_GAME).setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION).build());
                sound.setDataSource(fd.getFileDescriptor(),fd.getStartOffset(),fd.getLength());
                sound.setOnPreparedListener(mp->{if(player==mp && active)mp.start();});
                sound.setOnCompletionListener(mp->{if(player==mp)stopCry();});
                sound.setOnErrorListener((mp,what,extra)->{if(player==mp)stopCry();notice(tr("Cry unavailable","Grito no disponible"));return true;});
                sound.prepareAsync();
            }catch(Exception err){stopCry();notice(tr("No legacy cry for this form","Esta forma no tiene grito clásico"));}
        }
        void notice(String text){toast=text;toastUntil=SystemClock.uptimeMillis()+1700;invalidate();ui.postDelayed(()->invalidate(),1800);}
        /** Evolution family plus this species' alternate forms (Rotom appliances, regional forms...). */
        JSONArray evoRows(){JSONArray rows=new JSONArray();JSONArray fam=array("evolution");for(int i=0;i<fam.length();i++)rows.put(fam.optJSONObject(i));
            Entry cur=entry();if(cur==null)return rows;
            for(Entry x:all)if(x.species==cur.species&&x.id!=cur.id){try{JSONObject o=new JSONObject();o.put("id",x.id);o.put("name",nm(x));o.put("name_es",nm(x));o.put("form",true);rows.put(o);}catch(JSONException ignored){}}
            return rows;}
        void openEvolution(){JSONObject e=evoRows().optJSONObject(moveIndex);if(e==null)return;int id=e.optInt("id");
            if(e.optBoolean("form")){for(Entry x:all)if(x.id==id){filtered.set(selection,x);queueSelection();tab=0;page=0;moveIndex=0;ui.postDelayed(this::cry,220);return;}}
            if(id<=0||id==selectedId())return;boolean found=false;for(Entry x:filtered)if(x.id==id){found=true;break;}
            if(!found){national=true;collection=0;typeFilter=0;query="";}
            rebuild(id);tab=0;page=0;moveIndex=0;changed=SystemClock.uptimeMillis();save();ui.postDelayed(this::cry,220);}
        void randomEntry(){if(filtered.isEmpty())return;selection=new java.util.Random().nextInt(filtered.size());page=0;moveIndex=0;changed=SystemClock.uptimeMillis();queueSelection();invalidate();}
        void toggle(Set<String> set,String label,String labelEs){Entry e=entry();if(e==null)return;String id=""+e.species;boolean add=!set.remove(id);if(add)set.add(id);save();notice((es?labelEs:label)+(add?tr(" added"," añadido"):tr(" removed"," quitado")));if(screen!=1 && collection!=0)rebuild(e.id);}
        void back(){
            if(screen==5){screen=1;invalidate();return;}
            if(screen==3 && !query.isEmpty()){query=query.substring(0,query.length()-1);rebuild(selectedId());return;}
            if(screen==0){activity.finish();return;}
            screen=0;query="";rebuild(selectedId());save();
        }
        boolean handled(int k){return k==KeyEvent.KEYCODE_BACK||k==KeyEvent.KEYCODE_DEL||k==KeyEvent.KEYCODE_ESCAPE||k==KeyEvent.KEYCODE_DPAD_UP||k==KeyEvent.KEYCODE_DPAD_DOWN||k==KeyEvent.KEYCODE_DPAD_LEFT||k==KeyEvent.KEYCODE_DPAD_RIGHT||k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER||k==KeyEvent.KEYCODE_NUMPAD_ENTER||(k>=KeyEvent.KEYCODE_0&&k<=KeyEvent.KEYCODE_9)||(k>=KeyEvent.KEYCODE_F1&&k<=KeyEvent.KEYCODE_F4)||k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_POUND||k==KeyEvent.KEYCODE_MENU;}
        boolean key(KeyEvent ev){
            int k=ev.getKeyCode();if(!handled(k))return false;
            if(ev.getAction()==KeyEvent.ACTION_UP)return true;
            if(ev.getAction()!=KeyEvent.ACTION_DOWN)return true;
            boolean direction=k>=KeyEvent.KEYCODE_DPAD_UP&&k<=KeyEvent.KEYCODE_DPAD_RIGHT;
            // A held corner key, OK, or digit must never toggle twice or open two screens.
            if(ev.getRepeatCount()>0 && !direction)return true;
            if(!loaded){if(k==KeyEvent.KEYCODE_BACK)activity.finish();return true;}
            if(k==KeyEvent.KEYCODE_BACK||k==KeyEvent.KEYCODE_DEL||k==KeyEvent.KEYCODE_ESCAPE){back();return true;}
            if(screen==5){
                if(k==KeyEvent.KEYCODE_DPAD_RIGHT||k==KeyEvent.KEYCODE_DPAD_DOWN){moveIndex=DexLogic.wrap(moveIndex+1,array("moves").length());page=moveIndex/4;}
                else if(k==KeyEvent.KEYCODE_DPAD_LEFT||k==KeyEvent.KEYCODE_DPAD_UP){moveIndex=DexLogic.wrap(moveIndex-1,array("moves").length());page=moveIndex/4;}
                else {screen=1;}invalidate();return true;
            }
            if(screen==4){screen=0;invalidate();return true;}
            if(screen==2){
                if(k==KeyEvent.KEYCODE_DPAD_UP)menu=DexLogic.wrap(menu-1,11);
                else if(k==KeyEvent.KEYCODE_DPAD_DOWN)menu=DexLogic.wrap(menu+1,11);
                else if(k==KeyEvent.KEYCODE_F1){back();return true;}
                else if(k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER||k==KeyEvent.KEYCODE_NUMPAD_ENTER||k==KeyEvent.KEYCODE_DPAD_RIGHT||k==KeyEvent.KEYCODE_F2)option(1);
                else if(k==KeyEvent.KEYCODE_DPAD_LEFT)option(-1);
                invalidate();return true;
            }
            if(screen==3){
                if(k>=KeyEvent.KEYCODE_0&&k<=KeyEvent.KEYCODE_9){if(query.length()<(searchName?12:4)){query+=(k-KeyEvent.KEYCODE_0);rebuild(selectedId());}}
                else if(k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_F2){searchName=!searchName;query="";rebuild(selectedId());}
                else if(k==KeyEvent.KEYCODE_POUND||k==KeyEvent.KEYCODE_F1)back();
                
                else if(k==KeyEvent.KEYCODE_DPAD_DOWN)move(1);
                else if(k==KeyEvent.KEYCODE_DPAD_UP)move(-1);
                else if(k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER||k==KeyEvent.KEYCODE_NUMPAD_ENTER){if(entry()!=null){screen=1;tab=0;page=0;moveIndex=0;save();ui.postDelayed(this::cry,160);}}
                invalidate();return true;
            }
            if(k==KeyEvent.KEYCODE_DPAD_CENTER||k==KeyEvent.KEYCODE_ENTER||k==KeyEvent.KEYCODE_NUMPAD_ENTER){
                if(entry()!=null){if(screen==0){screen=1;tab=0;page=0;moveIndex=0;save();ui.postDelayed(this::cry,160);}else if(tab==0){whiteText=!whiteText;save();}else if(tab==3){areaGame=DexLogic.wrap(areaGame+1,encounterGames.length());page=0;}else if(tab==4 && evoRows().length()>0){openEvolution();}else if(tab==2 && array("moves").length()>0){screen=5;}else{page=0;}}invalidate();return true;
            }
            if(screen==0){
                if(k==KeyEvent.KEYCODE_DPAD_UP)move(-1);
                else if(k==KeyEvent.KEYCODE_DPAD_DOWN)move(1);
                else if(k==KeyEvent.KEYCODE_DPAD_LEFT)move(-5);
                else if(k==KeyEvent.KEYCODE_DPAD_RIGHT)move(5);
                else if(k==KeyEvent.KEYCODE_F1||k==KeyEvent.KEYCODE_0){screen=3;query="";searchName=false;rebuild(selectedId());}
                else if(k==KeyEvent.KEYCODE_F2){identify();}
                else if(k==KeyEvent.KEYCODE_F3){screen=2;menu=0;}
                else if(k==KeyEvent.KEYCODE_F4){toggle(favorites,"Favorite","Favorito");}
                else if(k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_MENU){screen=2;menu=0;}
                else if(k==KeyEvent.KEYCODE_5)toggle(caught,"Caught","Capturado");
                else if(k==KeyEvent.KEYCODE_POUND){national=!national;rebuild(selectedId());save();}
                else if(k==KeyEvent.KEYCODE_1)toggle(favorites,"Favorite","Favorito");
                else if(k==KeyEvent.KEYCODE_9)identify();
                else if(k==KeyEvent.KEYCODE_2)move(-5);
                else if(k==KeyEvent.KEYCODE_8)move(5);
            }else{
                if(k==KeyEvent.KEYCODE_0&&tab==3){areaGame=DexLogic.wrap(areaGame-1,encounterGames.length());page=0;}
                else if(k==KeyEvent.KEYCODE_DPAD_LEFT){tab=DexLogic.wrap(tab-1,tabs.length);page=0;moveIndex=0;changed=SystemClock.uptimeMillis();}
                else if(k==KeyEvent.KEYCODE_F3){screen=2;menu=0;}
                else if(k==KeyEvent.KEYCODE_F4){toggle(favorites,"Favorite","Favorito");}
                else if(k==KeyEvent.KEYCODE_DPAD_RIGHT){tab=DexLogic.wrap(tab+1,tabs.length);page=0;moveIndex=0;changed=SystemClock.uptimeMillis();}
                else if(k==KeyEvent.KEYCODE_DPAD_UP){if(tab==2||tab==4){moveIndex=Math.max(0,moveIndex-1);page=moveIndex/4;}else page=Math.max(0,page-1);}
                else if(k==KeyEvent.KEYCODE_DPAD_DOWN){if(tab==2||tab==4){moveIndex=Math.min(Math.max(0,(tab==2?array("moves"):evoRows()).length()-1),moveIndex+1);page=moveIndex/4;}else page=Math.min(detailPages()-1,page+1);}
                else if(k==KeyEvent.KEYCODE_F1)back();
                else if(k==KeyEvent.KEYCODE_F2||k==KeyEvent.KEYCODE_POUND){shiny=!shiny;queueSelection();}
                else if(k==KeyEvent.KEYCODE_5)toggle(caught,"Caught","Capturado");
                else if(k==KeyEvent.KEYCODE_1)toggle(favorites,"Favorite","Favorito");
                else if(k==KeyEvent.KEYCODE_2)move(-1);
                else if(k==KeyEvent.KEYCODE_8)move(1);
                else if(k==KeyEvent.KEYCODE_3)cycleForm();
                else if(k==KeyEvent.KEYCODE_6)cry();
                else if(k==KeyEvent.KEYCODE_7){rear=!rear;queueSelection();}
                else if(k==KeyEvent.KEYCODE_9){female=!female;queueSelection();}
                else if(k==KeyEvent.KEYCODE_STAR||k==KeyEvent.KEYCODE_MENU){screen=2;menu=0;}
            }
            updateDescription();invalidate();return true;
        }
        void cycleForm(){
            Entry selected=entry();if(selected==null)return;ArrayList<Entry> variants=new ArrayList<>();
            for(Entry e:all)if(e.species==selected.species)variants.add(e);
            if(variants.size()<2){notice(tr("No alternate forms","Sin formas alternativas"));return;}
            int i=0;for(int n=0;n<variants.size();n++)if(variants.get(n).id==selected.id)i=n;
            filtered.set(selection,variants.get((i+1)%variants.size()));queueSelection();page=0;
        }
        void identify(){activity.startActivityForResult(new Intent(activity,IdentifyActivity.class),70);}
        void option(int dir){
            int id=selectedId();
            switch(menu){
                case 0:national=!national;break;
                case 1:collection=DexLogic.wrap(collection+dir,3);break;
                case 2:typeFilter=DexLogic.wrap(typeFilter+dir,typeOptions.length);break;
                case 3:sort=1-sort;break;
                case 4:theme=DexLogic.wrap(theme+dir,3);break;
                case 5:animate=!animate;running(active);break;
                case 6:whiteText=!whiteText;break;
                case 7:collection=0;typeFilter=0;query="";sort=0;break;
                case 8:screen=4;break;
                case 9:screen=0;break;
                case 10:identify();break;
            }
            rebuild(id);save();
        }
        JSONArray array(String key){return detail==null?new JSONArray():detail.optJSONArray(key)==null?new JSONArray():detail.optJSONArray(key);}
        int detailPages(){if(tab==0)return 3;if(tab==1)return 2;return DexLogic.pageCount((tab==2?array("moves"):tab==3?areaRows():evoRows()).length(),tab==2?4:tab==3?3:4);}

        void palette(){
            if(theme==0){accent=0xffbd3f50;paper=0xffe8eee4;panel=0xfff9fbf2;ink=0xff263f43;muted=0xff677e7b;}
            else if(theme==1){accent=0xff766487;paper=0xffe9e9ee;panel=0xfffaf9fd;ink=0xff343544;muted=0xff727382;}
            else{accent=0xff39464f;paper=0xffe8eff3;panel=0xfffcfefe;ink=0xff233440;muted=0xff687c8b;}
        }
        void rect(Canvas c,float l,float t,float r,float b,int color){p.setColor(color);p.setStyle(Paint.Style.FILL);c.drawRect(l,t,r,b,p);}
        void round(Canvas c,float l,float t,float r,float b,float radius,int color){p.setColor(color);p.setStyle(Paint.Style.FILL);c.drawRoundRect(l,t,r,b,radius,radius,p);}
        void line(Canvas c,float x,float y,float xx,float yy,int color,float width){p.setColor(color);p.setStrokeWidth(width);c.drawLine(x,y,xx,yy,p);}
        void text(Canvas c,String value,float x,float y,float size,int color){
            p.setColor(color);p.setTextSize(size);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setTextAlign(Paint.Align.LEFT);c.drawText(value,x,y,p);
        }
        void center(Canvas c,String value,float x,float y,float size,int color){p.setColor(color);p.setTextSize(size);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setTextAlign(Paint.Align.CENTER);c.drawText(value,x,y,p);p.setTextAlign(Paint.Align.LEFT);}
        String fit(String s,float size,float max){p.setTextSize(size);if(p.measureText(s)<=max)return s;while(s.length()>0&&p.measureText(s+"…")>max)s=s.substring(0,s.length()-1);return s+"…";}
        int wrapText(Canvas c,String value,float x,float y,float width,float size,float leading,int color,int maxLines){
            p.setTextSize(size);StringBuilder current=new StringBuilder();int rows=0;
            for(String word:value.split("\\s+")){
                String next=current.length()==0?word:current+" "+word;
                if(p.measureText(next)>width && current.length()>0){text(c,current.toString(),x,y+rows*leading,size,color);rows++;current.setLength(0);if(rows>=maxLines)return rows;}
                if(current.length()>0)current.append(' ');current.append(word);
            }
            if(current.length()>0 && rows<maxLines){text(c,current.toString(),x,y+rows*leading,size,color);rows++;}return rows;
        }
        void ball(Canvas c,float x,float y,float radius,int color){
            p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2);p.setColor(color);c.drawCircle(x,y,radius,p);c.drawLine(x-radius,y,x+radius,y,p);
            p.setStyle(Paint.Style.FILL);p.setColor(panel);c.drawCircle(x,y,radius*.35f,p);p.setStyle(Paint.Style.STROKE);p.setColor(color);c.drawCircle(x,y,radius*.35f,p);p.setStyle(Paint.Style.FILL);
        }
        void bitmap(Canvas c,Bitmap image,float x,float y,float size){if(image==null)return;p.setFilterBitmap(false);c.drawBitmap(image,null,new RectF(x,y,x+size,y+size),p);}
        void hero(Canvas c,Entry e,float y,float h){
            round(c,20,y,460,y+h,6,panel);
            for(float gy=y+8;gy<y+h;gy+=12)line(c,22,gy,458,gy,paper,1);
            for(float gx=30;gx<460;gx+=12)line(c,gx,y+2,gx,y+h-2,paper,1);
            long elapsed=SystemClock.uptimeMillis()-changed;
            if(animate && elapsed<360){float sy=y+(h-1)*elapsed/360f;line(c,24,sy,456,sy,0xff72c2b8,2);}
            p.setColor(0xffd8e2d3);c.drawOval(130,y+h-34,350,y+h-12,p);
            if(media!=null&&mediaId==e.id){
                if(media.movie!=null){Movie m=media.movie;int duration=m.duration()>0?m.duration():1000;m.setTime(animate?(int)(SystemClock.uptimeMillis()%duration):0);
                    float s=Math.min(210f/Math.max(1,m.width()),(h-24)/Math.max(1,m.height()));s=Math.min(s,3f);
                    c.save();c.translate((480-m.width()*s)/2,y+(h-m.height()*s)/2-7);c.scale(s,s);m.draw(c,0,0);c.restore();
                }else bitmap(c,media.bitmap,140,y+(h-200)/2-5,200);
            }else{Bitmap image=icon(e.id);if(image!=null)bitmap(c,image,140,y+(h-200)/2,200);else ball(c,240,y+h/2,24,muted);}
            text(c,shiny?tr("SHINY","VARIOCOLOR"):"NORMAL",32,y+24,13,muted);
            if(rear)text(c,tr("BACK","ESPALDA"),32,y+44,13,muted);
            if(female)text(c,tr("♀ / DEFAULT","♀ / PREDET."),32,y+64,13,muted);
            if(favorites.contains(""+e.species))text(c,"★",427,y+27,23,accent);
            if(caught.contains(""+e.species))ball(c,438,y+h-20,9,accent);
        }
        @Override protected void onDraw(Canvas canvas){
            super.onDraw(canvas);if(loaded)updateDescription();palette();canvas.drawColor(0xff141f25);
            scale=Math.min(getWidth()/480f,getHeight()/854f);offsetX=(getWidth()-480*scale)/2;offsetY=(getHeight()-854*scale)/2;
            canvas.save();canvas.translate(offsetX,offsetY);canvas.scale(scale,scale);Canvas c=canvas;
            rect(c,0,0,480,854,paper);
            rect(c,0,0,480,83,accent);rect(c,0,78,480,83,0xff943541);
            round(c,18,15,57,54,20,0xffe4f6fc);round(c,23,20,52,49,15,0xff61c9e0);round(c,28,24,37,31,4,0xffffffff);
            for(int i=0;i<3;i++)round(c,70+i*14,21,78+i*14,29,4,i==0?0xfff2b7a3:0xffdc8590);
            text(c,"POKÉDEX",70,60,27,0xffffffff);text(c,tr("FIELD JOURNAL / B2·W2","DIARIO DE CAMPO / B2·W2"),270,59,13,0xfff5dce0);
            if(!loaded){center(c,error.isEmpty()?status:tr("Data unavailable","Datos no disponibles"),240,365,23,ink);if(!error.isEmpty())wrapText(c,error,35,410,410,19,28,ink,6);footer(c);c.restore();return;}
            if(screen==2)drawOptions(c);
            else if(screen==4)drawHelp(c);
            else if(screen==5)drawMoveRecord(c);
            else if(screen==1)drawDetail(c);
            else drawList(c);
            footer(c);
            if(SystemClock.uptimeMillis()<toastUntil){round(c,55,700,425,744,6,ink);center(c,toast,240,729,18,0xffffffff);}
            c.restore();
        }
        void subhead(Canvas c,String left,String right){rect(c,0,83,480,126,panel);text(c,left,22,111,18,ink);p.setTextSize(15);float w=p.measureText(right);text(c,right,458-w,110,15,muted);line(c,0,125,480,125,0xffc6d0cc,1);}
        String number(Entry e){return String.format(Locale.ROOT,"%03d",national?e.national:e.unova);}
        void drawList(Canvas c){
            String mode=national?tr("NATIONAL / 1025","NACIONAL / 1025"):"UNOVA / B2·W2";
            subhead(c,screen==3?(searchName?tr("NAME / T9","NOMBRE / T9"):tr("NUMBER SEARCH","BUSCAR NÚMERO")):mode,filtered.size()+tr(" entries"," entradas"));
            Entry e=entry();
            if(screen==3){round(c,20,141,460,198,5,panel);text(c,query.isEmpty()?(searchName?tr("Type name: 2 ABC · 3 DEF…","Escribe nombre: 2 ABC · 3 DEF…"):tr("Enter Pokédex number…","Escribe el número…")):query,34,178,23,query.isEmpty()?muted:ink);text(c,tr("* mode   # erase   OK open   Clear return","* modo   # borra   OK abre   Clear vuelve"),24,227,17,muted);}
            else if(e!=null){
                hero(c,e,141,212);text(c,tr("No. ","Nº ")+number(e),30,387,19,muted);text(c,fit(nm(e),25,305),145,388,25,ink);
                text(c,collection==1?tr("FAVORITES","FAVORITOS"):collection==2?tr("CAUGHT","CAPTURADOS"):typeFilter>0?tOpt(typeFilter).toUpperCase(Locale.ROOT):tr("SEEN IN YOUR JOURNEY","VISTOS EN TU DIARIO"),24,422,13,muted);
            }
            if(e==null){center(c,tr("No matching Pokémon","Ningún Pokémon coincide"),240,365,24,ink);center(c,screen==3?tr("Clear erases / returns to the journal","Clear borra / vuelve al diario"):tr("* Options → Reset filters","* Opciones → Borrar filtros"),240,405,19,muted);return;}
            float top=screen==3?250:438;int rows=screen==3?8:5;int first=(selection/rows)*rows;
            for(int n=0;n<rows&&first+n<filtered.size();n++){
                int at=first+n;Entry row=filtered.get(at);float y=top+n*59;boolean focused=at==selection;
                if(focused){round(c,18,y,462,y+54,4,accent);rect(c,18,y+5,23,y+49,0xffffd59c);}
                else{round(c,20,y,460,y+54,4,panel);}
                Bitmap img=icon(row.id);bitmap(c,img,59,y-1,56);
                int fg=focused?0xffffffff:ink; text(c,number(row),29,y+33,16,focused?0xfffbdadd:muted);text(c,fit(nm(row),20,267),121,y+33,20,fg);
                if(caught.contains(""+row.species))ball(c,427,y+27,9,fg);else if(favorites.contains(""+row.species))text(c,"★",416,y+34,20,fg);
            }
            text(c,(selection+1)+" / "+filtered.size(),24,screen==3?749:756,14,muted);
            text(c,"★ "+favorites.size()+"     ✓ "+caught.size(),208,screen==3?749:756,14,muted);
        }
        int typeColor(String t){
            String[] names={"Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark","Fairy"};
            int[] colors={0xff7b816b,0xffae4b3e,0xff777dbc,0xff9563a5,0xffaa8c48,0xff96854a,0xff7c9639,0xff71618d,0xff768b97,0xffc96937,0xff497fbd,0xff588e4e,0xffab902d,0xffbb5e85,0xff4d959d,0xff7163af,0xff625954,0xffbd6f8f};
            for(int i=0;i<names.length;i++)if(names[i].equals(t))return colors[i];return muted;
        }
        void types(Canvas c,JSONArray ts,float y){int count=ts.length();float start=240-count*57;for(int i=0;i<count;i++){String t=ts.optString(i);round(c,start+i*114,y,start+i*114+106,y+27,3,typeColor(t));center(c,tn(t).toUpperCase(Locale.ROOT),start+i*114+53,y+19,14,0xffffffff);}}
        void drawDetail(Canvas c){
            Entry e=entry();if(e==null){center(c,tr("No selected entry","Ninguna ficha seleccionada"),240,400,23,ink);return;}
            subhead(c,fit(tr("No. ","Nº ")+number(e)+"  "+nm(e),18,318),national?tr("NATIONAL","NACIONAL"):"UNOVA");
            hero(c,e,139,202);types(c,e.types,348);
            for(int n=0;n<tabs.length;n++){float x=16+n*90;round(c,x,391,x+86,430,3,n==tab?accent:panel);center(c,tabs[n],x+43,416,14,n==tab?0xffffffff:muted);}
            round(c,18,442,462,738,6,panel);
            if(detail==null||detailId!=e.id){center(c,tr("Loading entry…","Cargando ficha…"),240,550,20,muted);return;}
            page=Math.min(page,detailPages()-1);
            c.save();c.clipRect(22,446,458,735);
            if(tab==0)drawEntry(c,e);
            else if(tab==1)drawStats(c);
            else if(tab==2)drawMoves(c);
            else if(tab==3)drawArea(c);
            else drawEvolve(c);
            c.restore();
            text(c,(page+1)+" / "+detailPages(),24,759,15,muted);
        }
        void drawEntry(Canvas c,Entry e){
            if(page==0){
                text(c,dstr(detail,"genus"),32,474,20,ink);text(c,String.format(Locale.ROOT,(es?"Alt. %.1f m     Peso %.1f kg":"HT  %.1f m       WT  %.1f kg"),detail.optDouble("height"),detail.optDouble("weight")),32,507,18,muted);
                String[] ft=flavorText();String flavor=ft[0];
                text(c,ft[1],32,548,13,accent);
                wrapText(c,flavor,32,580,416,20,28,ink,5);
            }else if(page==1){
                text(c,tr("ABILITIES","HABILIDADES"),32,474,15,accent);JSONArray aa=array("abilities");float y=510;
                for(int i=0;i<aa.length();i++){JSONObject a=aa.optJSONObject(i);if(a==null)continue;text(c,dstr(a,"name")+(a.optBoolean("hidden")?tr("  [hidden]","  [oculta]"):""),32,y,20,ink);int lines=wrapText(c,dstr(a,"text"),32,y+25,412,16,21,muted,2);y+=34+lines*21;}
            }else{
                text(c,tr("BREEDING & FIELD NOTES","CRIANZA Y NOTAS DE CAMPO"),32,474,15,accent);
                text(c,tr("Egg groups: ","Grupos huevo: ")+join(dstrs(detail,"eggGroups")),32,515,18,ink);
                int gender=detail.optInt("genderRate");text(c,tr("Gender: ","Género: ")+(gender<0?tr("Genderless","Sin género"):String.format(Locale.ROOT,"%.1f%% "+tr("female","hembra"),gender*12.5)),32,552,18,ink);
                text(c,tr("Catch rate: ","Ratio de captura: ")+detail.optInt("captureRate")+" / 255",32,589,18,ink);
                text(c,tr("Base friendship: ","Amistad base: ")+detail.optInt("friendship"),32,626,18,ink);
                text(c,tr("Egg cycles: ","Ciclos de huevo: ")+detail.optInt("hatchCounter"),32,663,18,ink);
                text(c,tr("3 forms · 6 cry · 7 back · 9 female","3 formas · 6 grito · 7 espalda · 9 hembra"),32,710,15,muted);
            }
        }
        String join(JSONArray a){StringBuilder b=new StringBuilder();for(int i=0;i<a.length();i++){if(i>0)b.append(" / ");b.append(a.optString(i));}return b.toString();}
        void drawStats(Canvas c){
            if(page==0){
                String[] labels=es?new String[]{"PS","ATAQUE","DEFENSA","AT. ESP.","DEF. ESP.","VELOCIDAD"}:new String[]{"HP","ATTACK","DEFENSE","SP. ATK","SP. DEF","SPEED"};JSONArray stats=array("stats");int total=0;
                for(int i=0;i<6;i++){int v=stats.optInt(i);total+=v;float y=480+i*35;text(c,labels[i],32,y,15,muted);text(c,""+v,142,y,18,ink);round(c,190,y-15,438,y,2,paper);round(c,190,y-15,190+248*v/255f,y,2,i%2==0?accent:0xff6b9693);}
                text(c,tr("BASE STAT TOTAL","TOTAL BASE"),32,713,14,muted);text(c,""+total,375,714,23,ink);
            }else{
                boolean later=detail.optInt("species")>649;text(c,later?tr("DEFENSIVE TYPE MATCHUPS / GEN VI+","DEBILIDADES Y RESISTENCIAS / GEN VI+"):tr("DEFENSIVE TYPE MATCHUPS / GEN V","DEBILIDADES Y RESISTENCIAS / GEN V"),32,473,14,accent);JSONArray a=array("matchups");float y=505;int col=0;
                for(int i=0;i<a.length();i++){JSONObject t=a.optJSONObject(i);if(t==null)continue;float x=32+(col%2)*210;text(c,tn(t.optString("type")),x,y,17,ink);text(c,"×"+t.optDouble("factor"),x+120,y,17,t.optDouble("factor")>1?accent:muted);col++;if(col%2==0)y+=25;}
                if(!later)text(c,tr("Steel retains Ghost / Dark resistance.","Acero conserva resistencia a Fantasma / Siniestro."),32,718,14,muted);
            }
        }
        // ---- B2W2-style move plates (kyf37-ds-moves)
        int shade(int color,float f){int r=(color>>16)&255,g=(color>>8)&255,b=color&255;
            if(f>0){r+=(int)((255-r)*f);g+=(int)((255-g)*f);b+=(int)((255-b)*f);}else{r=(int)(r*(1+f));g=(int)(g*(1+f));b=(int)(b*(1+f));}
            return 0xff000000|(r<<16)|(g<<8)|b;}
        void typePill(Canvas c,String type,float l,float t,float w,float h){int tc=typeColor(type);
            round(c,l,t,l+w,t+h,h/2,shade(tc,-0.25f));round(c,l+1.5f,t+1.5f,l+w-1.5f,t+h-1.5f,h/2,tc);
            p.setColor(0xffffffff);p.setTextSize(h*0.56f);p.setTypeface(Typeface.create("sans-serif-condensed",Typeface.BOLD));p.setTextAlign(Paint.Align.CENTER);
            c.drawText(tn(type).toUpperCase(Locale.getDefault()),l+w/2,t+h*0.7f,p);p.setTextAlign(Paint.Align.LEFT);}
        void categoryIcon(Canvas c,String cat,float cx,float cy,float r){
            if("physical".equals(cat)){round(c,cx-r,cy-r*0.72f,cx+r,cy+r*0.72f,r*0.3f,0xffc92112);p.setColor(0xfff7d038);
                android.graphics.Path star=new android.graphics.Path();for(int i=0;i<10;i++){double a=-Math.PI/2+i*Math.PI/5;float rr=i%2==0?r*0.62f:r*0.28f;
                    float x=cx+(float)Math.cos(a)*rr,y=cy+(float)Math.sin(a)*rr*0.9f;if(i==0)star.moveTo(x,y);else star.lineTo(x,y);}star.close();c.drawPath(star,p);}
            else if("special".equals(cat)){round(c,cx-r,cy-r*0.72f,cx+r,cy+r*0.72f,r*0.3f,0xff4f5870);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(r*0.14f);p.setColor(0xff8fd6ff);
                c.drawCircle(cx,cy,r*0.48f,p);c.drawCircle(cx,cy,r*0.22f,p);p.setStyle(Paint.Style.FILL);}
            else{round(c,cx-r,cy-r*0.72f,cx+r,cy+r*0.72f,r*0.3f,0xff8c888c);p.setColor(0xffffffff);c.drawCircle(cx-r*0.28f,cy,r*0.2f,p);c.drawCircle(cx+r*0.28f,cy,r*0.2f,p);}
        }
        String learnBadge(JSONObject m){String method=m.optString("method");
            return method.equals("level-up")?tr("Lv. ","Nv. ")+m.optInt("level"):method.equals("machine")?(m.optInt("machine")>=100?tr("HM","MO")+(m.optInt("machine")-100):tr("TM","MT")+m.optString("machine")):method.equals("egg")?tr("EGG","HUEVO"):method.equals("tutor")?"TUTOR":method.toUpperCase(Locale.ROOT);}
        void movePlate(Canvas c,JSONObject m,float l,float t,float r,float b,boolean selected){
            int tc=typeColor(m.optString("type"));
            if(selected){round(c,l-4,t-4,r+4,b+4,12,0xffffffff);round(c,l-2,t-2,r+2,b+2,11,accent);}
            round(c,l,t,r,b,9,shade(tc,-0.35f));round(c,l+2,t+2,r-2,b-2,8,shade(tc,0.72f));
            round(c,l+2,t+2,r-2,(t+b)/2,8,shade(tc,0.82f));
            typePill(c,m.optString("type"),l+10,t+(b-t)/2-12,82,24);
            p.setColor(0xff202020);p.setTextSize(19);p.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));p.setTextAlign(Paint.Align.LEFT);
            c.drawText(fit(dstr(m,"name"),19,215),l+102,t+(b-t)/2+7,p);
            p.setTextSize(13);p.setTypeface(Typeface.create("sans-serif-medium",Typeface.NORMAL));p.setColor(shade(tc,-0.55f));p.setTextAlign(Paint.Align.RIGHT);
            c.drawText("PP "+m.optString("pp"),r-12,t+(b-t)/2-3,p);c.drawText(learnBadge(m),r-12,t+(b-t)/2+14,p);p.setTextAlign(Paint.Align.LEFT);
        }
        void drawMoves(Canvas c){
            JSONArray moves=array("moves");
            text(c,moves.length()+tr(" MOVES"," MOVIMIENTOS"),32,474,14,accent);
            if(moves.length()==0){wrapText(c,tr("No learnset is recorded for this form.","No hay movimientos registrados para esta forma."),32,525,405,19,28,ink,5);return;}
            for(int n=0;n<4 && page*4+n<moves.length();n++){
                JSONObject m=moves.optJSONObject(page*4+n);if(m==null)continue;float y=490+n*58;
                movePlate(c,m,26,y,454,y+48,page*4+n==moveIndex);
            }
        }
        void drawMoveRecord(Canvas c){
            JSONObject m=array("moves").optJSONObject(moveIndex);if(m==null)return;
            subhead(c,tr("MOVE","MOVIMIENTO"),(moveIndex+1)+" / "+array("moves").length());
            movePlate(c,m,22,150,458,206,false);
            // stat boxes, like the B2W2 summary screen
            String[] heads={tr("CATEGORY","CATEGORÍA"),tr("POWER","POTENCIA"),tr("ACCURACY","PRECISIÓN"),"PP"};
            String pw=m.optString("power"),ac=m.optString("accuracy");
            String[] vals={"",pw.isEmpty()||pw.equals("null")?"—":pw,ac.isEmpty()||ac.equals("null")?"—":ac,m.optString("pp")};
            for(int i=0;i<4;i++){float l=22+i*110,t=222;
                round(c,l,t,l+104,t+86,8,shade(accent,-0.3f));round(c,l+2,t+2,l+102,t+84,7,0xfff8f8f0);
                round(c,l+2,t+2,l+102,t+26,7,shade(accent,0.15f));
                p.setColor(0xffffffff);p.setTextSize(12);p.setTypeface(Typeface.create("sans-serif-condensed",Typeface.BOLD));p.setTextAlign(Paint.Align.CENTER);
                c.drawText(heads[i],l+52,t+19,p);
                if(i==0)categoryIcon(c,m.optString("category"),l+52,t+56,22);
                else{p.setColor(0xff202020);p.setTextSize(26);p.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));c.drawText(vals[i],l+52,t+66,p);}
                p.setTextAlign(Paint.Align.LEFT);}
            text(c,catLabel(m.optString("category"))+"  ·  "+methodLabel(m.optString("method"))+"  "+learnBadge(m),26,336,15,muted);
            // DS text box
            round(c,18,352,462,560,10,0xff5a5a68);round(c,22,356,458,556,8,0xfff8f8f0);round(c,26,360,454,552,6,0xffffffff);
            wrapText(c,dstr(m,"text"),40,396,404,19,30,0xff303030,6);
        }
        JSONArray areaRowsCache=new JSONArray();JSONObject areaRowsDetail;int areaRowsGame=-1;
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
        void drawEvolve(Canvas c){
            JSONArray a=evoRows();text(c,(detail.optInt("species")>649?tr("EVOLUTION FAMILY / GEN VI+","FAMILIA EVOLUTIVA / GEN VI+"):tr("EVOLUTION FAMILY / GEN V","FAMILIA EVOLUTIVA / GEN V")),32,474,14,accent);
            for(int n=0;n<4&&page*4+n<a.length();n++){
                JSONObject e=a.optJSONObject(page*4+n);if(e==null)continue;float y=508+n*55;
                if(page*4+n==moveIndex)round(c,22,y-34,458,y+28,8,paper);
                bitmap(c,icon(e.optInt("id")),27,y-28,50);text(c,dstr(e,"name"),89,y,19,ink);
                JSONArray conditions=dstrs(e,"conditions");String condition=e.optBoolean("form")?tr("Alternate form","Forma alternativa"):conditions.length()==0?tr("Base stage","Etapa base"):join(conditions);
                if(e.optInt("from")>0){for(Entry from:all)if(from.id==e.optInt("from")){condition=tr("From ","Desde ")+nm(from)+": "+condition;break;}}
                text(c,fit(condition,13,352),89,y+20,13,muted);
            }
        }
        void drawOptions(Canvas c){
            subhead(c,tr("JOURNAL OPTIONS","OPCIONES DEL DIARIO"),tr("◀ ▶ change","◀ ▶ cambiar"));String[] values={national?tr("National · 1025","Nacional · 1025"):"Unova · B2W2",collection==0?tr("All Pokémon","Todos"):collection==1?tr("Favorites","Favoritos"):tr("Caught","Capturados"),tOpt(typeFilter),sort==0?tr("Pokédex number","Nº Pokédex"):"A → Z",theme==0?tr("Diamond","Diamante"):theme==1?tr("Platinum","Platino"):tr("White","Blanco"),animate?tr("On","Sí"):tr("Off","No"),whiteText?tr("White 2","Blanco 2"):tr("Black 2","Negro 2"),tr("Reset","Borrar"),tr("Read","Leer"),tr("Return","Volver"),tr("Open","Abrir")};
            String[] labels=es?new String[]{"Pokédex","Colección","Filtro de tipo","Orden","Tema de carcasa","Animaciones","Texto de ficha","Borrar filtros","Teclas y créditos","Volver al diario","Identificar (IA)"}:new String[]{"Pokédex","Collection","Type filter","Order","Shell theme","Animations","Entry text","Clear filters","Keys & credits","Back to journal","Identify (AI)"};
            for(int i=0;i<labels.length;i++){float y=143+i*52;round(c,18,y,462,y+47,4,i==menu?accent:panel);text(c,labels[i],32,y+32,19,i==menu?0xffffffff:ink);String v=fit(values[i],16,206);p.setTextSize(16);text(c,v,444-p.measureText(v),y+32,16,i==menu?0xfffce2e4:muted);}
        }
        void drawHelp(Canvas c){
            subhead(c,tr("TRAINER'S GUIDE","GUÍA DEL ENTRENADOR"),tr("Clear: return","Clear: volver"));
            String[] lines=es?helpEs():new String[]{"D-pad moves; OK opens an entry.","Left/right changes tabs or list pages.","0 searches by number; * selects T9 name.","T9: 2 ABC · 3 DEF · 4 GHI · 5 JKL", "6 MNO · 7 PQRS · 8 TUV · 9 WXYZ", "Clear/# erases; OK opens a result.","1 favorite · 5 caught · 2/8 prev/next", "Entry: 3 form · 7 back · 9 female", "AREA: 0 previous game; OK next game", "6 plays the original legacy cry", "# shiny · * options · Clear returns", "", "Records: PokéAPI / Veekun / WikiDex", "Sprites: PokeAPI/sprites (Gen V; Gen VI-IX static)", "Pokémon © Nintendo / Creatures /", "GAME FREAK. Unofficial fan project.", "Gen V sprites are shared B/W assets;", "B2W2 animation changes may differ.", "9 on list: offline photo identification"};
            float y=158;for(String s:lines){text(c,s,26,y,18,ink);y+=30;}
        }
        void footer(Canvas c){
            rect(c,0,777,480,854,accent);line(c,0,777,480,777,0xffedb8b1,3);
            String left=screen==0?tr("Search","Buscar"):screen==3?tr("Erase","Borrar"):tr("Back","Atrás");String right=screen==0?tr("Scan","Escanear"):screen==1?tr("Shiny","Variocolor"):screen==3?tr("T9 / No.","T9 / Nº"):tr("Change","Cambiar");
            if(screen==4||screen==5){left=tr("Back","Atrás");right=left;}
            String bottomLeft=screen<=1?tr("Settings","Ajustes"):"";String bottomRight=screen<=1?tr("Favorite","Favorito"):"";
            footerCell(c,left,12,785,170,813);footerCell(c,right,310,785,468,813);
            footerCell(c,bottomLeft,12,818,170,846);footerCell(c,bottomRight,310,818,468,846);
            round(c,183,789,297,844,27,0xfff7f3e9);ball(c,240,806,9,accent);center(c,screen==1?(tab==2?tr("MOVE","MOVER"):tab==0?tr("TEXT","TEXTO"):tab==3?tr("GAME","JUEGO"):tr("TOP","INICIO")):screen==4||screen==5?tr("BACK","ATRÁS"):"OK",240,833,16,accent);
        }
        void footerCell(Canvas c,String value,float l,float t,float r,float b){round(c,l,t,r,b,4,0x33301522);center(c,value,(l+r)/2,t+20,15,0xffffffff);}
        @Override public boolean onTouchEvent(android.view.MotionEvent ev){
            if(ev.getAction()!=MotionEvent.ACTION_UP)return true;float x=(ev.getX()-offsetX)/scale,y=(ev.getY()-offsetY)/scale;int key=-1;
            if(y>=777){if(x<175)key=y<816?KeyEvent.KEYCODE_F1:KeyEvent.KEYCODE_5;else if(x>305)key=y<816?KeyEvent.KEYCODE_F2:KeyEvent.KEYCODE_POUND;else key=KeyEvent.KEYCODE_DPAD_CENTER;}
            else if(screen==2&&y>=143&&y<733){menu=Math.min(10,(int)((y-143)/52));key=KeyEvent.KEYCODE_DPAD_CENTER;}
            else if((screen==0||screen==3)&&y>=(screen==3?250:438)&&y<733){int rows=screen==3?8:5;int idx=(selection/rows)*rows+(int)((y-(screen==3?250:438))/59);if(idx<filtered.size()){selection=idx;queueSelection();key=KeyEvent.KEYCODE_DPAD_CENTER;}}
            else if(screen==1&&y>=391&&y<=430){tab=DexLogic.clamp((int)((x-16)/90),5);page=0;invalidate();}
            else if(screen==1&&y>445&&y<738){page= DexLogic.wrap(page+1,detailPages());invalidate();}
            if(key>=0)key(new KeyEvent(KeyEvent.ACTION_DOWN,key));performClick();return true;
        }
        @Override public boolean performClick(){super.performClick();return true;}
    }
}
