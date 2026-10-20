package org.kyf37.walker;
import java.io.*;
import java.util.*;

public final class ProtocolTest {
    static int checks;
    static void check(boolean b,String name){if(!b)throw new AssertionError(name);checks++;System.out.println("PASS "+name);}
    static void rejects(Runnable test,String name){try{test.run();throw new AssertionError(name);}catch(IllegalArgumentException good){checks++;System.out.println("PASS "+name);}}
    static byte[] sid={1,2,3,4};
    static byte[] hex(String value){byte[] b=new byte[value.length()/2];for(int i=0;i<b.length;i++)b[i]=(byte)Integer.parseInt(value.substring(i*2,i*2+2),16);return b;}
    static Packet send(Walker w,int command,int extra,byte[] p)throws Exception{
        byte[] reply=w.receive(new Packet(command,extra,sid,p).encode());return reply==null?null:Packet.decode(reply);
    }
    static void handshake(Walker w)throws Exception{
        sid=new byte[]{1,2,3,4};byte[] request=new Packet(0xfa,1,sid,new byte[0]).encode();
        byte[] reply=w.receive(request);
        check(Arrays.equals(reply,w.receive(request)),"duplicate handshake keeps session");
        Packet response=Packet.decode(reply);check(response.command==0xf8,"handshake response");
        for(int i=0;i<4;i++)sid[i]^=response.session[i];
    }
    public static void main(String[] args)throws Exception{
        Packet p=new Packet(0x24,1,new byte[]{1,2,3,4},new byte[0]);
        // Hand-calculated seed=2, carry-fold, byte-swapped checksum 09 28.
        check(Arrays.equals(p.encode(),new byte[]{(byte)0x8e,(byte)0xab,(byte)0xa3,(byte)0x82,(byte)0xab,(byte)0xa8,(byte)0xa9,(byte)0xae}),"known ping wire vector");
        byte[] documented=new Packet(0xfa,1,new byte[]{0x3f,0x57,(byte)0xcf,0x34},new byte[0]).encode();
        check(((documented[2]^0xaa)&255)==0x90 && ((documented[3]^0xaa)&255)==8,"published FA checksum 9008");
        documented=new Packet(0xf8,2,new byte[]{0x4a,0x21,0x2e,7},new byte[0]).encode();
        check(((documented[2]^0xaa)&255)==0x2d && ((documented[3]^0xaa)&255)==0x70,"published F8 checksum 2D70");
        check(Packet.decode(hex("50abb2b3efde7335")).command==0xfa,"independent captured game handshake");
        check(Packet.decode(hex("8aabbd95efde7335")).command==0x20,"independent captured identity request");
        byte[] corrupt=p.encode();corrupt[4]^=1;rejects(()->Packet.decode(corrupt),"corrupt checksum rejected");
        rejects(()->Packet.decode(new byte[7]),"short packet rejected");
        Random r=new Random(37);
        for(int size:new int[]{0,1,3,104,128,255}){
            byte[] bytes=new byte[size];r.nextBytes(bytes);Packet q=Packet.decode(new Packet(0x82,0xab,sid,bytes).encode());
            check(Arrays.equals(bytes,q.payload),"packet roundtrip "+size);
        }
        ByteArrayOutputStream literal=new ByteArrayOutputStream();literal.write(new byte[]{0x10,(byte)0x80,0,0});
        for(int i=0;i<16;i++){literal.write(0);for(int j=0;j<8;j++)literal.write(i*8+j);}
        byte[] decompressed=Packet.decompress(literal.toByteArray());check(decompressed[127]==127,"LZ literal block");
        ByteArrayOutputStream repeat=new ByteArrayOutputStream();repeat.write(new byte[]{0x10,(byte)0x80,0,0,0x7f,65});
        for(int i=0;i<7;i++)repeat.write(new byte[]{(byte)0xf0,0});repeat.write(new byte[]{0,65});
        byte[] repeated=Packet.decompress(repeat.toByteArray());boolean allA=true;for(byte b:repeated)allA&=b==65;
        check(allA,"LZ overlapping backreference block");
        rejects(()->Packet.decompress(new byte[]{0x10,(byte)0x80,0,0,(byte)0x80,0,0}),"LZ backwards underflow rejected");
        rejects(()->Packet.decompress(new byte[]{0x10,(byte)0x80,0,0}),"truncated LZ rejected");
        List<byte[]> commits=new ArrayList<>();Walker w=new Walker(null,bytes->commits.add(bytes));handshake(w);
        check(send(w,0x20,1,new byte[0]).payload.length==104,"unpaired identity");
        byte[] page=new byte[128];for(int i=0;i<128;i++)page[i]=(byte)i;
        check(send(w,2,0x40,page).command==4 && commits.size()>0,"write committed before ACK");
        check(Arrays.equals(send(w,0x0c,1,new byte[]{0x40,0,(byte)128}).payload,page),"EEPROM readback");
        check(send(w,0,0x41,literal.toByteArray()).command==4,"compressed EEPROM ACK");
        check(Arrays.equals(send(w,0x0c,1,new byte[]{0x41,0,(byte)128}).payload,page),"compressed EEPROM readback");
        byte[] identity=new byte[104]; // Real game sends zero walker flags/version here.
        check(send(w,0x52,1,identity).command==0x54,"RTC / walk identity staging");
        byte[] route=new byte[128];route[0]=25;route[82]=16;route[94]=5;
        send(w,2,0xd7,route);route=new byte[128];route[8]=100;route[12]=13;route[52]=100;send(w,0x82,0xd7,route);
        check(send(w,0x5a,1,new byte[0]).command==0x5a && w.species()==25 && w.strolling(),"start walk copies staged route and identity");
        check(w.snapshot()[0xed+0x5c]==2 && w.snapshot()[0xed+0x5b]==3,"start walk supplies walker flags and version");
        check(send(w,0x40,1,identity).command==0x42,"game return metadata command 40 replies 42");
        w.addSteps(201);check(w.steps()==201 && w.watts()==10,"real steps earn watts");
        check(w.snapshot()[0x164]==0 && w.snapshot()[0x165]==10 && w.snapshot()[0x166]==0,"watts match documented HealthData offset");
        check(w.chooseEncounter(new Random(1),false)==0,"route Pokémon selection");
        check(w.chooseEncounter(new Random(1),true)==0,"route item selection");
        check(w.collect(0,false)&&w.caughtCount()==1,"caught Pokémon game save slot");
        check(w.collect(0,true)&&w.itemCount()==1,"dowsed item game save slot");
        byte[] snapshot=w.snapshot();Walker restored=new Walker(snapshot,bytes->{});
        check(restored.steps()==201 && restored.watts()==10 && restored.caughtCount()==1,"save survives process restart");
        restored.advanceDays(1);check(restored.steps()==0 && restored.snapshot()[0xcef3]==(byte)201 && restored.watts()==10,"midnight preserves watts and shifts step history");
        for(int i=0;i<10;i++)restored.addSteps(10000);
        check(restored.steps()==99999 && (restored.snapshot()[0xce88]&1)==1,"daily step cap and berry flag");
        int cappedWatts=restored.watts();for(int i=0;i<19;i++)restored.addSteps(1);
        check(restored.watts()==cappedWatts+1,"step cap does not grant one watt every step");
        restored.advanceDays(8);check(restored.snapshot()[0xcef3]==0 && restored.snapshot()[0xcf0b]==0,"old steps expire beyond seven-day history");
        send(w,0x20,1,new byte[0]);check((w.snapshot()[0xce8b]&255)==10,"watts exported to game");
        check(send(w,0x60,1,identity).command==0x62,"gift collection metadata replies 62");
        check(send(w,0x66,1,new byte[0]).command==0x68 && w.strolling() && w.caughtCount()==0 && w.itemCount()==0 && w.watts()==0,"gift completion clears transferred rewards and keeps companion");
        check(send(w,0x4e,1,new byte[0]).command==0x50 && !w.strolling() && w.paired(),"return walk preserves pairing");
        byte[] before=w.snapshot();try{send(w,0x0a,255,new byte[]{(byte)255,1,2});throw new AssertionError();}catch(IllegalArgumentException expected){}
        check(Arrays.equals(before,w.snapshot()),"out-of-range writes do not alter save");
        try{send(w,0x06,0,new byte[]{0});throw new AssertionError();}catch(IllegalArgumentException expected){}
        check(Arrays.equals(before,w.snapshot()),"internal memory writes cannot affect virtual save");
        Packet wrong=new Packet(2,0,new byte[4],new byte[128]);check(w.receive(wrong.encode())==null,"foreign sessions ignored");
        Walker failing=new Walker(null,bytes->{throw new IOException("disk full");});handshake(failing);before=failing.snapshot();
        try{send(failing,2,0x40,page);throw new AssertionError();}catch(IOException expected){}
        check(Arrays.equals(before,failing.snapshot()),"disk failure rolls back without ACK");
        handshake(w);send(w,0xf4,1,new byte[0]);check(!w.connected(),"disconnect releases protocol session");
        final byte[][] backup={null};Walker reset=new Walker(snapshot,new Walker.Store(){
            public void beforeGameReset(byte[] bytes){backup[0]=bytes;}
            public void commit(byte[] bytes){}
        });handshake(reset);Packet resetReply=send(reset,0x2a,1,new byte[40]);
        check(resetReply.command==0x2a && resetReply.payload.length==40 && resetReply.payload[0]==(byte)0xff && !reset.paired(),"game reset affects virtual walker and returns erased unique ID");
        check(Arrays.equals(backup[0],snapshot),"game reset checkpoints previous virtual save");
        System.out.println("PROTOCOL_CHECKS="+checks);
    }
}
