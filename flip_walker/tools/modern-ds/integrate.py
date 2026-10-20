#!/usr/bin/env python3
"""Idempotent integration. Source templates are staged by tools/stage.py."""
from pathlib import Path
r=Path(__file__).resolve().parents[2];p=r/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
if 'private final RealMenu realMenu' not in s:
 s=s.replace('private volatile byte[] hardwareSnapshot;private int hardwareChoice;','private volatile byte[] hardwareSnapshot,hardwareRom;private int hardwareChoice;\n    private final RealMenu realMenu=new RealMenu();private boolean confirmRom;private boolean exportingRom;')
 s=s.replace('"Read real walker"','"Real Pokewalker"')
 s=s.replace('hardwareSnapshot=readerFiles.latest();','hardwareSnapshot=readerFiles.latest();hardwareRom=readerFiles.latestRom();')
 s=s.replace('private void back(){if(connecting)stopIr();','private void back(){if(page==8&&!connecting){if(realMenu.confirm||confirmRom){realMenu.confirm=false;confirmRom=false;view.invalidate();return;}if(realMenu.mode!=0){realMenu.mode=0;realMenu.row=0;view.invalidate();return;}}if(connecting)stopIr();')
 start=s.index('    private void exportHardware()')
 s=s[:start]+'''    private void selectHardware(){
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
''' +s[start:]
 s=s.replace('if(hardwareSnapshot==null){message="Read a full backup first.";return;}','exportingRom=realMenu.mode==0&&realMenu.choice==5;\n        if((exportingRom?hardwareRom:hardwareSnapshot)==null){message=exportingRom?"Dump the ROM first.":"Read a full backup first.";return;}')
 s=s.replace('"pokewalker-eeprom.bin");','exportingRom?"pokewalker-rom.bin":"pokewalker-eeprom.bin");')
 s=s.replace('||hardwareSnapshot==null)return;','||(exportingRom?hardwareRom:hardwareSnapshot)==null)return;')
 s=s.replace('final byte[] backup=hardwareSnapshot.clone();','final byte[] backup=(exportingRom?hardwareRom:hardwareSnapshot).clone();')
 s=s.replace('message="64 KiB backup exported."','message=backup.length==49152?"48 KiB ROM exported.":"64 KiB backup exported."')
 s=s.replace('else readHardware(hardwareChoice==1);','else selectHardware();')
 s=s.replace('if(page==8)readHardware(hardwareChoice==1);','if(page==8)selectHardware();')
 s=s.replace('(k>=8&&k<=15)||k==17','(k>=7&&k<=16)||k==17')
 s=s.replace('else if(page==8 && (k==8||k==9)){hardwareChoice=k-8;readHardware(hardwareChoice==1);}', '''else if(page==8 && k>=7&&k<=16){
            if(!connecting&&!realMenu.confirm&&!confirmRom){if(realMenu.mode==0&&k>=8&&k<=13){realMenu.choice=k-8;selectHardware();}else realMenu.digit(k-7);}
        }''')
 s=s.replace('else if(page==8)hardwareChoice=(hardwareChoice+1)%2;', '''else if(page==8&&!connecting&&!realMenu.confirm&&!confirmRom){
                if(k==21||k==22)realMenu.change(delta);else realMenu.move(delta);hardwareChoice=realMenu.choice;
            }''')
 start=s.index('            }else if(page==8){',s.index('@Override protected void onDraw'))
 end=s.index('            }else{',start)
 s=s[:start]+'''            }else if(page==8){
                boolean review=realMenu.confirm||confirmRom;
                text(review?"REVIEW CONNECTION":realMenu.title(),28,132,23,ink);
                if(review){
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
                        box(24,y,432,50,focus?0xff2467be:0xffe1efff);
                        text((realMenu.mode==0?(i+1)+" ":"")+realMenu.label(i),36,y+20,15,focus?paper:ink);
                        if(realMenu.mode!=0)text(realMenu.value(i),36,y+41,15,focus?0xffffe78c:ink);
                    }
                    if(realMenu.mode!=0){text((realMenu.row+1)+" / "+realMenu.count()+"  < > CHANGE · DIGITS: ID",28,573,15,red);}
                    String status=connecting?connection:realMenu.mode==0?connection:"UP/DOWN selects. LEFT/RIGHT adjusts. Number keys enter a value or catalog ID. 0 today steps keeps today's count.";
                    lines(status.length()>120?status.substring(0,117)+"...":status,609,ink);
                    if(realMenu.mode==0&&hardwareIdentity!=null)text("ID "+hardwareIdentity.trainerId+" · "+hardwareIdentity.trainer+" · "+hardwareIdentity.steps+" steps",28,713,15,ink);
                    if(realMenu.mode==0)text(realMenu.choice==5?(hardwareRom==null?"No ROM capture":"48 KiB ROM available"):(hardwareSnapshot==null?"No backup":"64 KiB backup available"),28,743,15,red);
                }
''' +s[end:]
 s=s.replace('page==8?"F2  Read"','page==8?"F2  Select"').replace('"OK Stop":"OK Read"','"OK Stop":realMenu.confirm||confirmRom?"OK Apply":"OK Select"')
 old='"Read-only real device. "+(hardwareChoice==0?"Read trainer & steps":"Back up all data")'
 s=s.replace(old,'realMenu.description()+". "+(confirmRom?"Confirm ROM dump. Temporary RAM payload. OK connects; Back cancels.":"")')
 p.write_text(s)
