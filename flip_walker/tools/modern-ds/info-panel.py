#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
if 'private boolean hardwareDetails' not in s:
 s=s.replace('private final RealMenu realMenu','private boolean hardwareDetails;\n    private final RealMenu realMenu')
 s=s.replace('if(page==8&&!connecting){','if(page==8&&!connecting){if(hardwareDetails){hardwareDetails=false;view.invalidate();return;}')
 s=s.replace('readerFiles.identity(result.identity);hardwareIdentity=result.identity;','readerFiles.identity(result.identity);hardwareIdentity=result.identity;if(!fullBackup)ui.post(()->hardwareDetails=true);')
 s=s.replace('private void selectHardware(){','private void selectHardware(){\n        if(hardwareDetails){hardwareDetails=false;return;}')
 s=s.replace('if(!connecting&&!realMenu.confirm&&!confirmRom){','if(!connecting&&!hardwareDetails&&!realMenu.confirm&&!confirmRom){')
 s=s.replace('page==8&&!connecting&&!realMenu.confirm&&!confirmRom','page==8&&!connecting&&!hardwareDetails&&!realMenu.confirm&&!confirmRom')
 s=s.replace('if(review){\n                    box','if(hardwareDetails&&hardwareIdentity!=null){\n                    WalkerReader.Identity id=hardwareIdentity;\n                    String[] info={"Trainer: "+id.trainer,"Trainer ID: "+id.trainerId,"Secret ID: "+id.secretId,"Steps today: "+id.steps,"Paired: "+id.paired,"Has Pokemon: "+id.hasPokemon,"Last sync (raw): "+id.lastSync};\n                    for(int i=0;i<info.length;i++){box(24,158+i*64,432,54,i%2==0?0xffe1efff:0xffd7f3e7);text(info[i],36,193+i*64,20,ink);}\n                    lines("OK or Back returns to connection options.",665,ink);\n                }else if(review){\n                    box')
 s=s.replace('". Device steps "+hardwareIdentity.steps','". Device steps "+hardwareIdentity.steps+". Secret ID "+hardwareIdentity.secretId+". Paired "+hardwareIdentity.paired+". Has Pokemon "+hardwareIdentity.hasPokemon+". Last sync "+hardwareIdentity.lastSync')
 p.write_text(s)

s=p.read_text()
s=s.replace('ui.removeCallbacks(refresh);stopIr();super.onPause();','ui.removeCallbacks(refresh);stopIr();realMenu.confirm=false;confirmRom=false;super.onPause();')
s=s.replace('if(page==8&&connecting)stopIr();page=page==0?1:0;', 'if(page==8&&connecting)stopIr();realMenu.confirm=false;confirmRom=false;page=page==0?1:0;')
p.write_text(s)
