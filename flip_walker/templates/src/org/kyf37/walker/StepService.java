package org.kyf37.walker;

import android.app.*;
import android.os.*;
import android.content.*;
import android.hardware.*;

/** User-started foreground walking session. No boot receiver, no synthetic steps. */
public final class StepService extends Service implements SensorEventListener {
    private SensorManager sensors; private Walker walker; private long last=-1;
    public static volatile String sensorStatus="Walking paused";
    public static volatile boolean running;
    @Override public void onCreate(){
        super.onCreate();
        UiText.choose(getSharedPreferences("ui",0).getString("language",UiText.defaultLanguage(java.util.Locale.getDefault().toLanguageTag())));
        startForeground(37,notification(this));
        try{walker=SaveFile.get(this);}catch(Exception e){sensorStatus="Save unavailable; walking stopped";stopSelf();return;}
        sensors=(SensorManager)getSystemService(SENSOR_SERVICE);
        Sensor counter=sensors.getDefaultSensor(Sensor.TYPE_STEP_COUNTER);
        if(counter==null){sensorStatus="No step-counter sensor; no steps added";stopSelf();return;}
        // Resume from the persisted counter only during the same device boot.
        android.content.SharedPreferences prefs=getSharedPreferences("sensor",0);
        long boot=System.currentTimeMillis()-SystemClock.elapsedRealtime();
        if(Math.abs(boot-prefs.getLong("boot",0))<60000)last=prefs.getLong("counter",-1);
        try{
            if(!sensors.registerListener(this,counter,SensorManager.SENSOR_DELAY_NORMAL)){sensorStatus="Step sensor refused registration";stopSelf();}
            else {sensorStatus="Counting real steps";running=true;}
        }catch(SecurityException e){sensorStatus="Step permission required";stopSelf();}
    }
    private static Notification notification(Context c){
        NotificationManager manager=(NotificationManager)c.getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel("walk",UiText.tr("Walking steps"),NotificationManager.IMPORTANCE_LOW));
        PendingIntent open=PendingIntent.getActivity(c,0,new Intent(c,WalkerActivity.class),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(c,"walk").setSmallIcon(R.drawable.ic_walker).setContentTitle(UiText.tr("Flip Walker is counting steps"))
                .setContentText(UiText.tr("Open Flip Walker to pause")).setContentIntent(open).setOngoing(true).build();
    }
    static void refreshLanguage(Context c){if(running)((NotificationManager)c.getSystemService(NOTIFICATION_SERVICE)).notify(37,notification(c));}
    @Override public int onStartCommand(Intent intent,int flags,int id){return START_NOT_STICKY;}
    @Override public void onSensorChanged(SensorEvent e){
        android.content.SharedPreferences daily=getSharedPreferences("sensor",0);
        java.util.Calendar calendar=java.util.Calendar.getInstance();
        long day=java.time.LocalDate.of(calendar.get(java.util.Calendar.YEAR),calendar.get(java.util.Calendar.MONTH)+1,calendar.get(java.util.Calendar.DAY_OF_MONTH)).toEpochDay();
        long previousDay=daily.getLong("day",day);
        if(day>previousDay){try{walker.advanceDays((int)Math.min(65535,day-previousDay));}catch(Exception failure){sensorStatus="Daily save failed";stopSelf();return;}}
        daily.edit().putLong("day",day).commit();
        long value=(long)e.values[0],difference=last<0?0:value-last;
        if(difference>=0 && difference<=10000){
            try{walker.addSteps((int)difference);}catch(Exception failure){sensorStatus="Save failed; walking paused";stopSelf();return;}
        }
        last=value;
        getSharedPreferences("sensor",0).edit().putLong("counter",value)
            .putLong("boot",System.currentTimeMillis()-SystemClock.elapsedRealtime()).commit();
    }
    @Override public void onAccuracyChanged(Sensor s,int accuracy){}
    @Override public IBinder onBind(Intent i){return null;}
    @Override public void onDestroy(){running=false;if(sensors!=null)sensors.unregisterListener(this);last=-1;
        getSharedPreferences("sensor",0).edit().remove("counter").apply();
        if(sensorStatus.equals("Counting real steps"))sensorStatus="Walking paused";super.onDestroy();}
}
