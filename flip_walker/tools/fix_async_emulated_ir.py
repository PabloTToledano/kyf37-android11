from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'templates/src/org/kyf37/walker/EmulatedIr.java'
p.write_text('''package org.kyf37.walker;

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
''')
p=r/'templates/src/org/kyf37/walker/IrSession.java';s=p.read_text().replace('implements AutoCloseable, WalkerReader.Link','implements AutoCloseable, WalkerReader.Link, EmulatedIr.Link')
if 'read(int timeout)' not in s:s=s.replace('    public byte[] read()throws IOException', '    public byte[] read(int timeout)throws IOException{return exchange(2,timeout,null);}\n    public byte[] read()throws IOException')
p.write_text(s)
p=r/'templates/src/org/kyf37/walker/EmulatedWalkerActivity.java';s=p.read_text().replace('IrSession ir = null;','EmulatedIr ir = null;').replace('ir = new IrSession(this);','ir = new EmulatedIr(new IrSession(this));')
s=s.replace('if (ir != null) { trace("TX", burst); ir.send(burst); irTx++;\n                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }','if (ir != null) ir.send(burst);')
s=s.replace('''                            byte[] rx = ir.exchange(2, 2, null);
                            if (rx.length > 0) { trace("RX", rx); PwCore.irPush(rx); irRx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            else if''','''                            byte[] completed;
                            while ((completed = ir.sent()) != null) { trace("TX", completed); irTx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            byte[] rx;
                            while ((rx = ir.poll()) != null) { trace("RX", rx); PwCore.irPush(rx); irRx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            if''')
p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('versionCode="8"','versionCode="9"').replace('0.8-eeprom-checksum','0.9-ir-timing');p.write_text(s)
