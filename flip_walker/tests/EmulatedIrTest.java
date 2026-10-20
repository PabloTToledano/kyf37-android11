package org.kyf37.walker;
import java.io.IOException;
import java.util.concurrent.*;
import java.util.*;
public class EmulatedIrTest {
 static void check(boolean b){if(!b)throw new AssertionError();}
 static class Fake implements EmulatedIr.Link {
  CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
  List<Integer> sent=Collections.synchronizedList(new ArrayList<>());volatile boolean closed,fail;int reads;
  public void send(byte[] b){sent.add((int)b[0]);}
  public byte[] read(int timeout)throws IOException{entered.countDown();try{release.await();Thread.sleep(2);}catch(InterruptedException e){throw new IOException(e);}if(fail)throw new IOException("synthetic UART failure");return reads++==0?new byte[]{7}:new byte[0];}
  public void close(){closed=true;release.countDown();}
 }
 public static void main(String[] args)throws Exception{
  Fake f=new Fake();EmulatedIr ir=new EmulatedIr(f);check(f.entered.await(1,TimeUnit.SECONDS));
  // The worker is deliberately blocked in UART read. CPU-facing methods must still finish.
  ExecutorService cpu=Executors.newSingleThreadExecutor();
  Future<?> nonblocking=cpu.submit(()->{try{byte[] b={1};ir.send(b);b[0]=99;ir.send(new byte[]{2});check(ir.poll()==null);}catch(IOException e){throw new RuntimeException(e);}});
  nonblocking.get(200,TimeUnit.MILLISECONDS);f.release.countDown();
  long until=System.nanoTime()+TimeUnit.SECONDS.toNanos(2);while(f.sent.size()<2&&System.nanoTime()<until)Thread.sleep(2);
  check(f.sent.equals(Arrays.asList(1,2)));check(ir.sent()[0]==1);check(ir.sent()[0]==2);
  check(ir.poll()[0]==7);ir.close();check(f.closed);cpu.shutdownNow();
  Fake bad=new Fake();bad.fail=true;bad.release.countDown();EmulatedIr broken=new EmulatedIr(bad);Thread.sleep(20);
  boolean rejected=false;try{broken.poll();}catch(IOException e){rejected=true;}check(rejected);broken.close();check(bad.closed);
  System.out.println("EMULATED_IR_OK: nonblocking CPU, ordered cloned TX, RX, failures, close");
 }
}
