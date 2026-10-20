package org.kyf37.walker;

import android.content.Context;
import android.util.AtomicFile;
import java.io.*;
import java.util.*;

/** Captured device data is separate from walker.eeprom and never auto-imported. */
public final class ReaderFiles {
    private final File directory;
    public ReaderFiles(Context c)throws IOException{
        directory=new File(c.getApplicationContext().getFilesDir(),"real-pokewalker");
        if(!directory.isDirectory()&&!directory.mkdirs())throw new IOException("Cannot create readback folder");
    }
    public void identity(WalkerReader.Identity identity)throws IOException{
        AtomicFile file=new AtomicFile(new File(directory,"last-identity.bin"));FileOutputStream out=null;
        try{out=file.startWrite();out.write(identity.bytes());out.getFD().sync();file.finishWrite(out);}
        catch(IOException e){if(out!=null)file.failWrite(out);throw e;}
    }
    public WalkerReader.Identity identity()throws IOException{
        AtomicFile f=new AtomicFile(new File(directory,"last-identity.bin"));
        if(!f.getBaseFile().exists()&&!new File(f.getBaseFile()+".bak").exists())return null;
        try(InputStream in=f.openRead()){return new WalkerReader.Identity(readExact(in,104));}
    }
    public String save(byte[] snapshot)throws IOException{
        return saveCapture(snapshot,65536,"pokewalker-");
    }
    public String saveRom(byte[] snapshot)throws IOException {return saveCapture(snapshot,49152,"rom-");}
    private String saveCapture(byte[] snapshot,int size,String prefix)throws IOException {
        if(snapshot.length!=size)throw new IOException("Incomplete capture; not saved");
        String name=prefix+System.currentTimeMillis()+"-"+UUID.randomUUID()+".bin";
        File part=new File(directory,name+".partial"),complete=new File(directory,name);
        if(!part.createNewFile())throw new IOException("Readback filename collision");
        try{
            try(FileOutputStream out=new FileOutputStream(part)){out.write(snapshot);out.getFD().sync();}
            if(!part.renameTo(complete))throw new IOException("Could not finish EEPROM backup");
            return name;
        }finally{if(part.exists())part.delete();}
    }
    public byte[] latest()throws IOException{return latestCapture("pokewalker-",65536);}
    public byte[] latestRom()throws IOException{return latestCapture("rom-",49152);}
    private byte[] latestCapture(String prefix,int size)throws IOException{
        File[] files=directory.listFiles((dir,name)->name.startsWith(prefix)&&name.endsWith(".bin"));
        if(files==null||files.length==0)return null;
        Arrays.sort(files,(a,b)->b.getName().compareTo(a.getName()));
        try(InputStream in=new FileInputStream(files[0])){return readExact(in,size);}
    }
    private static byte[] readExact(InputStream in,int size)throws IOException{
        byte[] b=new byte[size];int at=0,n;
        while(at<size && (n=in.read(b,at,size-at))>0)at+=n;
        if(at!=size||in.read()!=-1)throw new IOException("Readback file has wrong size; preserved");return b;
    }
}
