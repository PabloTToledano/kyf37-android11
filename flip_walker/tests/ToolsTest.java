package org.kyf37.walker;
import java.io.*;
import java.util.*;
public final class ToolsTest {
 static int passed;static void ok(boolean v,String name){if(!v)throw new AssertionError(name);passed++;System.out.println("PASS "+name);}
 static class Fake implements WalkerReader.Link,WalkerReader.Clock {
  byte[] sid={3,5,7,9},memory=new byte[65536];ArrayDeque<byte[]> q=new ArrayDeque<>();ArrayList<Packet> sent=new ArrayList<>();long time;int romPage;boolean streaming;
  Fake(){q.add(new byte[]{0x56});for(int i=0;i<memory.length;i++)memory[i]=(byte)i;Arrays.fill(memory,0xfff0,0xfff8,(byte)0);memory[0xfff3]=10;memory[0xfff7]=100;}
  public long milliseconds(){return time;}
  void reply(int c,int e,byte[] data){q.add(new Packet(c,e,sid,data).encode());}
  public void send(byte[] b){Packet p=Packet.decode(b);sent.add(p);
   if(p.command==0xfa)reply(0xf8,2,new byte[0]);
   else if(p.command==0x20){byte[] id=new byte[104];id[12]=52;id[13]=18;id[14]=120;id[15]=86;Arrays.fill(id,72,88,(byte)255);reply(0x22,2,id);}
   else if(p.command==0xc){int a=WalkerReader.be16(p.payload,0),n=p.payload[2]&255;reply(0xe,2,Arrays.copyOfRange(memory,a,a+n));}
   else if(p.command==0xa){int a=(p.extra<<8)|(p.payload[0]&255);System.arraycopy(p.payload,1,memory,a,p.payload.length-1);reply(4,2,new byte[0]);}
   else if(p.command==6){reply(6,2,new byte[0]);if(p.extra==0xf9&&Arrays.equals(p.payload,WalkerCatalog.ROM_DUMP))streaming=true;else if(streaming&&p.extra==0xf7){
    byte[] ack=q.removeLast();byte[] page=new Packet(0xaa,2,sid,romBytes(romPage++)).encode();byte[] all=Arrays.copyOf(ack,ack.length+page.length);System.arraycopy(page,0,all,ack.length,page.length);q.add(all);
   }}else if(p.command==0xc2||p.command==0xc4)reply(p.command,2,new byte[0]);else if(p.command!=0xf4)throw new AssertionError("unexpected "+p.command);
  }
  byte[] romBytes(int page){byte[] b=new byte[128];for(int i=0;i<128;i++)b[i]=(byte)(page+i);return b;}
  public byte[] read(){time+=10;if(!q.isEmpty())return q.remove();if(streaming&&romPage<384)return new Packet(0xaa,2,sid,romBytes(romPage++)).encode();return new byte[0];}
  WalkerTools tools(){return new WalkerTools(new WalkerReader(this,()->false,this));}
  long count(int cmd){return sent.stream().filter(p->p.command==cmd).count();}
 }
 public static void main(String[] args)throws Exception {
  Fake f=new Fake();byte[][] backup={null};f.tools().item(50,b->backup[0]=b.clone(),n->{});
  ok(backup[0].length==65536&&backup[0][0xbd46]!=(byte)50,"pre-change backup before gift writes");
  ok(WalkerReader.le16(f.memory,0xbd46)==50&&f.count(0xc4)==1,"item event and little endian ID");
  ok(f.count(0xc)==512&&f.sent.get(f.sent.size()-1).command==0xf4,"complete backup and disconnect");
  f=new Fake();Fake blocked=f;try{f.tools().item(4,b->{throw new IOException("disk full");},n->{});throw new AssertionError();}catch(IOException expected){}
  ok(blocked.count(0xa)==0&&blocked.count(6)==0&&blocked.count(0xc4)==0,"backup failure prevents physical writes");
  f=new Fake();f.tools().watts(65535,100,false,b->{},n->{});
  Packet total=f.sent.stream().filter(p->p.command==6&&p.payload.length==5&&p.payload[0]==(byte)0x80).findFirst().get();
  ok(WalkerReader.be32(total.payload,1)==190,"step total subtracts old today before replacement");
  ok(f.sent.stream().anyMatch(p->p.command==6&&p.extra==0xf9&&p.payload.length==17&&(p.payload[3]&255)==255&&(p.payload[4]&255)==255),"watts payload unsigned 16-bit");
  f=new Fake();f.tools().watts(1,0,true,b->{},n->{});
  ok(f.sent.stream().anyMatch(p->p.command==6&&p.payload.length==5&&p.payload[0]==(byte)0x80&&WalkerReader.be32(p.payload,1)==9999999),"max total steps option");
  ok(f.sent.stream().noneMatch(p->p.command==6&&p.payload.length==5&&p.payload[0]==(byte)0x9c),"zero today leaves today unchanged");
  f=new Fake();f.tools().pokemon(new WalkerTools.Gift(new int[]{493,50,467,1,2,3,100,1,1,123}),b->{},n->{});
  ok(WalkerReader.le16(f.memory,0xba44)==493&&(f.memory[0xba50]&255)==100&&f.memory[0xba51]==0x20&&f.memory[0xba52]==2,"pokemon species level gender shiny layout");
  ok(WalkerReader.le16(f.memory,0xba58)==0x1234&&WalkerReader.le16(f.memory,0xba5a)==0x5678&&WalkerReader.le16(f.memory,0xba74)==4,"gift preserves physical trainer ownership and ball");
  ok((f.memory[0xba73]&255)==123&&f.count(0xc2)==1,"gift ability and event command");
  f=new Fake();byte[] rom=f.tools().rom(n->{});
  ok(rom.length==49152&&rom[0]==0&&(rom[49151]&255)==((383+127)&255),"ROM complete with ACK and first page coalesced");
  ok(f.count(0xa)==0&&f.count(0xc)==0,"ROM uses RAM payload without EEPROM writes");
  f=new Fake();try{f.tools().item(0,b->{},n->{});throw new AssertionError();}catch(IOException expected){}
  ok(f.sent.isEmpty(),"invalid gift rejected before handshake");
  f=new Fake();try{f.tools().pokemon(new WalkerTools.Gift(new int[]{25,0,0,0,0,0,50,0,0,9}),b->{},n->{});throw new AssertionError();}catch(IOException expected){}
  ok(f.sent.isEmpty(),"missing move rejected before handshake");
  Fake shortRom=new Fake(){public byte[] read(){if(streaming&&romPage>=5&&q.isEmpty()){time+=100;return new byte[0];}return super.read();}};
  try{shortRom.tools().rom(n->{});throw new AssertionError();}catch(IOException expected){}
  ok(shortRom.romPage==5&&shortRom.sent.get(shortRom.sent.size()-1).command==0xf4,"truncated ROM produces no capture and disconnects");
  Fake writeFail=new Fake(){public void send(byte[] b){Packet p=Packet.decode(b);if(p.command==0xa)throw new IllegalArgumentException("write link failed");super.send(b);}};
  try{writeFail.tools().item(4,b->{},n->{});throw new AssertionError();}catch(IllegalArgumentException expected){}
  ok(writeFail.count(0xc4)==0,"failed gift write never triggers event");
  Fake cancelFake=new Fake();boolean[] cancelled={false};WalkerTools cancelTools=new WalkerTools(new WalkerReader(cancelFake,()->cancelled[0],cancelFake));
  try{cancelTools.item(4,b->cancelled[0]=true,n->{});throw new AssertionError();}catch(IOException expected){}
  ok(cancelFake.count(0xa)==0&&cancelFake.count(0xc4)==0,"cancel after backup prevents first mutation");
  RealMenu m=new RealMenu();ok(m.count()==6,"all six reference operations");m.mode=2;m.row=9;m.change(1000);ok(m.gift[9]==123,"ability bounded");m.row=0;m.digit(4);m.digit(9);m.digit(3);ok(m.gift[0]==493,"keypad numeric catalog entry");
  m.row=10;m.move(1);ok(m.row==0,"editor scroll wraps");m.confirm=true;int old=m.gift[0];m.digit(1);ok(m.gift[0]==old,"confirmation freezes digit edits");
  byte[] image=GiftBitmap.name("RARE CANDY",96);ok(image.length==384&&Arrays.stream(new int[]{image[0],image[1]}).sum()==0,"gift bitmap size and left padding");
  ok(WalkerCatalog.POKE.length==494&&WalkerCatalog.MOVE.length==468&&WalkerCatalog.ABILITY.length==124,"complete generation four catalogs");
  System.out.println("TOOLS_CHECKS="+passed);
 }
}
