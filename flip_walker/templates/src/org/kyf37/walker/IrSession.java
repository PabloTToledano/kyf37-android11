package org.kyf37.walker;

import java.io.*;
import java.util.concurrent.*;
import android.content.Context;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;

/** Bounded process transport; root is requested only after pressing Connect. */
public final class IrSession implements AutoCloseable, WalkerReader.Link, EmulatedIr.Link {
    private final Process process;
    private final LocalSocket socket;
    public final boolean companion;
    private final DataInputStream in;
    private final DataOutputStream out;
    private volatile boolean closed;
    public IrSession(Context context) throws IOException {
        String binary=context.getApplicationInfo().nativeLibraryDir+"/libwalker_ir.so";
        if(!binary.matches("/[A-Za-z0-9_./=+~:-]+"))throw new IOException("Unexpected installed helper path");
        // A bundled system APK may rely on the companion's installed executable.
        if(!new java.io.File(binary).canExecute() && new java.io.File("/system/bin/kyf37-walker-ir").canExecute())binary="/system/bin/kyf37-walker-ir";
        LocalSocket candidate=new LocalSocket();Process launched=null;
        try{
            candidate.connect(new LocalSocketAddress("kyf37.walker.ir",LocalSocketAddress.Namespace.ABSTRACT));
            if(candidate.getPeerCredentials().getUid()!=0)throw new IOException("Infrared companion must run as root");
            candidate.setSoTimeout(12000);
        }catch(IOException unavailable){try{candidate.close();}catch(IOException ignored){}candidate=null;}
        if(candidate==null){
            String rootCommand="su";
            for(String path:new String[]{"/sbin/su","/debug_ramdisk/su","/system/bin/su","/system/xbin/su"})
                if(new java.io.File(path).canExecute()){rootCommand=path;break;}
            try{launched=new ProcessBuilder(rootCommand,"-c","exec '"+binary+"' --session").start();}
            catch(IOException e){throw new IOException("Infrared unavailable: root access could not start",e);}
        }
        socket=candidate;process=launched;
        companion=socket!=null;
        in=new DataInputStream(socket==null?process.getInputStream():socket.getInputStream());
        out=new DataOutputStream(socket==null?process.getOutputStream():socket.getOutputStream());
        ExecutorService startup=Executors.newSingleThreadExecutor();
        Future<String> ready=startup.submit(()->{byte[] b=new byte[5];in.readFully(b);return new String(b,"US-ASCII");});
        try{if(!"PWIR1".equals(ready.get(12,TimeUnit.SECONDS)))throw new IOException("Unexpected IR helper response");if(socket!=null)socket.setSoTimeout(2500);}
        catch(Exception e){close();throw new IOException("Infrared unavailable: root, UART arbitration or helper failed",e);}
        finally{startup.shutdownNow();}
    }
    public byte[] exchange(int op,int value,byte[] data)throws IOException {
        if(closed)throw new IOException("IR closed");out.writeByte(op);out.writeShort(value);if(data!=null)out.write(data);out.flush();
        int n=in.readUnsignedShort();if(n>263)throw new IOException("Oversized IR frame");byte[] b=new byte[n];in.readFully(b);return b;
    }
    public void send(byte[] data)throws IOException{exchange(1,data.length,data);}
    public byte[] read(int timeout)throws IOException{return exchange(2,timeout,null);}
    public byte[] read()throws IOException{return exchange(2,50,null);}
    @Override public void close(){
        if(closed)return;closed=true;
        try{out.write(new byte[]{3,0,0});out.flush();out.close();}catch(Exception ignored){}
        try{in.close();}catch(Exception ignored){}
        if(socket!=null)try{socket.close();}catch(IOException ignored){}
        if(process!=null)process.destroy();
    }
}