# color design across all original screens
s=p.read_text()
if 'DS_PALETTE' not in s:
 s=s.replace('final int ink=0xff34434b,paper=0xfff7f0d3,green=0xffc6d9a0,red=0xffab653f;','// DS_PALETTE: crisp pixels with brighter dual-screen era colors.\n        final int ink=0xff20365b,paper=0xfff6faff,green=0xffb6edcd,red=0xffb23d69;\n        final int[] accents={0xff39bd95,0xffe45e79,0xfff0b94e,0xff9478da,0xff37b8d3,0xff6191e0,0xffa98cbf,0xffe29a53};')
 s=s.replace('0xfff2eacb','0xffeaf2fc').replace('0xffe5dfb9','0xffc7e2fc').replace('0xffb5a26e','0xff79badf')
 s=s.replace('color==ink?0xffd2ba74:0xffe9edc7','color==ink?0xff72cce0:0xffffffff').replace('color==ink?0xff657a76:0xffa5b58b','color==ink?0xff142a47:0xff93b7cf')
 s=s.replace('float y=108+i*66;if(i==selection)box(20,y,440,58,ink);','float y=108+i*66;box(20,y,440,58,i==selection?ink:0xffffffff);rect(26,y+8,6,42,accents[i]);')
 s=s.replace('i==selection?green:red','i==selection?0xffffe28a:accents[i]')
 s=s.replace('rect(0,94,480,4,0xff79badf);','rect(0,94,480,4,0xff79badf);\n            for(int i=0;i<8;i++)rect(i*60,90,60,4,accents[i]);')
 s=s.replace('0xffe1c278','0xffffd16c')
 p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('versionCode="2"','versionCode="3"').replace('0.2-real-reader','0.3-ds-tools');p.write_text(s)
p=r/'templates/src/org/kyf37/walker/ReaderFiles.java';s=p.read_text()
if 'latestRom()' not in s:
 s=s.replace('if(snapshot.length!=65536)throw new IOException("Incomplete EEPROM read; not saved");','return saveCapture(snapshot,65536,"pokewalker-");\n    }\n    public String saveRom(byte[] snapshot)throws IOException {return saveCapture(snapshot,49152,"rom-");}\n    private String saveCapture(byte[] snapshot,int size,String prefix)throws IOException {\n        if(snapshot.length!=size)throw new IOException("Incomplete capture; not saved");')
 s=s.replace('String name="pokewalker-"','String name=prefix')
 s=s.replace('public byte[] latest()throws IOException{','public byte[] latest()throws IOException{return latestCapture("pokewalker-",65536);}\n    public byte[] latestRom()throws IOException{return latestCapture("rom-",49152);}\n    private byte[] latestCapture(String prefix,int size)throws IOException{')
 s=s.replace('name.startsWith("pokewalker-")','name.startsWith(prefix)').replace('readExact(in,65536)','readExact(in,size)');p.write_text(s)
p=r/'tools/test-host.sh'
p.write_text(r'''#!/usr/bin/env bash
set -euo pipefail
flock -n 9 || { echo 'Mandatory build lock missing'; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd)
JAVA="$ROOT/../native/kyf37-android11/prebuilts/jdk/jdk11/linux-x86/bin"
mkdir -p "$ROOT/build/tests"
"$JAVA/javac" -d "$ROOT/build/tests" "$ROOT/templates/src/org/kyf37/walker/Packet.java" "$ROOT/templates/src/org/kyf37/walker/Walker.java" "$ROOT/tests/ProtocolTest.java" "$ROOT/templates/src/org/kyf37/walker/WalkerReader.java" "$ROOT/tests/ReaderTest.java" "$ROOT/templates/src/org/kyf37/walker/WalkerCatalog.java" "$ROOT/templates/src/org/kyf37/walker/GiftBitmap.java" "$ROOT/templates/src/org/kyf37/walker/WalkerTools.java" "$ROOT/templates/src/org/kyf37/walker/RealMenu.java" "$ROOT/tests/ToolsTest.java"
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ProtocolTest
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ReaderTest
"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.ToolsTest
cc -Wall -Wextra -Werror -O2 "$ROOT/native/walker_ir.c" -o "$ROOT/build/tests/walker-ir-host"
"$ROOT/build/tests/walker-ir-host" --self-test
''')
