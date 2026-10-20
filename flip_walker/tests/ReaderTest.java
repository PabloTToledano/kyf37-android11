package org.kyf37.walker;
import java.io.*;
import java.util.*;

public final class ReaderTest {
    static int checks;
    static void check(boolean good,String name){if(!good)throw new AssertionError(name);checks++;System.out.println("PASS "+name);}
    interface Task { void run()throws Exception; }
    static void fails(Task task,String name)throws Exception{
        try{task.run();throw new AssertionError(name);}catch(IOException expected){check(true,name);}
    }
    static final byte[] SID={0x12,0x34,0x56,0x78};
    static byte[] identity(){
        byte[] b=new byte[104];b[12]=0x39;b[13]=0x30;b[14]=0x31;b[15]=(byte)0xd4;
        b[72]=(byte)0xac;b[74]=(byte)0xdf;b[76]=(byte)0xa2;b[78]=(byte)0xff;b[79]=(byte)0xff;
        b[91]=3;b[96]=1;b[99]=5;b[100]=0;b[101]=1;b[102]=(byte)0xe2;b[103]=0x40;return b;
    }
    static final class Fake implements WalkerReader.Link,WalkerReader.Clock,WalkerReader.Cancel {
        long time;boolean cancel,fragment,corrupt,wrongSession,wrongExtra,oversize,trailing;int truncatePage=-1;
        final List<Packet> sent=new ArrayList<>();final Deque<byte[]> replies=new ArrayDeque<>();
        final byte[] memory=new byte[65536];
        Fake(){for(int i=0;i<memory.length;i++)memory[i]=(byte)(i*37);replies.add(new byte[]{0x56});}
        public long milliseconds(){return time;}
        public boolean requested(){return cancel;}
        public byte[] read(){time+=50;return replies.isEmpty()?new byte[0]:replies.removeFirst();}
        void reply(Packet p){
            byte[] wire=p.encode();
            if(corrupt){byte[] bad=wire.clone();bad[3]^=1;replies.add(bad);}
            if(trailing){byte[] twice=new byte[wire.length*2];System.arraycopy(wire,0,twice,0,wire.length);System.arraycopy(wire,0,twice,wire.length,wire.length);replies.add(twice);return;}
            if(fragment){replies.add(new byte[]{0x13,0x24});for(int i=0;i<wire.length;i+=3)replies.add(Arrays.copyOfRange(wire,i,Math.min(i+3,wire.length)));}
            else replies.add(wire);
        }
        public void send(byte[] wire)throws IOException{
            Packet p=Packet.decode(wire);sent.add(p);
            if(p.extra!=1)throw new AssertionError("Master extra must be 1");
            if(p.command==0xfa){if(!Arrays.equals(p.session,new byte[4]))throw new AssertionError("SYN session");reply(new Packet(0xf8,2,SID,new byte[0]));}
            else if(p.command==0x20){
                if(oversize){replies.add(new byte[264]);return;}
                byte[] sid=wrongSession?new byte[4]:SID;
                reply(new Packet(0x22,wrongExtra?1:2,sid,identity()));
            }else if(p.command==0x0c){
                if(!Arrays.equals(p.session,SID)||p.payload.length!=3||(p.payload[2]&255)!=128)throw new AssertionError("Read request");
                int a=(p.payload[0]&255)*256+(p.payload[1]&255);
                if(a==truncatePage)return;
                reply(new Packet(0x0e,2,SID,Arrays.copyOfRange(memory,a,a+128)));
            }else if(p.command!=0xf4)throw new AssertionError("Remote write command: "+p.command);
        }
        WalkerReader reader(){return new WalkerReader(this,this,this);}
    }
    public static void main(String[] args)throws Exception{
        Fake f=new Fake();WalkerReader.Result info=f.reader().read(false,n->{});
        check(info.identity.trainerId==12345&&info.identity.secretId==54321,"identity trainer ID byte order");
        check(info.identity.steps==123456&&info.identity.lastSync==16777221,"identity unsigned big-endian fields");
        check(info.identity.paired&&info.identity.hasPokemon&&info.identity.trainer.equals("Az0"),"identity flags and bounded trainer decoding");
        check(info.snapshot()==null&&f.sent.size()==3&&f.sent.get(2).command==0xf4,"info read uses SYN, identity and disconnect only");
        byte[] raw=info.identity.bytes();raw[12]=0;check(info.identity.bytes()[12]==0x39,"identity capture is immutable");
        f=new Fake();final List<Integer> progress=new ArrayList<>();WalkerReader.Result full=f.reader().read(true,progress::add);
        check(Arrays.equals(full.snapshot(),f.memory),"all 64 KiB read without normalization");
        check(f.sent.size()==515&&f.sent.get(2).payload[0]==0&&f.sent.get(513).payload[0]==(byte)0xff&&f.sent.get(513).payload[1]==(byte)0x80,"512 page requests cover full address range once");
        check(progress.size()==513&&progress.get(0)==0&&progress.get(512)==65536,"progress ends only after final complete page");
        byte[] copy=full.snapshot();copy[0]=99;check(full.snapshot()[0]==f.memory[0],"EEPROM result is immutable");
        f=new Fake();f.fragment=true;check(f.reader().read(false,n->{}).identity.steps==123456,"fragmented packets and leading noise reassemble");
        f=new Fake();f.corrupt=true;check(f.reader().read(false,n->{}).identity.paired,"bad checksum rejected before valid reply");
        final Fake wrong=new Fake();wrong.wrongSession=true;fails(()->wrong.reader().read(false,n->{}),"wrong-session identity rejected");
        check(wrong.sent.get(wrong.sent.size()-1).command==0xf4,"failure attempts disconnect");
        final Fake extra=new Fake();extra.wrongExtra=true;fails(()->extra.reader().read(false,n->{}),"wrong master/slave direction rejected");
        final Fake big=new Fake();big.oversize=true;fails(()->big.reader().read(false,n->{}),"oversized transport reply rejected");
        final Fake doubled=new Fake();doubled.trailing=true;fails(()->doubled.reader().read(false,n->{}),"coalesced duplicate responses fail closed");
        final Fake none=new Fake();none.replies.clear();fails(()->none.reader().read(false,n->{}),"no device has bounded discovery timeout");
        check(none.time>=20000&&none.time<=20100&&none.sent.isEmpty(),"no unsolicited packets without real advertisement");
        final Fake cancelled=new Fake();cancelled.cancel=true;fails(()->cancelled.reader().read(true,n->{}),"cancel before handshake sends nothing");
        check(cancelled.sent.isEmpty(),"cancelled discovery never transmits");
        final Fake mid=new Fake();fails(()->mid.reader().read(true,n->{if(n>=128)mid.cancel=true;}),"cancelled backup returns no partial result");
        check(mid.sent.size()==4&&mid.sent.get(3).command==0xf4,"cancelled backup closes session after one page");
        final Fake missing=new Fake();missing.truncatePage=128;fails(()->missing.reader().read(true,n->{}),"missing EEPROM page aborts entire backup");
        int requests=0;for(Packet p:missing.sent)if(p.command==0x0c)requests++;
        check(requests==2,"ambiguous EEPROM replies are never retried in same session");
        final Fake once=new Fake();WalkerReader reader=once.reader();reader.read(false,n->{});fails(()->reader.read(false,n->{}),"sessions cannot be reused");
        byte[] allChars=new byte[104];Arrays.fill(allChars,(byte)0);check(new WalkerReader.Identity(allChars).trainer.length()==8,"unterminated trainer name stays within eight codepoints");
        try{new WalkerReader.Identity(new byte[103]);throw new AssertionError("short identity");}catch(IllegalArgumentException good){check(true,"truncated identity rejected");}
        System.out.println("READER_CHECKS="+checks);
    }
}
