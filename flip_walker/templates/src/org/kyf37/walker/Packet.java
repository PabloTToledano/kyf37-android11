package org.kyf37.walker;

import java.util.Arrays;

/** Raw SIR packets. Header byte order and checksum follow Dmitry.GR's research. */
public final class Packet {
    public final int command, extra;
    public final byte[] session, payload;
    public Packet(int command, int extra, byte[] session, byte[] payload) {
        if(session.length != 4 || payload.length > 255) throw new IllegalArgumentException("packet size");
        this.command=command&255; this.extra=extra&255;
        this.session=session.clone(); this.payload=payload.clone();
    }
    public static int checksum(byte[] plain) {
        long sum=2;
        for(int i=0;i<plain.length;i++) if(i!=2 && i!=3) sum+=(plain[i]&255L) << ((i&1)==0?8:0);
        while((sum>>>16)!=0) sum=(sum&65535)+(sum>>>16);
        return (int)(((sum&255)<<8)|(sum>>>8));
    }
    public byte[] encode() {
        byte[] b=new byte[8+payload.length]; b[0]=(byte)command; b[1]=(byte)extra;
        System.arraycopy(session,0,b,4,4); System.arraycopy(payload,0,b,8,payload.length);
        int crc=checksum(b); b[2]=(byte)(crc>>>8); b[3]=(byte)crc;
        for(int i=0;i<b.length;i++) b[i]^=(byte)0xaa;
        return b;
    }
    public static Packet decode(byte[] wire) {
        if(wire.length<8 || wire.length>263) throw new IllegalArgumentException("packet length");
        byte[] b=wire.clone(); for(int i=0;i<b.length;i++) b[i]^=(byte)0xaa;
        if(checksum(b)!=((b[2]&255)<<8 | b[3]&255)) throw new IllegalArgumentException("checksum");
        return new Packet(b[0],b[1],Arrays.copyOfRange(b,4,8),Arrays.copyOfRange(b,8,b.length));
    }
    public static byte[] decompress(byte[] b) {
        if(b.length<4 || b[0]!=0x10 || (b[1]&255)!=128 || b[2]!=0 || b[3]!=0)
            throw new IllegalArgumentException("LZ10 header");
        byte[] out=new byte[128]; int pos=4, n=0;
        while(n<128) {
            if(pos>=b.length) throw new IllegalArgumentException("LZ flags");
            int flags=b[pos++]&255;
            for(int bit=7;bit>=0 && n<128;bit--) {
                if((flags&(1<<bit))==0) {
                    if(pos>=b.length) throw new IllegalArgumentException("LZ literal");
                    out[n++]=b[pos++];
                } else {
                    if(pos+1>=b.length) throw new IllegalArgumentException("LZ reference");
                    int a=b[pos++]&255, c=b[pos++]&255, len=(a>>>4)+3, distance=((a&15)<<8|c)+1;
                    if(distance>n || n+len>128) throw new IllegalArgumentException("LZ bounds");
                    for(int j=0;j<len;j++) {out[n]=out[n-distance]; n++;}
                }
            }
        }
        return out;
    }
}
