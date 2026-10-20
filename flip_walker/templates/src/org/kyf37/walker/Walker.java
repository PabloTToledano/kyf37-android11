package org.kyf37.walker;

import java.io.IOException;
import java.util.Arrays;
import java.security.SecureRandom;

/** Game-facing virtual EEPROM. No phone partitions are used. */
public final class Walker {
    public interface Store {
        void commit(byte[] bytes) throws IOException;
        default void beforeGameReset(byte[] bytes) throws IOException {}
    }
    private byte[] memory;
    private final Store store;
    private byte[] session=new byte[4], handshakeRequest, handshakeReply, pending;
    private boolean connected, collectingGifts;
    private byte[] lastRequest, lastReply; // conformance: replay-safe cache
    public String status="Ready to pair with HeartGold / SoulSilver";
    public Walker(byte[] saved, Store store) {
        if(saved!=null && saved.length!=65536) throw new IllegalArgumentException("Save must be 64 KiB");
        this.store=store; memory=saved==null?new byte[65536]:saved.clone();
        if(saved==null) {
            byte[] magic={'n','i','n','t','e','n','d','o'};System.arraycopy(magic,0,memory,0,8);
            byte[] id=new byte[104]; id[0x5c]=2; reliable(0xed,id);
            reliable(0x156,new byte[24]); reliable(0x16f,new byte[2]);
            byte[] unique=new byte[40]; Arrays.fill(unique,(byte)0xff); reliable(0x83,unique);
        } else if(memory[0x16f]==(byte)0xa5) copyStaged();
    }
    public synchronized byte[] snapshot(){return memory.clone();}
    /** shared-save: adopt the emulated firmware's EEPROM (same layout) and persist it. */
    public synchronized void replaceAll(byte[] bytes)throws IOException{
        if(bytes.length!=65536)throw new IllegalArgumentException("Save must be 64 KiB");
        if(java.util.Arrays.equals(bytes,memory))return;
        byte[] old=memory;memory=bytes.clone();disconnect();
        try{store.commit(memory.clone());}catch(IOException e){memory=old;throw e;}
    }
    public synchronized int species(){return u16le(0x8f00);}
    public synchronized boolean paired(){return (memory[0xed+0x5b]&1)!=0;}
    public synchronized boolean strolling(){return (memory[0xed+0x5b]&2)!=0;}
    public synchronized long steps(){return u32be(0x15a);}
    public synchronized int watts(){return u16be(0x164);}
    public synchronized boolean connected(){return connected;}
    public synchronized int caughtCount(){int n=0;for(int i=0;i<3;i++)if(u16le(0xce8c+i*16)!=0)n++;return n;}
    public synchronized int itemCount(){int n=0;for(int i=0;i<3;i++)if(u16le(0xcebc+i*4)!=0)n++;return n;}
    public synchronized int routePokemon(int slot){if(slot<0||slot>2)return 0;return u16le(0x8f00+82+slot*16);}
    public synchronized int routeItem(int slot){if(slot<0||slot>9)return 0;return u16le(0x8f00+140+slot*2);}
    public synchronized int chooseEncounter(java.util.Random random,boolean item){
        int limit=item?10:3, base=0x8f00, minimum=item?160:130, chance=item?180:136;
        for(int i=0;i<limit;i++)if(steps()>=u16le(base+minimum+i*2) && random.nextInt(100)<(memory[base+chance+i]&255)
                && (item?routeItem(i):routePokemon(i))!=0)return i;
        return -1;
    }
    public synchronized boolean spendWatts(int amount)throws IOException {
        if(amount<0||watts()<amount)return false;byte[] old=memory.clone();put16(0x164,watts()-amount);health();
        try{store.commit(memory.clone());return true;}catch(IOException e){memory=old;throw e;}
    }
    public synchronized boolean collect(int slot,boolean item)throws IOException {
        if(slot<0||slot>=(item?10:3))return false;
        int species=item?routeItem(slot):routePokemon(slot);if(species==0)return false;
        for(int i=0;i<3;i++){
            int destination=(item?0xcebc:0xce8c)+i*(item?4:16);
            if(u16le(destination)==0){
                byte[] old=memory.clone();
                if(item){memory[destination]=(byte)species;memory[destination+1]=(byte)(species>>>8);}
                else System.arraycopy(memory,0x8f00+82+slot*16,memory,destination,16);
                try{store.commit(memory.clone());return true;}catch(IOException e){memory=old;throw e;}
            }
        }
        return false;
    }
    public synchronized void disconnect(){lastRequest=null;lastReply=null;connected=false;handshakeRequest=null;handshakeReply=null;pending=null;collectingGifts=false;}
    private int u16be(int a){return (memory[a]&255)<<8|memory[a+1]&255;}
    private int u16le(int a){return (memory[a]&255)|(memory[a+1]&255)<<8;}
    private long u32be(int a){return ((long)u16be(a)<<16)|u16be(a+2);}
    private void put32(int a,long n){for(int i=3;i>=0;i--){memory[a+i]=(byte)n;n>>>=8;}}
    private void put16(int a,int n){memory[a]=(byte)(n>>>8);memory[a+1]=(byte)n;}
    private byte[] slice(int a,int n){range(a,n);return Arrays.copyOfRange(memory,a,a+n);}
    private static void range(int a,int n){if(a<0||n<0||a>65536-n)throw new IllegalArgumentException("EEPROM range");}
    private static void size(byte[] p,int n){if(p.length!=n)throw new IllegalArgumentException("command size");}
    private void reliable(int a,byte[] data){
        int sum=1;for(byte b:data)sum=(sum+(b&255))&255;
        System.arraycopy(data,0,memory,a,data.length);memory[a+data.length]=(byte)sum;
        int copy=a<0x100?a+0x100:a==0x156?0x256:0x26f;
        System.arraycopy(memory,a,memory,copy,data.length+1);
    }
    private void health(){reliable(0x156,slice(0x156,24));}
    public synchronized void addSteps(int count) throws IOException {
        if(count<=0 || count>10000)return;
        byte[] old=memory.clone();
        long today=steps(),total=u32be(0x156);put32(0x156,Math.min(0xffffffffL,total+count));
        put32(0x15a,Math.min(99999,today+count));
        int earned=(int)((total+count)/20-total/20);put16(0x164,Math.min(9999,watts()+earned));
        if(today+count>=99999)memory[0xce88]|=1;health();
        try{store.commit(memory.clone());}catch(IOException e){memory=old;throw e;}
    }
    public synchronized void advanceDays(int days)throws IOException {
        if(days<=0)return;byte[] old=memory.clone();int shift=Math.min(days,7);
        for(int i=6;i>=0;i--)put32(0xcef0+i*4,days>7?0:i>=shift?u32be(0xcef0+(i-shift)*4):i==shift-1?steps():0);
        put32(0x15a,0);put16(0x162,Math.min(65535,u16be(0x162)+days));health();
        try{store.commit(memory.clone());}catch(IOException e){memory=old;throw e;}
    }
    private void copyStaged(){
        System.arraycopy(memory,0xd700,memory,0x8f00,0x2900);
        System.arraycopy(memory,0xd480,memory,0xcc00,0x280);
        reliable(0x16f,new byte[2]);
    }
    private void startWalk(boolean clearSpecial){
        reliable(0x16f,new byte[]{(byte)0xa5,0});copyStaged();
        if(pending!=null){
            byte[] id=pending.clone();id[0x5b]=(byte)((id[0x5b]&~6)|1|(species()!=0?2:0));
            id[0x5c]=2;id[0x5e]=0;id[0x5f]=2;reliable(0xed,id);pending=null;
        }
        if(clearSpecial)memory[0xb800]=0;
        Arrays.fill(memory,0xce8c,0xcef0,(byte)0);Arrays.fill(memory,0xcf0c,0xd480,(byte)0);
        Arrays.fill(memory,0xde24,0xf38c,(byte)0);put16(0x164,0);put16(0xce8a,0);health();
        status="Walk received from the game";
    }
    /** Commit all changed EEPROM bytes before acknowledging a game write. */
    public synchronized byte[] receive(byte[] wire) throws IOException {
        Packet p=Packet.decode(wire);
        if(p.command==0xfa){
            size(p.payload,0);
            if(handshakeRequest!=null && Arrays.equals(handshakeRequest,p.session))return handshakeReply.clone();
            byte[] slave=new byte[4];new SecureRandom().nextBytes(slave);
            handshakeRequest=p.session.clone();handshakeReply=new Packet(0xf8,2,slave,new byte[0]).encode();
            for(int i=0;i<4;i++)session[i]=(byte)(p.session[i]^slave[i]);
            connected=true;pending=null;collectingGifts=false;status="Game connected";return handshakeReply.clone();
        }
        if(!connected || !Arrays.equals(p.session,session))return null;
        // conformance: replay-safe — same request again means our reply was lost
        if(lastRequest!=null && Arrays.equals(lastRequest,wire))return lastReply==null?null:lastReply.clone();
        byte[] old=memory.clone(), oldPending=pending==null?null:pending.clone();String oldStatus=status;boolean oldGifts=collectingGifts;
        int reply=-1, extra=2;byte[] data=new byte[0];
        try {
            switch(p.command){
                case 0x00: case 0x80: case 0x02: case 0x82: {
                    // conformance: short-write — raw writes may be 1..128 bytes (HG/SS sends 36 at D680)
                    byte[] decoded=(p.command&2)==0?Packet.decompress(p.payload):p.payload;
                    if(decoded.length<1||decoded.length>128)throw new IllegalArgumentException("write size");
                    int a=(p.extra<<8)|(p.command&0x80);range(a,decoded.length);
                    System.arraycopy(decoded,0,memory,a,decoded.length);reply=4;extra=p.extra;break;
                }
                case 0x0a: {
                    if(p.payload.length<1)throw new IllegalArgumentException("write address");
                    int a=p.extra<<8|(p.payload[0]&255);range(a,p.payload.length-1);
                    System.arraycopy(p.payload,1,memory,a,p.payload.length-1);reply=4;extra=p.extra;break;
                }
                case 0x0c: {
                    size(p.payload,3);int a=(p.payload[0]&255)<<8|p.payload[1]&255,n=p.payload[2]&255;
                    if(n>128)throw new IllegalArgumentException("read length");data=slice(a,n);reply=0x0e;break;
                }
                case 0x20: {
                    size(p.payload,0);put16(0xce8a,watts());byte[] id=slice(0xed,104);
                    long n=steps();for(int i=0;i<4;i++)id[0x64+i]=(byte)(n>>>(24-8*i));
                    reliable(0xed,id);data=id;reply=0x22;break;
                }
                case 0x24:size(p.payload,0);reply=0x26;break;
                case 0x32:case 0x40:case 0x42:case 0x52:case 0x60:
                    size(p.payload,104);pending=p.payload.clone();
                    collectingGifts=p.command==0x60;
                    System.arraycopy(p.payload,0x60,memory,0x15e,4);health();reply=p.command+2;break;
                case 0x38:case 0x5a:size(p.payload,0);startWalk(p.command==0x5a);reply=p.command;break;
                case 0x4e: {
                    size(p.payload,0);byte[] id=slice(0xed,104);id[0x5b]&=1;id[0x5f]=0;
                    Arrays.fill(id,4,8,(byte)0);id[10]=0;id[11]=0;reliable(0xed,id);
                    Arrays.fill(memory,0xce8c,0xcef0,(byte)0);put16(0x164,0);put16(0xce8a,0);health();status="Pokémon returned to the game";reply=0x50;break;
                }
                case 0x66:
                    size(p.payload,0);
                    if(collectingGifts){Arrays.fill(memory,0xce8c,0xcef0,(byte)0);put16(0x164,0);put16(0xce8a,0);health();collectingGifts=false;}
                    reply=0x68;status="Transfer completed";break;
                case 0x2a: {
                    size(p.payload,40);store.beforeGameReset(memory.clone());
                    memory=new Walker(null,store).snapshot();pending=null;collectingGifts=false;
                    data=new byte[40];Arrays.fill(data,(byte)0xff);reply=0x2a;status="Virtual walker reset by the game; previous save backed up";break;
                }
                case 0xf4:size(p.payload,0);disconnect();return null;
                case 0x36:case 0x44:case 0x56:case 0x64:case 0xd8:disconnect();status="Game ended the connection";return null;
                // Factory enrollment, peer play, events and internal-memory writes are
                // unimplemented until their semantics are independently validated.
                default:throw new IllegalArgumentException(String.format("Unsupported command %02X",p.command));
            }
            if(!Arrays.equals(old,memory))store.commit(memory.clone());
            byte[] out=reply<0?null:new Packet(reply,extra,session,data).encode();
            lastRequest=wire.clone();lastReply=out==null?null:out.clone(); // conformance: cache reply
            return out;
        } catch(IOException|RuntimeException e){memory=old;pending=oldPending;status=oldStatus;collectingGifts=oldGifts;throw e;}
    }
}
