package org.kyf37.walker;

import java.io.IOException;
import java.util.Arrays;

/** Bounded master-side framing. read() is read-only; WalkerTools invokes explicit advanced commands. */
public final class WalkerReader {
    public interface Link { void send(byte[] wire) throws IOException; byte[] read() throws IOException; }
    public interface Cancel { boolean requested(); }
    public interface Progress { void bytesRead(int bytes); }
    public interface Clock { long milliseconds(); }
    public static final class Identity {
        private final byte[] raw;
        public final int trainerId, secretId;
        public final String trainer;
        public final boolean paired, hasPokemon;
        public final long lastSync, steps;
        public Identity(byte[] bytes) {
            if(bytes.length!=104)throw new IllegalArgumentException("Identity must be 104 bytes");
            raw=bytes.clone();trainerId=le16(raw,12);secretId=le16(raw,14);
            paired=(raw[91]&1)!=0;hasPokemon=(raw[91]&2)!=0;
            lastSync=be32(raw,96);steps=be32(raw,100);
            StringBuilder name=new StringBuilder();
            for(int i=0;i<8;i++){
                int code=le16(raw,72+i*2);if(code==65535)break;
                if(code>=0xa2&&code<=0xab)name.append((char)('0'+code-0xa2));
                else if(code>=0xac&&code<=0xc5)name.append((char)('A'+code-0xac));
                else if(code>=0xc6&&code<=0xdf)name.append((char)('a'+code-0xc6));
                else if(code>=0x121&&code<=0x12a)name.append((char)('0'+code-0x121));
                else if(code>=0x12b&&code<=0x144)name.append((char)('A'+code-0x12b));
                else if(code>=0x145&&code<=0x15e)name.append((char)('a'+code-0x145));
                else name.append('?');
            }
            trainer=name.toString();
        }
        public byte[] bytes(){return raw.clone();}
    }
    public static final class Result {
        public final Identity identity;
        private final byte[] eeprom;
        Result(Identity id,byte[] bytes){identity=id;eeprom=bytes==null?null:bytes.clone();}
        public byte[] snapshot(){return eeprom==null?null:eeprom.clone();}
    }
    private final Link link;private final Cancel cancel;private final Clock clock;
    private long operationDeadline;
    private byte[] session;private byte[] pending=new byte[0];
    public WalkerReader(Link link,Cancel cancel){this(link,cancel,()->System.nanoTime()/1000000L);}
    public WalkerReader(Link link,Cancel cancel,Clock clock){this.link=link;this.cancel=cancel;this.clock=clock;}
    private void check()throws IOException {if(operationDeadline!=0 && clock.milliseconds()>=operationDeadline)throw new IOException("Read session timed out; earlier captures preserved");if(cancel.requested()||Thread.currentThread().isInterrupted())throw new IOException("Read cancelled");}
    private void send(int command,byte[] data)throws IOException {
        check();link.send(new Packet(command,1,session==null?new byte[4]:session,data).encode());
    }
    private void advertise()throws IOException {
        long deadline=clock.milliseconds()+20000;
        while(clock.milliseconds()<deadline){
            check();byte[] bytes=link.read();
            // The walker sends raw 0x56 while its CONNECT screen is open.
            if(bytes.length>0){boolean onlyAdvertisement=true;for(byte b:bytes)if(b!=0x56)onlyAdvertisement=false;
                if(onlyAdvertisement)return;}
        }
        throw new IOException("No real Pokewalker found. Choose CONNECT and try again.");
    }
    private Packet receive(int command,int payloadSize,boolean handshake)throws IOException {
        return receiveTools(command,payloadSize,handshake,2,false);
    }
    Packet receiveTools(int command,int payloadSize,boolean handshake,int extra,boolean stream)throws IOException {
        int length=payloadSize+8;long deadline=clock.milliseconds()+2000;
        while(clock.milliseconds()<deadline){
            check();
            while(pending.length>=length){
                byte[] candidate=Arrays.copyOfRange(pending,0,length);
                try{
                    Packet packet=Packet.decode(candidate);
                    if(packet.command==command && (extra<0||packet.extra==extra) && (handshake||Arrays.equals(packet.session,session))){
                        pending=Arrays.copyOfRange(pending,length,pending.length);
                        if(!stream && pending.length!=0)throw new IOException("Extra infrared data; retry a new read");
                        return packet;
                    }
                }catch(IllegalArgumentException rejected){}
                pending=Arrays.copyOfRange(pending,1,pending.length);
            }
            byte[] more=link.read();if(more.length>263)throw new IOException("Oversized infrared input");
            if(pending.length+more.length>526)throw new IOException("Infrared input overflow");
            byte[] combined=Arrays.copyOf(pending,pending.length+more.length);
            System.arraycopy(more,0,combined,pending.length,more.length);pending=combined;
        }
        throw new IOException("Walker reply timed out. Start a new read.");
    }
    /** One fresh session per read. Never retries indistinguishable EEPROM page replies. */
    public Result read(boolean fullBackup,Progress progress)throws IOException {
        if(session!=null)throw new IOException("Use a fresh reader for each connection");
        operationDeadline=clock.milliseconds()+180000;
        try{
            advertise();send(0xfa,new byte[0]);session=receive(0xf8,0,true).session.clone();
            send(0x20,new byte[0]);Identity identity=new Identity(receive(0x22,104,false).payload);
            byte[] snapshot=null;
            if(fullBackup){
                snapshot=new byte[65536];progress.bytesRead(0);
                for(int address=0;address<65536;address+=128){
                    send(0x0c,new byte[]{(byte)(address>>>8),(byte)address,(byte)128});
                    byte[] page=receive(0x0e,128,false).payload;
                    System.arraycopy(page,0,snapshot,address,128);progress.bytesRead(address+128);
                }
            }
            check();return new Result(identity,snapshot);
        }finally{
            if(session!=null)try{link.send(new Packet(0xf4,1,session,new byte[0]).encode());}catch(IOException ignored){}
        }
    }
    // Explicit advanced operations use the same bounded framing and session checks.
    void beginTools()throws IOException {
        if(session!=null)throw new IOException("Use a fresh connection");
        operationDeadline=clock.milliseconds()+180000;
        advertise();send(0xfa,new byte[0]);session=receive(0xf8,0,true).session.clone();
    }
    Identity toolIdentity()throws IOException {send(0x20,new byte[0]);return new Identity(receive(0x22,104,false).payload);}
    byte[] toolRead(int address,int size)throws IOException {
        if(address<0||size<1||size>128||address+size>65536)throw new IOException("Invalid EEPROM range");
        send(0x0c,new byte[]{(byte)(address>>>8),(byte)address,(byte)size});return receive(0x0e,size,false).payload;
    }
    byte[] toolBackup(Progress progress)throws IOException {
        byte[] b=new byte[65536];for(int a=0;a<b.length;a+=128){System.arraycopy(toolRead(a,128),0,b,a,128);progress.bytesRead(a+128);}return b;
    }
    void toolCommand(int command,int extra,byte[] payload,int ack,boolean stream)throws IOException {
        check();link.send(new Packet(command,extra,session,payload).encode());receiveTools(ack,0,false,-1,stream);
    }
    void toolWrite(int address,byte[] data)throws IOException {
        if(address<0||address+data.length>65536)throw new IOException("Invalid write range");
        for(int at=0;at<data.length;){int n=Math.min(127,data.length-at);byte[] b=new byte[n+1];b[0]=(byte)address;
            System.arraycopy(data,at,b,1,n);toolCommand(0x0a,address>>>8,b,4,false);at+=n;address+=n;}
    }
    void toolExploit(byte[] payload,boolean stream)throws IOException {
        toolCommand(6,0xf9,payload,6,false);toolCommand(6,0xf7,WalkerCatalog.TRIGGER_EXPLOIT,6,stream);
    }
    void finishTools(){if(session!=null)try{link.send(new Packet(0xf4,1,session,new byte[0]).encode());}catch(IOException ignored){}}
    public static int le16(byte[] b,int a){return (b[a]&255)|((b[a+1]&255)<<8);}
    public static int be16(byte[] b,int a){return ((b[a]&255)<<8)|(b[a+1]&255);}
    public static long be32(byte[] b,int a){return ((b[a]&255L)<<24)|((b[a+1]&255L)<<16)|((b[a+2]&255L)<<8)|(b[a+3]&255L);}
}
