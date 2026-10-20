package org.kyf37.walker;

import java.util.Arrays;

/** Upgrade only provable legacy records; never synthesize identity or counters. */
public final class EepromRepair {
    private static final int[][] RECORDS={{0x83,0x183,40},{0xed,0x1ed,104},{0x156,0x256,24},{0x16f,0x26f,2}};
    private static int sum(byte[] b,int a,int n){int v=1;for(int i=0;i<n;i++)v+=b[a+i]&255;return v&255;}
    private static boolean valid(byte[] b,int a,int n){return (b[a+n]&255)==sum(b,a,n);}
    private static boolean erased(byte[] b,int a,int n){for(int i=0;i<=n;i++)if(b[a+i]!=(byte)255)return false;return true;}
    private static boolean legacy(byte[] b,int a,int c,int n){
        if((b[a+n]&255)!=((sum(b,a,n)-1)&255))return false;
        for(int i=0;i<=n;i++)if(b[a+i]!=b[c+i])return false;
        return true;
    }
    public static byte[] repair(byte[] saved,byte[] beforeEmulator){
        if(saved.length!=65536)throw new IllegalArgumentException("EEPROM size");
        byte[] out=saved.clone();
        boolean recoveredIdentity=false;
        // Only the original safety copy can recover firmware-rejected, completely erased identity.
        int a=0xed,c=0x1ed,n=104;
        if(beforeEmulator!=null&&beforeEmulator.length==65536&&erased(out,a,n)&&erased(out,c,n)
           &&beforeEmulator[a+0x5b]!=(byte)255&&(beforeEmulator[a+0x5b]&1)!=0
           &&(valid(beforeEmulator,a,n)||legacy(beforeEmulator,a,c,n))){
            System.arraycopy(beforeEmulator,a,out,a,n);System.arraycopy(beforeEmulator,a,out,c,n);
            out[a+n]=out[c+n]=(byte)sum(out,a,n);recoveredIdentity=true;
        }
        boolean sameIdentity=beforeEmulator!=null&&beforeEmulator.length==65536
            &&Arrays.equals(Arrays.copyOfRange(out,0xed,0x155),Arrays.copyOfRange(beforeEmulator,0xed,0x155))
            &&(valid(out,0xed,104)||legacy(out,0xed,0x1ed,104));
        for(int[] rec:RECORDS){a=rec[0];c=rec[1];n=rec[2];
            if(valid(out,a,n)||valid(out,c,n))continue;
            if(legacy(out,a,c,n)){out[a+n]=out[c+n]=(byte)sum(out,a,n);continue;}
            if((recoveredIdentity||sameIdentity)&&erased(out,a,n)&&erased(out,c,n)
                &&(valid(beforeEmulator,a,n)||legacy(beforeEmulator,a,c,n))){
                System.arraycopy(beforeEmulator,a,out,a,n);System.arraycopy(beforeEmulator,a,out,c,n);
                out[a+n]=out[c+n]=(byte)sum(out,a,n);
            }
        }
        return out;
    }
}
