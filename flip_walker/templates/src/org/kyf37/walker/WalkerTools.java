package org.kyf37.walker;
import java.io.IOException;
import java.util.Arrays;
/** Physical walker operations adapted from pwalkerHax; GPL-3.0. */
final class WalkerTools {
 interface Backup {void save(byte[] bytes)throws IOException;}
 static final class Gift {
  final int species,item,level,gender,shiny,ability;final int[] moves;
  Gift(int[] v){species=v[0];item=v[1];moves=Arrays.copyOfRange(v,2,6);level=v[6];gender=v[7];shiny=v[8];ability=v[9];}
  void validate()throws IOException {
   range(species,1,WalkerCatalog.POKE.length-1);range(item,0,WalkerCatalog.ITEM.length-1);
   range(level,1,100);range(gender,0,1);range(shiny,0,1);range(ability,0,WalkerCatalog.ABILITY.length-1);
   for(int m:moves)range(m,0,WalkerCatalog.MOVE.length-1);if(moves[0]==0)throw new IOException("Choose a first move");
  }
 }
 static void range(int v,int lo,int hi)throws IOException {if(v<lo||v>hi)throw new IOException("Value outside supported range");}
 private final WalkerReader reader;
 WalkerTools(WalkerReader r){reader=r;}
 private void before(Backup backup,WalkerReader.Progress progress)throws IOException {backup.save(reader.toolBackup(progress));}
 void watts(int watts,int steps,boolean max,Backup backup,WalkerReader.Progress progress)throws IOException {
  range(watts,1,65535);range(steps,0,99999);
  try{reader.beginTools();before(backup,progress);long total=9999999;
   if(steps>0){if(!max){reader.toolExploit(WalkerCatalog.WRITE_TODAYSTEPS_TO_EEPROM,false);reader.toolExploit(WalkerCatalog.WRITE_TOTALSTEPS_TO_EEPROM,false);
     byte[] old=reader.toolRead(0xfff0,8);total=Math.max(steps,Math.min(9999999,WalkerReader.be32(old,4)-WalkerReader.be32(old,0)+steps));}
    reader.toolCommand(6,0xf7,ram(0x9c,steps),6,false);}
   if(steps>0||max)reader.toolCommand(6,0xf7,ram(0x80,total),6,false);
   byte[] p=WalkerCatalog.ADD_WATTS.clone();p[3]=(byte)(watts>>>8);p[4]=(byte)watts;reader.toolExploit(p,false);
  }finally{reader.finishTools();}
 }
 void item(int item,Backup backup,WalkerReader.Progress progress)throws IOException {
  range(item,1,WalkerCatalog.ITEM.length-1);
  final String giftName=UiText.catalog(WalkerCatalog.ITEM,item);
  try{reader.beginTools();before(backup,progress);byte[] b=new byte[8];le(b,6,item);
   reader.toolWrite(0xbd40,b);reader.toolWrite(0xbd48,GiftBitmap.name(giftName,96));reader.toolCommand(0xc4,1,new byte[0],0xc4,false);
  }finally{reader.finishTools();}
 }
 void pokemon(Gift gift,Backup backup,WalkerReader.Progress progress)throws IOException {
  gift.validate();try{reader.beginTools();WalkerReader.Identity id=reader.toolIdentity();before(backup,progress);
   byte[] b=new byte[16];le(b,0,gift.species);le(b,2,gift.item);for(int i=0;i<4;i++)le(b,4+i*2,gift.moves[i]);
   b[12]=(byte)gift.level;b[13]=(byte)(gift.gender==1?0x20:0);b[14]=(byte)(gift.shiny==1?2:0);
   byte[] extra=new byte[44];le(extra,4,id.trainerId);le(extra,6,id.secretId);le(extra,10,2008);
   System.arraycopy(id.bytes(),72,extra,14,16);extra[31]=(byte)gift.ability;le(extra,32,4);
   byte[] animation=new byte[384];Arrays.fill(animation,192,384,(byte)255);
   reader.toolWrite(0xba44,b);reader.toolWrite(0xba54,extra);reader.toolWrite(0xba80,animation);
   reader.toolWrite(0xbc00,GiftBitmap.name(WalkerCatalog.POKE[gift.species],80));reader.toolCommand(0xc2,1,new byte[0],0xc2,false);
  }finally{reader.finishTools();}
 }
 byte[] rom(WalkerReader.Progress progress)throws IOException {
  try{reader.beginTools();reader.toolExploit(WalkerCatalog.ROM_DUMP,true);byte[] out=new byte[49152];
   for(int a=0;a<out.length;a+=128){byte[] page=reader.receiveTools(0xaa,128,false,-1,true).payload;System.arraycopy(page,0,out,a,128);progress.bytesRead(a+128);}return out;
  }finally{reader.finishTools();}
 }
 static byte[] ram(int address,long value){return new byte[]{(byte)address,(byte)(value>>>24),(byte)(value>>>16),(byte)(value>>>8),(byte)value};}
 static void le(byte[] b,int a,int v){b[a]=(byte)v;b[a+1]=(byte)(v>>>8);}
}
