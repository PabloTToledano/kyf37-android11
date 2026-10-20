package org.kyf37.walker;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.res.AssetFileDescriptor;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.util.Log;

/** Side key pressed on Flip Walker's outer-screen page: play the walking Pokémon's cry, read
 *  from the Pokédex app's assets (cries/<national number>.ogg). */
public final class OuterButtonReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        final PendingResult done = goAsync();
        try {
            int species = SaveFile.get(context).species();
            if (species < 1 || species > 493) { done.finish(); return; }
            Context pokedex = context.createPackageContext("org.kyf37.pokedex", 0);
            AssetFileDescriptor fd = pokedex.getAssets().openFd("cries/" + species + ".ogg");
            final MediaPlayer player = new MediaPlayer();
            player.setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build());
            try { player.setDataSource(fd.getFileDescriptor(), fd.getStartOffset(), fd.getLength()); } finally { fd.close(); }
            MediaPlayer.OnCompletionListener end = p -> { p.release(); done.finish(); };
            player.setOnCompletionListener(end);
            player.setOnErrorListener((p, what, extra) -> { end.onCompletion(p); return true; });
            player.prepare();
            player.start();
        } catch (Exception e) {
            Log.w("FlipWalker", "cry unavailable (is the Pokédex app installed?)", e);
            done.finish();
        }
    }
}
