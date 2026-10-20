package org.kyf37.walker;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.view.*;
import java.util.*;
import java.util.concurrent.*;

/** Keypad-only UI, designed at 480×854. App owns its contextual bottom bar. */
public final class WalkerActivity extends Activity {
    private Walker walker, demo;private WalkerView view;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private ReaderFiles readerFiles;private volatile WalkerReader.Identity hardwareIdentity;
    private volatile byte[] hardwareSnapshot,hardwareRom;private int hardwareChoice;
    private boolean hardwareDetails;
    private final RealMenu realMenu=new RealMenu();private boolean confirmRom;private boolean exportingRom;
    private volatile IrSession ir;private volatile boolean connecting, cancelled;
    private volatile String connection="Ready; real-game sync is still unverified";
    private boolean demoMode;private int page,selection,bush,tries,encounter=-1,hp=4;
    private boolean battle;
    private final Random random=new Random();private String message="";
    private final String[] menu={"Walk","Poké Radar · 10 W","Dowsing · 3 W","Pokémon & items","Connect to game","Trainer card","Settings & help","Real Pokewalker","Emulated Pokewalker"}; // menu-9: emulated
    private final Runnable refresh=new Runnable(){public void run(){if(view!=null){view.invalidate();ui.postDelayed(this,500);}}};
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        // Remove the legacy standalone emulator task; save files are untouched.
        try {
            ActivityManager manager = (ActivityManager)getSystemService(ACTIVITY_SERVICE);
            for (ActivityManager.AppTask task : manager.getAppTasks()) {
                ActivityManager.RecentTaskInfo info = task.getTaskInfo();
                ComponentName component = info.baseIntent == null ? null : info.baseIntent.getComponent();
                if (info.id != getTaskId() && component != null
                        && getPackageName().equals(component.getPackageName())
                        && EmulatedWalkerActivity.class.getName().equals(component.getClassName())) {
                    task.finishAndRemoveTask();
                }
            }
        } catch (RuntimeException failure) {
            android.util.Log.w("Pokewalker", "Legacy task cleanup unavailable", failure);
        }
        // TWO_LANGUAGES: preference affects UI only, never game/save bytes.
        UiText.choose(getSharedPreferences("ui",0).getString("language",UiText.defaultLanguage(Locale.getDefault().toLanguageTag())));
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().getDecorView().setSystemUiVisibility(5894);
        try{walker=SaveFile.get(this);}catch(Exception e){message="Save could not be loaded. Existing file preserved.";}
        try{readerFiles=new ReaderFiles(this);hardwareIdentity=readerFiles.identity();hardwareSnapshot=readerFiles.latest();hardwareRom=readerFiles.latestRom();}
        catch(Exception e){message="Previous readback could not be loaded; files preserved.";connection=message;}
        demo=new Walker(null,bytes->{});view=new WalkerView();setContentView(view);view.requestFocus();
    }
    private void toggleLanguage(){
        UiText.choose(UiText.spanish?"en":"es-ES");
        getSharedPreferences("ui",0).edit().putString("language",UiText.language()).apply();
        StepService.refreshLanguage(this);message="";
    }
    private String localizedDescription(String title,Walker w){
        StringBuilder b=new StringBuilder(UiText.tr(title)).append(". ").append(UiText.tr(demoMode?"Demo":"Real save"));
        if(page==0)b.append(". ").append(UiText.tr(menu[selection]));
        b.append(". ").append(UiText.tr(message)).append(". ").append(UiText.tr(connection));
        if(page==7)b.append(". ").append(UiText.tr("Language: "+(UiText.spanish?"Español (España)":"English")));
        if(page==8){
            b.append(". ").append(realMenu.description());if(confirmRom)b.append(". ").append(UiText.tr("Confirm ROM dump. Temporary RAM payload. OK connects; Back cancels."));
            if(hardwareIdentity==null)b.append(". ").append(UiText.tr("No capture"));
            else{WalkerReader.Identity id=hardwareIdentity;
                b.append(". ").append(id.trainer).append(". ").append(UiText.tr("Trainer ID: "+id.trainerId))
                 .append(". ").append(UiText.tr("Steps today: "+id.steps)).append(". ").append(UiText.tr("Secret ID: "+id.secretId))
                 .append(". ").append(UiText.tr("Paired: "+id.paired)).append(". ").append(UiText.tr("Has Pokemon: "+id.hasPokemon))
                 .append(". ").append(UiText.tr("Last sync (raw): "+id.lastSync));
            }
            b.append(". ").append(UiText.tr(hardwareSnapshot==null?"No backup":"64 KiB backup available"));
            b.append(". ").append(UiText.tr(hardwareRom==null?"No ROM capture":"48 KiB ROM available"));
        }
        if(w==null)b.append(". ").append(UiText.tr("Save error"));
        else b.append(". ").append(UiText.tr(w.steps()+" steps")).append(". ").append(UiText.tr(w.watts()+" watts"))
              .append(". ").append(w.caughtCount()).append(UiText.spanish?" capturados. ":" caught. ").append(w.itemCount()).append(UiText.spanish?" objetos.":" items.");
        return b.toString();
    }
    private Walker active(){return demoMode?demo:walker;}
    @Override public void onResume(){super.onResume();ui.post(refresh);}
    @Override public void onPause(){ui.removeCallbacks(refresh);stopIr();realMenu.confirm=false;confirmRom=false;super.onPause();}
    @Override public void onDestroy(){stopIr();worker.shutdownNow();super.onDestroy();}
    @Override public void onBackPressed(){back();}
    private void back(){if(page==8&&!connecting){if(hardwareDetails){hardwareDetails=false;view.invalidate();return;}if(realMenu.confirm||confirmRom){realMenu.confirm=false;confirmRom=false;view.invalidate();return;}if(realMenu.mode!=0){realMenu.mode=0;realMenu.row=0;view.invalidate();return;}}if(connecting)stopIr();if(page!=0){page=0;message="";}else finish();view.invalidate();}
    private void stopIr(){cancelled=true;IrSession current=ir;ir=null;if(current!=null)current.close();if(walker!=null)walker.disconnect();if(connecting)connection="Connection stopped";}
    private void connect(){
        if(demoMode){simulate();return;}if(connecting){stopIr();return;}
        if(walker==null)return;
        connecting=true;cancelled=false;connection="Requesting infrared access…";
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        worker.execute(()->{
            try(java.io.PrintWriter trace=new java.io.PrintWriter(new java.io.File(getFilesDir(),"last-ir-session.txt"));
                    IrSession session=new IrSession(this)){
                ir=session;if(cancelled)return;
                connection="Point phone IR at the rear IR window of your patched 3DS";
                long deadline=SystemClock.elapsedRealtime()+300000,lastAdvert=0,lastPacket=SystemClock.elapsedRealtime();
                int bad=0;
                while(!cancelled && SystemClock.elapsedRealtime()<deadline){
                    long now=SystemClock.elapsedRealtime();
                    if(walker.connected() && now-lastPacket>5000){walker.disconnect();connection="Connection timed out; retry in game";}
                    if(!walker.connected() && now-lastAdvert>=300){session.send(new byte[]{0x56});lastAdvert=now;}
                    byte[] b=session.read();if(b.length==0 || (b.length==1 && b[0]==0x56))continue;
                    trace.printf(Locale.ROOT,"%d RX %02X bytes=%d%n",now,(b[0]^0xaa)&255,b.length);
                    try{
                        byte[] reply=walker.receive(b);lastPacket=now;
                        if(reply!=null){session.send(reply);connection=walker.status;trace.printf(Locale.ROOT,"%d TX %02X bytes=%d%n",SystemClock.elapsedRealtime(),(reply[0]^0xaa)&255,reply.length);}
                        if((b[0]^0xaa)==0xf4){connection=walker.status;break;}
                    }catch(IllegalArgumentException e){trace.println("Rejected: "+e.getMessage());if(++bad>=20)throw e;connection=e.getMessage();}
                }
                if(!cancelled && connection.startsWith("Point"))connection="No game found. Retry from the game menu.";
            }catch(Exception e){connection=e.getMessage()==null?"Infrared session failed":e.getMessage();}
            finally{ir=null;walker.disconnect();connecting=false;ui.post(()->{getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);if(view!=null)view.invalidate();});}
        });
    }
    private void readHardware(boolean fullBackup){
        if(connecting){stopIr();return;}
        if(readerFiles==null){message="Readback storage unavailable; existing files preserved.";return;}
        connecting=true;cancelled=false;connection="Choose CONNECT on your real Pokewalker. Aim its IR window at the phone.";
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        worker.execute(()->{
            try(IrSession session=new IrSession(this)){
                ir=session;if(cancelled)throw new java.io.IOException("Read cancelled");
                WalkerReader reader=new WalkerReader(session,()->cancelled);
                WalkerReader.Result result=reader.read(fullBackup,bytes->connection="Reading device backup: "+(bytes*100/65536)+"% · F2 cancels");
                if(cancelled)throw new java.io.IOException("Read cancelled");
                byte[] snapshot=result.snapshot();
                if(snapshot!=null){readerFiles.save(snapshot);hardwareSnapshot=snapshot;}
                readerFiles.identity(result.identity);hardwareIdentity=result.identity;if(!fullBackup)ui.post(()->hardwareDetails=true);
                connection=fullBackup?"Full 64 KiB backup saved separately. F3 exports it.":"Trainer data received. The app's walking save was not replaced.";
            }catch(Exception e){connection=cancelled?"Read cancelled; previous captures preserved.":e.getMessage()==null?"Device read failed":e.getMessage();}
            finally{ir=null;connecting=false;ui.post(()->{getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);if(view!=null)view.invalidate();});}
        });
    }
    private void selectHardware(){
        if(hardwareDetails){hardwareDetails=false;return;}
        if(connecting){stopIr();return;}
        message="";
        if(confirmRom){confirmRom=false;advancedHardware(5);return;}
        if(realMenu.confirm){realMenu.confirm=false;advancedHardware(realMenu.mode==1?2:realMenu.mode==2?3:4);return;}
        if(realMenu.mode==0){
            hardwareChoice=realMenu.choice;
            if(hardwareChoice<2){readHardware(hardwareChoice==1);return;}
            if(hardwareChoice==5){confirmRom=true;return;}
            realMenu.mode=hardwareChoice==2?1:hardwareChoice==3?2:3;realMenu.row=0;realMenu.editing=false;
        }else if(realMenu.row==realMenu.values().length){
            if(realMenu.valid())realMenu.confirm=true;else message="Choose a Pokemon, first move and valid level, or a nonzero item/watt value.";
        }else{realMenu.editing=!realMenu.editing;realMenu.digits="";}
    }
    private void advancedHardware(int action){
        if(connecting||readerFiles==null)return;
        final int[] watts=realMenu.watts.clone();final int item=realMenu.item[0];final WalkerTools.Gift gift=new WalkerTools.Gift(realMenu.gift.clone());
        connecting=true;cancelled=false;connection="Choose CONNECT on your real Pokewalker. Aim its IR window at the phone.";
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        worker.execute(()->{
            final boolean[] backed={false};
            try(IrSession session=new IrSession(this)){
                ir=session;if(cancelled)throw new java.io.IOException("Cancelled");
                WalkerTools tools=new WalkerTools(new WalkerReader(session,()->cancelled));
                WalkerTools.Backup backup=bytes->{if(cancelled)throw new java.io.IOException("Cancelled before changes");readerFiles.save(bytes);hardwareSnapshot=bytes;backed[0]=true;connection="Backup saved. Applying selected operation...";};
                WalkerReader.Progress progress=bytes->connection=(action==5?"Reading ROM: ":"Saving backup first: ")+(bytes*100/(action==5?49152:65536))+"% · F2 stops";
                if(action==2)tools.watts(watts[0],watts[1],watts[2]==1,backup,progress);
                else if(action==3)tools.pokemon(gift,backup,progress);
                else if(action==4)tools.item(item,backup,progress);
                else{byte[] rom=tools.rom(progress);if(cancelled)throw new java.io.IOException("Cancelled");readerFiles.saveRom(rom);hardwareRom=rom;}
                connection=action==5?"48 KiB ROM saved separately. Select Dump ROM and F3 to export.":"Walker acknowledged the operation. F3 exports the backup from before changes.";
            }catch(Exception e){connection=(cancelled?"Operation cancelled":e.getMessage()==null?"Operation failed":e.getMessage())+(backed[0]?". Changes may be partial; pre-change backup retained.":". Earlier captures preserved.");}
            finally{ir=null;connecting=false;ui.post(()->{getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);if(view!=null)view.invalidate();});}
        });
    }
    private void exportHardware(){
        if(connecting){message="Finish or cancel the read before exporting.";return;}
        exportingRom=realMenu.mode==0&&realMenu.choice==5;
        if((exportingRom?hardwareRom:hardwareSnapshot)==null){message=exportingRom?"Dump the ROM first.":"Read a full backup first.";return;}
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/octet-stream").putExtra(Intent.EXTRA_TITLE,exportingRom?"pokewalker-rom.bin":"pokewalker-eeprom.bin");
        try{startActivityForResult(intent,83);}catch(ActivityNotFoundException e){message="No file picker installed. Private backup retained.";}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=83||result!=RESULT_OK||data==null||data.getData()==null||(exportingRom?hardwareRom:hardwareSnapshot)==null)return;
        final byte[] backup=(exportingRom?hardwareRom:hardwareSnapshot).clone();final android.net.Uri uri=data.getData();
        worker.execute(()->{
            try(java.io.OutputStream out=getContentResolver().openOutputStream(uri,"w")){
                if(out==null)throw new java.io.IOException("Destination unavailable");out.write(backup);out.flush();
                ui.post(()->{message=backup.length==49152?"48 KiB ROM exported.":"64 KiB backup exported.";if(view!=null)view.invalidate();});
            }catch(Exception e){ui.post(()->{message="Export failed; private backup retained.";if(view!=null)view.invalidate();});}
        });
    }
    /** Disposable game fixture; never reads or changes the real walker save. */
    private void simulate(){
        try{
            demo=new Walker(null,bytes->{});byte[] master={1,2,3,4};
            Packet reply=Packet.decode(demo.receive(new Packet(0xfa,1,master,new byte[0]).encode()));
            byte[] sid=new byte[4];for(int i=0;i<4;i++)sid[i]=(byte)(master[i]^reply.session[i]);
            byte[] id=new byte[104];id[0x5b]=3;id[0x5c]=2;
            demo.receive(new Packet(0x32,1,sid,id).encode());
            byte[] route=new byte[128];route[0]=25;route[12]=5;route[82]=16;route[94]=3;
            demo.receive(new Packet(2,0xd7,sid,route).encode());
            route=new byte[128];route[8]=100;route[12]=13;route[52]=100;
            demo.receive(new Packet(0x82,0xd7,sid,route).encode());
            demo.receive(new Packet(0x5a,1,sid,new byte[0]).encode());demo.disconnect();demo.addSteps(2000);
            message="Demo game transfer complete. Real save untouched.";
        }catch(Exception e){message="Simulator error: "+e.getMessage();}
    }
    private void toggleWalking(){
        if(demoMode){try{demo.addSteps(20);message="Demo: +20 steps";}catch(Exception e){message=e.getMessage();}return;}
        if(StepService.running){stopService(new Intent(this,StepService.class));return;}
        if(Build.VERSION.SDK_INT>=29 && checkSelfPermission("android.permission.ACTIVITY_RECOGNITION")!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{"android.permission.ACTIVITY_RECOGNITION"},37);return;
        }
        startForegroundService(new Intent(this,StepService.class));
    }
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] results){
        super.onRequestPermissionsResult(code,permissions,results);
        if(code==37 && results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)toggleWalking();
        else message="Step permission denied; save retained";
    }
    private void select(){
        if(page==0 && selection==8){stopIr();startActivity(new android.content.Intent(this,EmulatedWalkerActivity.class));return;} // menu-9 open
        if(page==8 || (page==0 && selection==7)){
            if(page==0){page=8;message="";}else selectHardware();
            view.invalidate();return;
        }
        Walker w=active();if(w==null)return;
        try{
            if(page==0){
                page=selection+1;message="";
                if(page==2 || page==3){
                    if(!w.strolling()){message="Receive a Pokémon from the game first.";return;}
                    if(!w.spendWatts(page==2?10:3)){message="Walk more to earn watts.";return;}
                    encounter=w.chooseEncounter(random,page==3);tries=page==2?4:2;hp=4;bush=0;hiddenBush=random.nextInt(page==2?4:6);battle=false;
                    message=encounter<0?"Nothing found this time.":page==2?"Choose a bush to find the Pokémon.":"An item is hiding in one of six bushes.";
                }
            }else if(page==1)toggleWalking();
            else if(page==2 && encounter>=0 && tries>0){
                if(!battle){if(bush==hiddenBush){battle=true;message="Wild Pokémon #"+w.routePokemon(encounter)+" appeared!";}
                    else{tries--;message=tries==0?"It got away.":"Rustling nearby… try another bush.";}}
                else{hp=Math.max(1,hp-1-random.nextInt(2));tries--;message="Wild Pokémon #"+w.routePokemon(encounter)+" · HP "+hp+" / 4";}
            }else if(page==3 && encounter>=0 && tries>0){
                tries--;if(bush==hiddenBush){message=w.collect(encounter,true)?"Found item #"+w.routeItem(encounter)+"!":"Item bag full (3).";encounter=-1;}
                else message=tries==0?"The item slipped away.":"Try another bush. One chance left.";
            }else if(page==5)connect();
        }catch(Exception e){message="Could not save: "+e.getMessage();}
        view.invalidate();
    }
    private int hiddenBush=random.nextInt(6);
    private void catchPokemon(){
        Walker w=active();if(page!=2||!battle||encounter<0||tries<=0)return;
        try{tries--;if(random.nextInt(4)>=hp-1){message=w.collect(encounter,false)?"Caught Pokémon #"+w.routePokemon(encounter)+"!":"Pokémon slots full (3).";encounter=-1;}
            else message=tries==0?"The Pokémon fled.":"Almost caught it!";}catch(Exception e){message=e.getMessage();}
    }
    @Override public boolean dispatchKeyEvent(KeyEvent e){
        int k=e.getKeyCode(),scan=e.getScanCode();
        boolean left=scan==59||k==KeyEvent.KEYCODE_F1,right=scan==60||k==KeyEvent.KEYCODE_F2;
        boolean bottomLeft=scan==61||k==KeyEvent.KEYCODE_F3,bottomRight=scan==62||k==KeyEvent.KEYCODE_F4;
        boolean use=left||right||bottomLeft||bottomRight||k==4||k==23||k==66||k==82||(k>=19&&k<=22)||(k>=7&&k<=16)||k==17;
        if(!use)return super.dispatchKeyEvent(e);
        if(e.getAction()!=KeyEvent.ACTION_DOWN)return true;
        if(e.getRepeatCount()>0 && !(k>=19&&k<=22))return true;
        if(k==4||bottomRight){back();return true;}
        if(left||k==82){if(page==8&&connecting)stopIr();realMenu.confirm=false;confirmRom=false;page=page==0?1:0;message="";}
        else if(right){if(page==7)toggleLanguage();else if(page==8)selectHardware();else if(page==2)catchPokemon();else{page=5;connect();}}
        else if(bottomLeft){if(page==8)exportHardware();else if(page==7){stopIr();demoMode=!demoMode;message=demoMode?"Demo save is separate from your game save.":"Real walker save selected.";}else page=7;}
        else if(k==17 && demoMode){simulate();}
        else if(page==0 && k>=8&&k<=16){selection=k-8;select();} // menu-9 key
        else if(page==8 && k>=7&&k<=16){
            if(!connecting&&!hardwareDetails&&!realMenu.confirm&&!confirmRom){if(realMenu.mode==0&&k>=8&&k<=13){realMenu.choice=k-8;selectHardware();}else realMenu.digit(k-7);}
        }
        else if(k==23||k==66)select();
        else if(k>=19&&k<=22){int delta=(k==19||k==21)?-1:1;
            if(page==0)selection=(selection+delta+menu.length)%menu.length;
            else if(page==8&&!connecting&&!hardwareDetails&&!realMenu.confirm&&!confirmRom){
                if(k==21||k==22)realMenu.change(delta);else realMenu.move(delta);hardwareChoice=realMenu.choice;
            }
            else if(page==2||page==3)bush=(bush+delta+(page==2?4:6))%(page==2?4:6);
        }
        view.invalidate();return true;
    }
    private final class WalkerView extends View {
        final Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);Canvas c;
        // DS_PALETTE: crisp pixels with brighter dual-screen era colors.
        final int ink=0xff20365b,paper=0xfff6faff,green=0xffb6edcd,red=0xffb23d69;
        final int[] cards={0xffd6f4e5,0xffffdae4,0xffffedb3,0xffe8dcff,0xffcdf2fc,0xffd4e5ff,0xffedddf5,0xffffdfbd};
        final int[] accents={0xff39bd95,0xffe45e79,0xfff0b94e,0xff9478da,0xff37b8d3,0xff6191e0,0xffa98cbf,0xffe29a53};
        WalkerView(){super(WalkerActivity.this);setFocusable(true);setFocusableInTouchMode(true);}
        void text(String s,float x,float y,float size,int color){PixelArt.text(c,p,UiText.tr(s),x,y,size,color);}
        void rect(float x,float y,float w,float h,int color){p.setColor(color);p.setAntiAlias(false);c.drawRect(x,y,x+w,y+h,p);}
        void box(float x,float y,float w,float h,int color){
            rect(x+4,y,w-8,h,ink);rect(x,y+4,w,h-8,ink);rect(x+4,y+4,w-8,h-8,color);
            rect(x+8,y+4,w-16,3,color==ink?0xff72cce0:0xffffffff);
            rect(x+8,y+h-7,w-16,3,color==ink?0xff142a47:0xff93b7cf);
        }
        void lines(String s,float y,int color){
            s=UiText.tr(s);String line="";for(String word:s.split(" ")){if(PixelArt.width(line+word,21)>414){text(line,32,y,21,color);y+=25;line="";}line+=word+" ";}text(line,32,y,21,color);
        }
        void sprite(byte[] bytes,int address,int width,int height,int x,int y,int scale){
            p.setAntiAlias(false);
            for(int row=0;row<height;row++)for(int col=0;col<width;col++){
                int offset=address+(row/8)*width*2+col*2,bit=row%8;
                int shade=((bytes[offset]>>>bit)&1)*2+((bytes[offset+1]>>>bit)&1);
                if(shade!=0){p.setColor(new int[]{green,0xff768961,0xffafbc8e,ink}[shade]);c.drawRect(x+col*scale,y+row*scale,x+(col+1)*scale,y+(row+1)*scale,p);}
            }
        }
        @Override protected void onDraw(Canvas canvas){
            c=canvas;c.save();c.scale(getWidth()/480f,getHeight()/854f);c.drawColor(paper);
            for(int y=96;y<774;y+=12)for(int x=0;x<480;x+=12)if(((x+y)/12)%2==0)rect(x,y,12,12,0xffeaf2fc);
            rect(0,0,480,90,0xffc7e2fc);rect(0,90,480,4,ink);rect(0,94,480,4,0xff79badf);
            for(int i=0;i<8;i++)rect(i*60,90,60,4,accents[i]);
            Walker w=active();String title=page==0?"FLIP WALKER":menu[Math.min(page-1,7)].split(" ·")[0].toUpperCase(Locale.ROOT);
            text(title,28,48,26,ink);text(demoMode?"DEMO · SEPARATE SAVE":"HEARTGOLD / SOULSILVER",28,78,14,red);
            PixelArt.ball(c,p,426,22,3);
            if(page==0){
                for(int i=0;i<menu.length;i++){float y=104+i*60;box(20,y,440,54,i==selection?ink:cards[i%cards.length]);rect(26,y+7,6,40,accents[i%accents.length]); // menu-9 layout
                    text(""+(i+1),36,y+38,18,i==selection?0xffffe28a:accents[i%accents.length]);text(UiText.tr(menu[i]),70,y+38,23,i==selection?paper:ink);PixelArt.icon(c,p,Math.min(i,7),421,(int)y+18);}
                if(w!=null)text(w.steps()+" steps     "+w.watts()+" W",28,690,22,ink);
            }else if(page==1){
                box(24,110,432,350,green);
                c.save();c.clipRect(32,118,448,392);
                for(int y=124;y<380;y+=32)for(int x=36;x<448;x+=32){
                    rect(x+5,y+8,3,9,0xffa5bd82);rect(x+12,y+14,3,8,0xffa5bd82);rect(x+20,y+5,3,8,0xffb6ca8c);
                }
                rect(32,325,416,44,0xffddca8e);rect(32,325,416,4,0xffc4b17a);rect(32,365,416,4,0xffc4b17a);
                for(int x=36;x<448;x+=64)PixelArt.bush(c,p,x,128,4);
                c.restore();
                if(w!=null && w.strolling()){
                    int frame=(int)(SystemClock.uptimeMillis()/650%2);
                    if(demoMode){
                        PixelArt.companion(c,p,180,212,10,frame);
                        text("DEMO COMPANION",151,390,14,ink);
                    }else sprite(w.snapshot(),0x933e+frame*768,64,48,112,150,4);
                    text("Pokémon #"+w.species(),50,425,24,ink);
                }else{lines("Your walking companion will appear here after a game transfer.",245,ink);}
                if(w!=null){text(String.format(UiText.spanish?new Locale("es","ES"):Locale.US,"%,d",w.steps()),30,535,54,ink);text("STEPS TODAY",32,566,16,ink);text(w.watts()+" WATTS",300,537,24,red);}
                lines(demoMode?"OK adds 20 demo steps. No real steps are fabricated.":StepService.sensorStatus,618,ink);
            }else if(page==2||page==3){
                text(page==2?"Find a new friend":"Search for an item",28,132,25,ink);
                int count=page==2?4:6;
                for(int i=0;i<count;i++){int x=32+(i%3)*148,y=190+(i/3)*130;
                    box(x,y,118,100,i==bush?0xffffd16c:green);PixelArt.bush(c,p,x+27,y+15,8);
                    if(i==bush)text(">",x+6,y+61,18,ink);}
                text(tries+" chances left",28,505,23,ink);
                lines(page==2?"OK: approach / attack. F2: throw a Poké Ball.":"Choose with the D-pad, then press OK.",553,ink);
            }else if(page==4){
                text("Collected on this walk",28,140,26,ink);
                if(w!=null){text(w.caughtCount()+" / 3 Pokémon",28,215,30,ink);text(w.itemCount()+" / 3 items",28,275,30,ink);}
                lines("Connect to return your companion and collected Pokémon and items to the game.",350,ink);
            }else if(page==5){
                box(28,115,424,162,green);text(connecting?"CONNECTING…":"INFRARED LINK",48,166,28,ink);
                text("115,200 · bidirectional SIR",48,214,20,ink);
                lines(demoMode?"OK runs an offline game exchange.":connection,325,ink);
                lines("On your RtcPwalker-patched 3DS, open Connect to Pokéwalker. Point the phone's infrared window at the rear IR window of the 3DS.",455,ink);
                lines("Experimental: pairing and returning a Pokémon need real hardware validation.",612,red);
            }else if(page==6){
                text("Trainer card",28,140,28,ink);
                if(w!=null){text(w.paired()?"Paired with a game":"Not paired yet",28,210,25,ink);text("Today: "+w.steps()+" steps",28,267,26,ink);text("Watts: "+w.watts(),28,317,26,ink);}
                lines("Your game supplies the route, Pokémon and graphics over infrared.",405,ink);
            }else if(page==8){
                boolean review=realMenu.confirm||confirmRom;
                text(review?"REVIEW CONNECTION":realMenu.title(),28,132,23,ink);
                if(hardwareDetails&&hardwareIdentity!=null){
                    WalkerReader.Identity id=hardwareIdentity;
                    String[] info={"Trainer: "+id.trainer,"Trainer ID: "+id.trainerId,"Secret ID: "+id.secretId,"Steps today: "+id.steps,"Paired: "+id.paired,"Has Pokemon: "+id.hasPokemon,"Last sync (raw): "+id.lastSync};
                    for(int i=0;i<info.length;i++){box(24,158+i*64,432,54,i%2==0?0xffe1efff:0xffd7f3e7);text(info[i],36,193+i*64,20,ink);}
                    lines("OK or Back returns to connection options.",665,ink);
                }else if(review){
                    box(24,150,432,80,0xffffd8b0);
                    lines(confirmRom?"Read ROM using a temporary RAM payload. No firmware is installed.":"This changes your physical walker. A full backup is saved before changes.",176,ink);
                    if(!confirmRom)for(int i=0;i<realMenu.values().length;i++){
                        text(realMenu.label(i)+": "+realMenu.value(i),28,264+i*32,15,ink);
                    }
                    lines("OK: connect and apply. F4: cancel.",620,red);
                }else{
                    int cursor=realMenu.mode==0?realMenu.choice:realMenu.row;
                    int visible=realMenu.mode==0?6:7,first=Math.max(0,Math.min(cursor-3,realMenu.count()-visible));
                    for(int i=first;i<Math.min(first+visible,realMenu.count());i++){
                        int y=152+(i-first)*57;boolean focus=i==cursor;
                        box(24,y,432,50,focus?0xff2467be:realMenu.mode==0?cards[(i+2)%cards.length]:0xffe1efff);
                        text((realMenu.mode==0?(i+1)+" ":"")+realMenu.label(i),36,y+20,15,focus?paper:ink);
                        if(realMenu.mode!=0)text(realMenu.value(i),36,y+41,15,focus?0xffffe78c:ink);
                    }
                    if(realMenu.mode!=0){text(realMenu.editing?"ENTER VALUE / ID: "+(realMenu.digits.isEmpty()?"...":realMenu.digits)+" · OK DONE":(realMenu.row+1)+" / "+realMenu.count()+"  < > CHANGE · DIGITS: ID",28,573,15,red);}
                    String status=connecting?connection:realMenu.mode==0?connection:"UP/DOWN selects. LEFT/RIGHT adjusts. Number keys enter a value or catalog ID. 0 today steps keeps today's count.";
                    status=UiText.tr(status);
                    lines(status.length()>120?status.substring(0,117)+"...":status,609,ink);
                    if(realMenu.mode==0&&hardwareIdentity!=null)text("ID "+hardwareIdentity.trainerId+" · "+hardwareIdentity.trainer+" · "+hardwareIdentity.steps+" steps",28,713,15,ink);
                    if(realMenu.mode==0)text(realMenu.choice==5?(hardwareRom==null?"No ROM capture":"48 KiB ROM available"):(hardwareSnapshot==null?"No backup":"64 KiB backup available"),28,743,15,red);
                }
            }else{
                text(demoMode?"Demo mode":"Real walker save",28,140,29,ink);
                text("Language: "+(UiText.spanish?"Español (España)":"English"),28,175,17,red);
                lines("F3 switches real / demo saves. In demo mode, * simulates receiving a Pokémon. OK on Walk adds 20 demo steps.",200,ink);
                lines("F1: menu / walk. F2: infrared / catch. F3: settings. F4 or Clear: back. D-pad: choose. OK: select. Number keys: menu shortcuts.",358,ink);
                lines("Walking counts only with a real step-counter sensor. Start or pause with OK on Walk. Root is requested only for an infrared connection.",515,ink);
            }
            if(!message.isEmpty()) {box(18,666,444,90,green);lines(message,695,ink);}
            // Two app-owned rows match the phone's four corner keys and central OK.
            box(0,774,480,80,ink);
            SoftKeyBar.draw(c,p,
                    page==0?"F1  Walk":"F1  Menu",
                    page==7?"F2  Language":page==2?"F2  Catch":connecting?"F2  Stop":page==8?(realMenu.confirm||confirmRom?"F2  Apply":"F2  Select"):"F2  Connect",
                    page==7?"F3  Mode":page==8?"F3  Export":"F3  Settings",
                    "F4  Back",
                    page==8?(connecting?"OK Stop":realMenu.confirm||confirmRom?"OK Apply":"OK Select"):page==5?"OK Link":page==1&&StepService.running?"OK Pause":page==1?"OK Walk":"OK Select");
            c.restore();
            setContentDescription(localizedDescription(title,w));
        }
    }
}
