#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];p=r/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
if 'final int[] cards=' not in s:
 s=s.replace('final int[] accents=', 'final int[] cards={0xffd6f4e5,0xffffdae4,0xffffedb3,0xffe8dcff,0xffcdf2fc,0xffd4e5ff,0xffedddf5,0xffffdfbd};\n        final int[] accents=')
 s=s.replace('i==selection?ink:0xffffffff','i==selection?ink:cards[i]')
 s=s.replace('focus?0xff2467be:0xffe1efff','focus?0xff2467be:realMenu.mode==0?cards[(i+2)%cards.length]:0xffe1efff')
 p.write_text(s)
p=r/'templates/src/org/kyf37/walker/PixelArt.java';s=p.read_text()
if 'REAL_DEVICE_ICON' not in s:
 s=s.replace('static void icon(Canvas c,Paint p,int type,int x,int y){','''static void icon(Canvas c,Paint p,int type,int x,int y){
        // REAL_DEVICE_ICON: original walker silhouette with colored IR indicator.
        if(type==7){tile(c,p,new String[]{"00111100","01233210","12333321","12333321","12222221","12122121","01222210","00111100"},x,y,3,new int[]{0,0xff20365b,0xffe29a53,0xff87d6ef});return;}''')
 p.write_text(s)
