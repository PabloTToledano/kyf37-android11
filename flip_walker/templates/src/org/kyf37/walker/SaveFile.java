package org.kyf37.walker;

import android.content.Context;
import android.util.AtomicFile;
import java.io.*;

/** One process-wide walker, shared with step service. Atomic file, never a partition. */
public final class SaveFile {
    private static Walker instance;
    public static synchronized Walker get(Context context) throws IOException {
        if(instance!=null)return instance;
        final File directory=context.getApplicationContext().getFilesDir();
        final Context app=context.getApplicationContext();
        final AtomicFile file=new AtomicFile(new File(directory,"walker.eeprom"));
        byte[] saved=null;
        if(file.getBaseFile().exists() || new File(file.getBaseFile().getPath()+".bak").exists()){
            try(InputStream in=file.openRead();ByteArrayOutputStream out=new ByteArrayOutputStream()){
                byte[] block=new byte[4096];int n;while((n=in.read(block))>=0)out.write(block,0,n);saved=out.toByteArray();
            }
            if(saved.length!=65536)throw new IOException("Save has wrong size; preserved for recovery");
        }
        File marker=new File(directory,"checksum-v2.done");
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
        instance=new Walker(saved, new Walker.Store(){
          public void beforeGameReset(byte[] bytes)throws IOException{
            File backup=new File(directory,"walker-before-game-reset-"+System.currentTimeMillis()+".eeprom");
            try(FileOutputStream out=new FileOutputStream(backup)){out.write(bytes);out.getFD().sync();}
          }
          public void commit(byte[] bytes)throws IOException{
            FileOutputStream out=null;
            try{out=file.startWrite();out.write(bytes);out.getFD().sync();file.finishWrite(out);}
            catch(IOException e){if(out!=null)file.failWrite(out);throw e;}
            OuterScreenPublisher.update(app,bytes);
          }
        });
        OuterScreenPublisher.update(app,instance.snapshot());
        return instance;
    }
}
