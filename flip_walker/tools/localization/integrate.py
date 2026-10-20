#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];p=r/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
if '// TWO_LANGUAGES' not in s:
 s=s.replace('super.onCreate(state);','''super.onCreate(state);
        // TWO_LANGUAGES: preference affects UI only, never game/save bytes.
        UiText.choose(getSharedPreferences("ui",0).getString("language",UiText.defaultLanguage(Locale.getDefault().toLanguageTag())));''')
 at=s.index('    private Walker active()')
 s=s[:at]+'''    private void toggleLanguage(){
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
''' +s[at:]
 s=s.replace('else if(right){if(page==8)', 'else if(right){if(page==7)toggleLanguage();else if(page==8)')
 s=s.replace('PixelArt.text(c,p,s,x,y,size,color);','PixelArt.text(c,p,UiText.tr(s),x,y,size,color);')
 s=s.replace('String line="";for(String word:s.split(" "))','s=UiText.tr(s);String line="";for(String word:s.split(" "))')
 s=s.replace('String.format(Locale.ROOT,"%,d",w.steps())','String.format(UiText.spanish?new Locale("es","ES"):Locale.US,"%,d",w.steps())')
 s=s.replace('lines(status.length()>120?', 'status=UiText.tr(status);\n                    lines(status.length()>120?')
 s=s.replace('text(demoMode?"Demo mode":"Real walker save",28,140,29,ink);','text(demoMode?"Demo mode":"Real walker save",28,140,29,ink);\n                text("Language: "+(UiText.spanish?"Español (España)":"English"),28,175,17,red);')
 s=s.replace('text(page==2?"F2  Catch":','text(page==7?"F2  Language":page==2?"F2  Catch":')
 start=s.index('            setContentDescription(');end=s.index('\n',start)
 s=s[:start]+'            setContentDescription(localizedDescription(title,w));'+s[end:]
 p.write_text(s)
p=r/'templates/src/org/kyf37/walker/RealMenu.java';s=p.read_text()
if 'UiText.catalog' not in s:
 s=s.replace('return v+" "+c[v];','return v+" "+UiText.catalog(c,v);')
 s=s.replace('StringBuilder b=new StringBuilder(title())','StringBuilder b=new StringBuilder(UiText.tr(title()))')
 s=s.replace('append(OPTIONS[choice])','append(UiText.tr(OPTIONS[choice]))')
 s=s.replace('append(label(i)).append(": ").append(value(i))','append(UiText.tr(label(i))).append(": ").append(UiText.tr(value(i)))')
 s=s.replace('b.append(confirm?". Confirm changes. OK applies; Back cancels.":". D-pad chooses; left/right changes; digits enter ID or value; OK edits.")','b.append(". ").append(UiText.tr(confirm?"Confirm changes. OK applies; Back cancels.":"D-pad chooses; left/right changes; digits enter ID or value; OK edits."))')
 p.write_text(s)
p=r/'templates/src/org/kyf37/walker/StepService.java';s=p.read_text()
if 'static void refreshLanguage' not in s:
 start=s.index('        NotificationManager manager=');end=s.index('        try{walker=',start)
 s=s[:start]+'''        UiText.choose(getSharedPreferences("ui",0).getString("language",UiText.defaultLanguage(java.util.Locale.getDefault().toLanguageTag())));
        startForeground(37,notification(this));
''' +s[end:]
 at=s.index('    @Override public int onStartCommand')
 s=s[:at]+'''    private static Notification notification(Context c){
        NotificationManager manager=(NotificationManager)c.getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel("walk",UiText.tr("Walking steps"),NotificationManager.IMPORTANCE_LOW));
        PendingIntent open=PendingIntent.getActivity(c,0,new Intent(c,WalkerActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(c,"walk").setSmallIcon(R.drawable.ic_walker).setContentTitle(UiText.tr("Flip Walker is counting steps"))
                .setContentText(UiText.tr("Open Flip Walker to pause")).setContentIntent(open).setOngoing(true).build();
    }
    static void refreshLanguage(Context c){if(running)((NotificationManager)c.getSystemService(NOTIFICATION_SERVICE)).notify(37,notification(c));}
''' +s[at:];p.write_text(s)
p=r/'templates/src/org/kyf37/walker/PixelArt.java';s=p.read_text()
if '"Ñ:' not in s:
 s=s.replace('"A:01110', '''"Ñ:01010/10100/10001/11001/10101/10011/10001",
            "Á:00100/00010/01110/10001/11111/10001/10001",
            "É:00010/00100/11111/10000/11110/10000/11111",
            "Í:00010/00100/11111/00100/00100/00100/11111",
            "Ó:00010/00100/01110/10001/10001/10001/01110",
            "Ú:00010/00100/10001/10001/10001/10001/01110",
            "Ü:01010/00000/10001/10001/10001/10001/01110",
            "¿:00100/00000/00100/01000/10000/10001/01110",
            "¡:00100/00000/00100/00100/00100/00100/00100",
            "A:01110''')
 s=s.replace('Normalizer.Form.NFD).replaceAll("\\\\p{M}","")','Normalizer.Form.NFC)')
 p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('versionCode="3"','versionCode="4"').replace('0.3-ds-tools','0.4-es-ES');p.write_text(s)
p=r/'tools/test-host.sh';s=p.read_text()
if 'LocaleTest.java' not in s:
 s=s.replace('"$ROOT/tests/ToolsTest.java"','"$ROOT/tests/ToolsTest.java" "$ROOT/templates/src/org/kyf37/walker/UiText.java" "$ROOT/tests/LocaleTest.java"')
 s=s.replace('cc -Wall','"$JAVA/java" -cp "$ROOT/build/tests" org.kyf37.walker.LocaleTest\ncc -Wall');p.write_text(s)

p=r/'templates/src/org/kyf37/walker/WalkerActivity.java'
s=p.read_text().replace('UiText.tr(w.watts()+" WATTS")','UiText.tr(w.watts()+" watts")')
p.write_text(s)
p=r/'templates/src/org/kyf37/walker/WalkerTools.java';s=p.read_text()
s=s.replace('range(item,1,WalkerCatalog.ITEM.length-1);\n  try{','range(item,1,WalkerCatalog.ITEM.length-1);\n  final String giftName=UiText.catalog(WalkerCatalog.ITEM,item);\n  try{')
s=s.replace('GiftBitmap.name(WalkerCatalog.ITEM[item],96)','GiftBitmap.name(giftName,96)')
p.write_text(s)
