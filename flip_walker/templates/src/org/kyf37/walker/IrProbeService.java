package org.kyf37.walker;

import android.app.*;
import android.content.*;
import android.os.*;
import android.util.AtomicFile;
import java.io.*;

/** Private, explicitly invoked phone-side diagnostic; never accesses a game save. */
public final class IrProbeService extends Service {
    @Override public int onStartCommand(Intent intent,int flags,int id){
        NotificationManager manager=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel("ir-check","Infrared check",NotificationManager.IMPORTANCE_LOW));
        startForeground(38,new Notification.Builder(this,"ir-check").setSmallIcon(R.drawable.ic_walker)
            .setContentTitle("Flip Walker infrared check").setContentText("Checking the phone connection").build());
        new Thread(()->{
            String result;
            try(IrSession session=new IrSession(this)){
                session.send(new byte[]{0x56});
                byte[] received=session.read();
                result="APP_IR_PROBE_OK\ntransport="+(session.companion?"root-companion":"su")+
                    "\nuart_initialized=true\nadvertisement_tx_accepted=true\nreceived_bytes="+received.length+
                    "\nreal_game_verified=false\ngame_save_accessed=false\n";
            }catch(Exception e){result="APP_IR_PROBE_FAILED\n"+e.getMessage()+"\nreal_game_verified=false\ngame_save_accessed=false\n";}
            AtomicFile file=new AtomicFile(new File(getFilesDir(),"last-ir-probe.txt"));FileOutputStream out=null;
            try{out=file.startWrite();out.write(result.getBytes("UTF-8"));file.finishWrite(out);}
            catch(IOException e){if(out!=null)file.failWrite(out);}
            stopForeground(true);stopSelf(id);
        },"FlipWalkerIrCheck").start();
        return START_NOT_STICKY;
    }
    @Override public IBinder onBind(Intent intent){return null;}
}
