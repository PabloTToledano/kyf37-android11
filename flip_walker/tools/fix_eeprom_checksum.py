from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'templates/src/org/kyf37/walker/Walker.java'
s=p.read_text().replace('int sum=0;for(byte b:data)', 'int sum=1;for(byte b:data)');p.write_text(s)
p=r/'templates/src/org/kyf37/walker/EepromRepair.java'
p.write_text('''package org.kyf37.walker;

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
''')
p=r/'templates/src/org/kyf37/walker/SaveFile.java';s=p.read_text().replace('checksum-v1.done','checksum-v2.done');needle='        instance=new Walker(saved, new Walker.Store(){'
if 'checksum-v2.done' not in s:
 s=s.replace(needle,'''        File marker=new File(directory,"checksum-v2.done");
        if(saved!=null&&!marker.exists()){
            File original=new File(directory,"walker-before-emulator.eeprom");
            byte[] before=null;
            if(original.exists()&&original.length()==65536){
                try(InputStream in=new FileInputStream(original);ByteArrayOutputStream out=new ByteArrayOutputStream()){
                    byte[] b=new byte[4096];int n;while((n=in.read(b))>=0)out.write(b,0,n);before=out.toByteArray();
                }
            }
            byte[] repaired=EepromRepair.repair(saved,before);
            if(!java.util.Arrays.equals(saved,repaired)){
                File backup=new File(directory,"walker-before-checksum-v1.eeprom");
                if(!backup.exists())EmulatedWalkerActivity.atomicWrite(backup,saved);
                FileOutputStream out=null;
                try{out=file.startWrite();out.write(repaired);out.getFD().sync();file.finishWrite(out);}
                catch(IOException e){if(out!=null)file.failWrite(out);throw e;}
                saved=repaired;
                android.util.Log.i("Pokewalker","EEPROM checksum migration restored validated records; original preserved");
            }
            EmulatedWalkerActivity.atomicWrite(marker,new byte[]{1});
        }
'''+needle)
p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('versionCode="7"','versionCode="8"').replace('0.7-core-timing','0.8-eeprom-checksum');p.write_text(s)
