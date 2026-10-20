#!/usr/bin/env python3
"""Idempotent additive UI integration into the rerunnable template source."""
from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'templates/src/org/kyf37/walker/WalkerActivity.java'
s=p.read_text()
if 'private void readHardware(' in s:raise SystemExit('Real-device reader already integrated')
s=s.replace('private volatile IrSession ir;', 'private ReaderFiles readerFiles;private volatile WalkerReader.Identity hardwareIdentity;\n    private volatile byte[] hardwareSnapshot;private int hardwareChoice;\n    private volatile IrSession ir;')
s=s.replace('Infrared has not been hardware tested','Ready; real-game sync is still unverified')
s=s.replace('"Settings & help"};','"Settings & help","Read real walker"};')
s=s.replace('demo=new Walker(null,bytes->{});view=', '''try{readerFiles=new ReaderFiles(this);hardwareIdentity=readerFiles.identity();hardwareSnapshot=readerFiles.latest();}
        catch(Exception e){message="Previous readback could not be loaded; files preserved.";connection=message;}
        demo=new Walker(null,bytes->{});view=''')
anchor='    /** Disposable game fixture; never reads or changes the real walker save. */'
methods='''    private void readHardware(boolean fullBackup){
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
                readerFiles.identity(result.identity);hardwareIdentity=result.identity;
                connection=fullBackup?"Full 64 KiB backup saved separately. F3 exports it.":"Trainer data received. The app's walking save was not replaced.";
            }catch(Exception e){connection=cancelled?"Read cancelled; previous captures preserved.":e.getMessage()==null?"Device read failed":e.getMessage();}
            finally{ir=null;connecting=false;ui.post(()->{getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);if(view!=null)view.invalidate();});}
        });
    }
    private void exportHardware(){
        if(connecting){message="Finish or cancel the read before exporting.";return;}
        if(hardwareSnapshot==null){message="Read a full backup first.";return;}
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/octet-stream").putExtra(Intent.EXTRA_TITLE,"pokewalker-eeprom.bin");
        try{startActivityForResult(intent,83);}catch(ActivityNotFoundException e){message="No file picker installed. Private backup retained.";}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=83||result!=RESULT_OK||data==null||data.getData()==null||hardwareSnapshot==null)return;
        final byte[] backup=hardwareSnapshot.clone();final android.net.Uri uri=data.getData();
        worker.execute(()->{
            try(java.io.OutputStream out=getContentResolver().openOutputStream(uri,"w")){
                if(out==null)throw new java.io.IOException("Destination unavailable");out.write(backup);out.flush();
                ui.post(()->{message="64 KiB backup exported.";if(view!=null)view.invalidate();});
            }catch(Exception e){ui.post(()->{message="Export failed; private backup retained.";if(view!=null)view.invalidate();});}
        });
    }
'''
assert anchor in s;s=s.replace(anchor,methods+anchor)
s=s.replace('Walker w=active();if(w==null)return;\n        try{','''if(page==8 || (page==0 && selection==7)){
            if(page==0){page=8;message="";}else readHardware(hardwareChoice==1);
            view.invalidate();return;
        }
        Walker w=active();if(w==null)return;
        try{''',1)
s=s.replace('(k>=8&&k<=14)','(k>=8&&k<=15)')
s=s.replace('if(left||k==82){page=', 'if(left||k==82){if(page==8&&connecting)stopIr();page=')
s=s.replace('else if(right){if(page==2)', 'else if(right){if(page==8)readHardware(hardwareChoice==1);else if(page==2)')
s=s.replace('else if(bottomLeft){if(page==7)', 'else if(bottomLeft){if(page==8)exportHardware();else if(page==7)')
s=s.replace('else if(page==0 && k>=8&&k<=14)', 'else if(page==0 && k>=8&&k<=15)')
s=s.replace('else if(k==23||k==66)select();','else if(page==8 && (k==8||k==9)){hardwareChoice=k-8;readHardware(hardwareChoice==1);}\n        else if(k==23||k==66)select();')
s=s.replace('else if(page==2||page==3)bush=', 'else if(page==8)hardwareChoice=(hardwareChoice+1)%2;\n            else if(page==2||page==3)bush=')
s=s.replace('Math.min(page-1,6)','Math.min(page-1,7)')
s=s.replace('108+i*76','108+i*66').replace('440,66,ink','440,58,ink')
anchor='''            }else{
                text(demoMode?"Demo mode":"Real walker save"'''
new='''            }else if(page==8){
                for(int i=0;i<2;i++){
                    int y=118+i*72;box(24,y,432,60,i==hardwareChoice?ink:green);
                    text((i+1)+" "+(i==0?"Read trainer & steps":"Back up all data"),40,y+38,22,i==hardwareChoice?paper:ink);
                }
                String status=connection.length()>115?connection.substring(0,112)+"...":connection;
                lines(status,302,ink);
                WalkerReader.Identity id=hardwareIdentity;
                if(id!=null){
                    text("Trainer: "+id.trainer,28,414,24,ink);
                    text(String.format(Locale.ROOT,"ID %05d",id.trainerId),28,450,23,ink);
                    text("Steps: "+id.steps,28,488,26,ink);
                    text((id.paired?"Paired":"Unpaired")+" / "+(id.hasPokemon?"Has Pokemon":"No Pokemon"),28,525,20,ink);
                }
                byte[] capture=hardwareSnapshot;
                if(capture!=null){
                    text("Backup: 64 KiB / "+WalkerReader.be16(capture,0x164)+" watts",28,565,20,ink);
                    text("Total: "+WalkerReader.be32(capture,0x156)+" steps",28,600,20,ink);
                }
                lines("Choose CONNECT on the real Pokewalker and point its IR window at this phone. Reads do not replace your app save.",638,ink);
            }else{
                text(demoMode?"Demo mode":"Real walker save"'''
assert anchor in s;s=s.replace(anchor,new)
s=s.replace('page==2?"F2  Catch":connecting?"F2  Stop":"F2  Connect"','page==2?"F2  Catch":connecting?"F2  Stop":page==8?"F2  Read":"F2  Connect"')
s=s.replace('page==7?"F3  Mode":"F3  Settings"','page==7?"F3  Mode":page==8?"F3  Export":"F3  Settings"')
s=s.replace('page==5?"OK Link":','page==8?(connecting?"OK Stop":"OK Read"):page==5?"OK Link":')
s=s.replace('". "+connection+". "+(w==null?', '". "+connection+". "+(page==8?"Read-only real device. "+(hardwareChoice==0?"Read trainer & steps":"Back up all data")+". "+(hardwareIdentity==null?"No capture":hardwareIdentity.trainer+". Trainer ID "+hardwareIdentity.trainerId+". Device steps "+hardwareIdentity.steps)+". "+(hardwareSnapshot==null?"No backup":"64 KiB backup available")+". ":"")+(w==null?')
p.write_text(s)
p=r/'templates/src/org/kyf37/walker/IrSession.java';p.write_text(p.read_text().replace('implements AutoCloseable','implements AutoCloseable, WalkerReader.Link'))
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('android:versionCode="1" android:versionName="0.1-offline"','android:versionCode="2" android:versionName="0.2-real-reader"');p.write_text(s)
print('Real reader UI added; existing seven functions and shortcuts retained')
