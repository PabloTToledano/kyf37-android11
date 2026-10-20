package org.kyf37.walker;

import java.io.IOException;
import java.util.concurrent.ArrayBlockingQueue;

/** One owner of the request/reply transport; UART waits never stall the H8 CPU. */
public final class EmulatedIr implements AutoCloseable {
    public interface Link extends AutoCloseable {
        void send(byte[] b) throws IOException;
        byte[] read(int timeout) throws IOException;
        void close();
    }
    private final Link link;
    private final ArrayBlockingQueue<byte[]> tx=new ArrayBlockingQueue<>(32),rx=new ArrayBlockingQueue<>(32),sent=new ArrayBlockingQueue<>(32);
    private volatile boolean open=true;
    private volatile IOException failure;
    private final Thread worker;
    public EmulatedIr(Link link){
        this.link=link;
        worker=new Thread(this::pump,"walker-ir-transport");worker.setDaemon(true);worker.start();
    }
    private void pump(){
        try{
            while(open){
                byte[] b;
                while(open&&(b=tx.poll())!=null){link.send(b);if(!sent.offer(b))throw new IOException("IR completion queue full");}
                if(!open)break;
                b=link.read(2);
                if(b.length>0&&!rx.offer(b))throw new IOException("IR receive queue full");
            }
        }catch(IOException e){if(open)failure=e;}
        catch(RuntimeException e){if(open)failure=new IOException("IR transport stopped",e);}
        finally{open=false;link.close();}
    }
    private void check()throws IOException{if(failure!=null)throw failure;if(!open)throw new IOException("IR closed");}
    public void send(byte[] b)throws IOException{check();if(!tx.offer(b.clone()))throw new IOException("IR transmit queue full");}
    public byte[] poll()throws IOException{check();return rx.poll();}
    public byte[] sent()throws IOException{check();return sent.poll();}
    public void close(){
        open=false;
        try{worker.join(3000);}catch(InterruptedException e){Thread.currentThread().interrupt();}
        // LocalSocket read has a 2.5 s deadline. This also closes a wedged process transport.
        if(worker.isAlive()){link.close();worker.interrupt();}
    }
}
