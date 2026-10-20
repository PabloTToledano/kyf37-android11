#!/usr/bin/env python3
"""Rerunnable generation of pwalkerHax catalogs/payloads and original name bitmaps."""
from pathlib import Path
import re,json
r=Path(__file__).resolve().parents[2];out=r/'templates/src/org/kyf37/walker';src=(r/'references/pwalkerHax/include/pokewalker.h').read_text()
s='package org.kyf37.walker;\n/** Derived from pwalkerHax bed237a; GPL-3.0. See THIRD_PARTY.md. */\nfinal class WalkerCatalog {\n'
for name in ['item','poke','move','ability']:
 block=re.search(r'static const char \*'+name+r'_list\[\] = \{(.*?)\};',src,re.S).group(1)
 values=re.findall(r'"(?:[^"\\]|\\.)*"',block)
 s+='static final String[] '+name.upper()+'={'+','.join(values)+'};\n'
for name in ['add_watts','write_todaysteps_to_eeprom','write_totalsteps_to_eeprom','rom_dump','trigger_exploit']:
 block=re.search(r'static (?:const )?u8 '+name+r'(?:_payload)?\[\] = \{(.*?)\};',src,re.S).group(1)
 block=re.sub(r'//[^\n]*','',block)
 vals=re.findall(r'0x[0-9a-fA-F]+',block)
 s+='static final byte[] '+name.upper()+'={'+','.join('(byte)'+v for v in vals)+'};\n'
s+='}\n';(out/'WalkerCatalog.java').write_text(s)
# Reuse our original glyphs, not the reference game's font.
pixel=(out/'PixelArt.java').read_text();data=pixel[pixel.index('String[] data={')+len('String[] data={'):pixel.index('};',pixel.index('String[] data={'))]
(out/'GiftBitmap.java').write_text('''package org.kyf37.walker;
import java.util.*;
import java.text.Normalizer;
/** Original 5x7 glyphs in the walker's column/two-plane 2bpp format. */
final class GiftBitmap {
 static byte[] name(String name,int width){
  String[] data={'''+data+'''};
  HashMap<Character,String[]> font=new HashMap<>();for(String e:data)font.put(e.charAt(0),e.substring(2).split("/"));
  name=Normalizer.normalize(name,Normalizer.Form.NFC).toUpperCase(Locale.ROOT);
  byte[] b=new byte[width*4];int advance=name.length()*6+2>width?5:6;
  for(int i=0;i<name.length();i++){if(name.charAt(i)==' ')continue;String[] g=font.get(name.charAt(i));if(g==null)g=font.get('?');
   for(int y=0;y<7;y++)for(int x=0;x<5;x++)if(g[y].charAt(x)=='1'){
    int col=2+i*advance+x;if(col>=width)continue;int row=y+4,at=(row/8)*width*2+col*2;
    b[at]|=(byte)(1<<(row%8));b[at+1]|=(byte)(1<<(row%8));
   }
  }return b;
 }
}
''')
