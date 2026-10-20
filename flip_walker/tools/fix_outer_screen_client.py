#!/usr/bin/env python3
"""Rerunnable: Flip Walker as a client of the KYF37 outer screen API v1
(docs/ui/OUTER-SCREEN-CLIENT-API.md). Shows the walking Pokémon, today's steps and watts."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
project = root.parent
T = root / 'templates'
def patch(rel, old, new):
    p = T / rel; t = p.read_text()
    if new in t: return
    assert old in t, f'{rel}: anchor'
    p.write_text(t.replace(old, new, 1)); print('applied', rel)
# the public client library, re-packaged
sdk = (project / 'device-inspection/outer-client-api/OuterScreenClient.java').read_text()
(T / 'src/org/kyf37/walker/OuterScreenClient.java').write_text(sdk.replace('package org.kyf37.outerscreen;', 'package org.kyf37.walker;', 1))
patch('AndroidManifest.xml', '<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>',
      '<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>\n  <uses-permission android:name="org.kyf37.permission.OUTER_SCREEN_CLIENT"/>\n  <queries><package android:name="org.kyf37.subdisplay"/></queries>')
patch('src/org/kyf37/walker/PixelArt.java', '    static String plain(String text){',
      '    static String[] glyph(char c){return FONT.get(c);} // outer screen\n    static String plain(String text){')
patch('src/org/kyf37/walker/SaveFile.java', '''          public void commit(byte[] bytes)throws IOException{
            FileOutputStream out=null;
            try{out=file.startWrite();out.write(bytes);out.getFD().sync();file.finishWrite(out);}
            catch(IOException e){if(out!=null)file.failWrite(out);throw e;}
          }''', '''          public void commit(byte[] bytes)throws IOException{
            FileOutputStream out=null;
            try{out=file.startWrite();out.write(bytes);out.getFD().sync();file.finishWrite(out);}
            catch(IOException e){if(out!=null)file.failWrite(out);throw e;}
            OuterScreenPublisher.update(app,bytes);
          }''')
patch('src/org/kyf37/walker/SaveFile.java', '''        final File directory=context.getApplicationContext().getFilesDir();''',
      '''        final File directory=context.getApplicationContext().getFilesDir();
        final Context app=context.getApplicationContext();''')
patch('src/org/kyf37/walker/SaveFile.java', '''        return instance;
    }''', '''        OuterScreenPublisher.update(app,instance.snapshot());
        return instance;
    }''')
(T / 'src/org/kyf37/walker/OuterScreenPublisher.java').write_text('''package org.kyf37.walker;

import android.content.Context;
import android.util.Log;
import java.util.Arrays;

/** Shows the walking Pokémon with today's steps and watts on the outer screen (API v1, ambient
 *  frame). Sends only when the picture changes; does nothing until the user switches Flip
 *  Walker on in Settings > Outer screen. */
final class OuterScreenPublisher {
    private static OuterScreenClient client;
    private static byte[] pending, sent;

    static synchronized void update(Context context, byte[] eeprom) {
        byte[] frame = frames(eeprom);
        if (Arrays.equals(frame, sent)) return;
        pending = frame;
        if (client == null) {
            client = OuterScreenClient.bind(context, new OuterScreenClient.Listener() {
                public void onConnected(OuterScreenClient c) { flush(); }
                public void onDisconnected(OuterScreenClient c) { synchronized (OuterScreenPublisher.class) { sent = null; } }
            });
            if (client == null) return; // no outer screen service on this phone
        }
        flush();
    }

    private static synchronized void flush() {
        if (client == null || !client.isConnected() || pending == null) return;
        try {
            int r;
            if (pending.length == 0) r = client.clear();
            else {
                byte[][] two = {Arrays.copyOfRange(pending, 0, 576), Arrays.copyOfRange(pending, 576, 1152)};
                // walking animation (API level 2); a level-1 service only gets the first frame
                r = client.info().apiLevel >= 2 ? client.postAnimation(two, 500, 0) : client.post(two[0], OuterScreenClient.AMBIENT, 0);
            }
            if (r == OuterScreenClient.OK) { sent = pending; pending = null; }
            else if (r != OuterScreenClient.ERROR_DISABLED) Log.w("FlipWalker", "outer screen post: " + r);
        } catch (Exception e) { Log.w("FlipWalker", "outer screen unavailable", e); }
    }

    /** Both walking frames (2 x 576 bytes); empty means "no Pokémon: give the screen back to the clock". */
    static byte[] frames(byte[] e) {
        byte[] a = frame(e, 0);
        if (a.length == 0) return a;
        byte[] both = Arrays.copyOf(a, 1152);
        System.arraycopy(frame(e, 1), 0, both, 576, 576);
        return both;
    }

    /** 128x36 frame of walking frame `n` (0 or 1). */
    static byte[] frame(byte[] e, int n) {
        if (e == null || e.length != 65536) return new byte[0];
        int species = (e[0x8f00] & 255) | (e[0x8f01] & 255) << 8;
        if (species == 0 || species > 493) return new byte[0];
        byte[] px = new byte[OuterScreenClient.WIDTH * OuterScreenClient.HEIGHT];
        // The game's small walking sprite (32x24, 2 bits per pixel, frame 0 at 0x91be), drawn
        // 1:1 so its lines stay intact; only the darkest shade is lit, which reads as clean line art
        // on the 1-bit panel (scaling the 64x48 portrait or lighting mid-greys looked smeared).
        for (int y = 0; y < 24; y++) for (int x = 0; x < 32; x++) {
            int off = 0x91be + n * 192 + (y / 8) * 32 * 2 + x * 2, bit = y % 8;
            int shade = ((e[off] >>> bit) & 1) * 2 + ((e[off + 1] >>> bit) & 1);
            if (shade == 3) px[(y + 6) * 128 + x + 4] = 1;
        }
        long steps = ((e[0x15a] & 255L) << 24) | ((e[0x15b] & 255) << 16) | ((e[0x15c] & 255) << 8) | (e[0x15d] & 255);
        int watts = (e[0x164] & 255) << 8 | (e[0x165] & 255);
        text(px, String.valueOf(Math.min(steps, 99999)), 44, 4);
        text(px, UiText.tr("steps"), 44, 14);
        text(px, watts + " W", 44, 26);
        return OuterScreenClient.pack(px);
    }

    private static void text(byte[] px, String s, int x, int y) {
        s = PixelArt.plain(s);
        for (int i = 0; i < s.length() && x + i * 6 + 5 <= 128; i++) {
            String[] g = PixelArt.glyph(s.charAt(i));
            if (g == null) continue;
            for (int r = 0; r < 7; r++) for (int c = 0; c < 5; c++)
                if (g[r].charAt(c) == '1') px[(y + r) * 128 + x + i * 6 + c] = 1;
        }
    }
}
''')
patch('AndroidManifest.xml', '<queries><package android:name="org.kyf37.subdisplay"/></queries>',
      '<queries><package android:name="org.kyf37.subdisplay"/><package android:name="org.kyf37.pokedex"/></queries>')
patch('AndroidManifest.xml', '    <service android:name=".StepService"',
      '    <!-- outer screen side key on Flip Walker\'s page: only the system display service may send it -->\n    <receiver android:name=".OuterButtonReceiver" android:exported="true" android:permission="org.kyf37.permission.OUTER_SCREEN"><intent-filter><action android:name="org.kyf37.outerscreen.action.BUTTON"/></intent-filter></receiver>\n    <service android:name=".StepService"')
(T / 'src/org/kyf37/walker/OuterButtonReceiver.java').write_text('''package org.kyf37.walker;

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
''')
print('outer screen client staged')
