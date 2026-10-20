#!/usr/bin/env python3
"""Rerunnable: full emulation becomes main-menu item 9 of Flip Walker (no separate launcher icon)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'templates'
def patch(rel, old, new, tag):
    p = root / rel; t = p.read_text()
    if tag in t: return
    assert old in t, f'{rel}: anchor for {tag}'
    p.write_text(t.replace(old, new, 1)); print('applied', tag)
W = 'src/org/kyf37/walker/WalkerActivity.java'
patch(W, '"Settings & help","Real Pokewalker"};', '"Settings & help","Real Pokewalker","Emulated Pokewalker"}; // menu-9: emulated', 'menu-9: emulated')
# key 9 selects item 9
patch(W, 'else if(page==0 && k>=8&&k<=15){selection=k-8;select();}', 'else if(page==0 && k>=8&&k<=16){selection=k-8;select();} // menu-9 key', 'menu-9 key')
# item 9 opens the emulator screen
patch(W, '''    private void select(){
        if(page==8 || (page==0 && selection==7)){''', '''    private void select(){
        if(page==0 && selection==8){stopIr();startActivity(new android.content.Intent(this,EmulatedWalkerActivity.class));return;} // menu-9 open
        if(page==8 || (page==0 && selection==7)){''', 'menu-9 open')
# nine cards fit above the step line: 58 px pitch, colours/icons wrap
patch(W, '''for(int i=0;i<menu.length;i++){float y=108+i*66;box(20,y,440,58,i==selection?ink:cards[i]);rect(26,y+8,6,42,accents[i]);
                    text(""+(i+1),36,y+42,18,i==selection?0xffffe28a:accents[i]);text(menu[i],70,y+42,23,i==selection?paper:ink);PixelArt.icon(c,p,i,421,(int)y+21);}''',
'''for(int i=0;i<menu.length;i++){float y=104+i*60;box(20,y,440,54,i==selection?ink:cards[i%cards.length]);rect(26,y+7,6,40,accents[i%accents.length]); // menu-9 layout
                    text(""+(i+1),36,y+38,18,i==selection?0xffffe28a:accents[i%accents.length]);text(UiText.tr(menu[i]),70,y+38,23,i==selection?paper:ink);PixelArt.icon(c,p,Math.min(i,7),421,(int)y+18);}''',
'menu-9 layout')
patch('src/org/kyf37/walker/UiText.java', 'UI.put("Real Pokewalker","Pokéwalker real");',
      'UI.put("Real Pokewalker","Pokéwalker real");\nUI.put("Emulated Pokewalker","Pokéwalker emulado");', 'Pokéwalker emulado')
# the emulator is reached from the menu only
m = root / 'AndroidManifest.xml'; t = m.read_text()
launcher = '<intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity>\n    <service android:name=".StepService"'
if 'android:name=".EmulatedWalkerActivity"' in t and launcher in t:
    t = t.replace(launcher, '</activity>\n    <service android:name=".StepService"', 1)
    t = t.replace('android:launchMode="singleTask" android:screenOrientation="portrait" android:exported="true"', 'android:launchMode="singleTask" android:screenOrientation="portrait" android:exported="false"', 1)
    m.write_text(t); print('applied emulator launcher removal')

# emulator-ui-es: Spanish (Spain) strings for the emulator screen
patch('src/org/kyf37/walker/UiText.java', 'UI.put("Emulated Pokewalker","Pokéwalker emulado");', '''UI.put("Emulated Pokewalker","Pokéwalker emulado"); // emulator-ui-es
UI.put("Real firmware · your ROM","Firmware real · tu ROM");UI.put("F2  Help","F2  Ayuda");UI.put("F3  Save","F3  Guardar");UI.put("OK Button","OK Botón");
UI.put("IR open","IR abierto");UI.put("IR idle","IR inactivo");UI.put("IR failed","IR con error");UI.put("IR opening…","Abriendo IR…");UI.put("Saved","Guardado");
UI.put("Not registered yet - send from the game","Sin registrar: envía desde el juego");
UI.put("In the game open the Pokewalker","En el juego abre el envío al");UI.put("transfer and wait until it searches.","Pokéwalker y espera a que busque.");
UI.put("Press OK here, then hold the IR","Pulsa OK aquí y acerca las");UI.put("windows 5-10 cm apart, facing.","ventanas IR a 5-10 cm, de frente.");
UI.put("Left / OK / Right are the walker","Izquierda / OK / Derecha son los");UI.put("buttons. Progress saves itself.","botones. Se guarda solo.");''', 'emulator-ui-es')

# emulator-ui-es2
patch('src/org/kyf37/walker/UiText.java', 'UI.put("Saved","Guardado");', 'UI.put("Saved","Guardado"); // emulator-ui-es2\nUI.put("Sent","Enviados");UI.put("Received","Recibidos");UI.put("In Flip Walker menus","En los menús de Flip Walker");', 'emulator-ui-es2')

# emulator-ui-es3
patch('src/org/kyf37/walker/UiText.java', 'UI.put("Sent","Enviados");', 'UI.put("Sent","Enviados"); // emulator-ui-es3\nUI.put("steps","pasos");UI.put("Today","Hoy");UI.put("Walker busy, try again","Walker ocupado, prueba otra vez");', 'emulator-ui-es3')
