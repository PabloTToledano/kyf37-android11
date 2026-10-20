package org.kyf37.walker;

import android.app.Activity;
import android.content.Context;
import android.graphics.*;
import android.os.*;
import android.view.*;
import java.io.*;
import java.util.Arrays;

/** Full emulation mode: the user's own Pokéwalker ROM dump runs unmodified; its LCD fills
 *  the screen, LEFT/OK/RIGHT are the walker's three buttons and the walker's IR port is the
 *  phone's IrDA transceiver (opened only while the firmware is transmitting). */
public final class EmulatedWalkerActivity extends Activity {
    static final String ROM = "walker-rom.bin", EEPROM = "emulated-walker.eeprom";
    private static final Object CORE_LOCK = new Object();
    private volatile int emulationGeneration;
    private final Object lock = new Object();
    private final byte[] lcd = new byte[PwCore.W * PwCore.H];
    private volatile int keys;
    private final EmulatedButtons buttons = new EmulatedButtons();
    private volatile boolean running;
    private volatile String status = "", irState = "IR idle";
    private volatile int irTx, irRx;
    private Thread thread;
    private Walker shared;
    private File own;
    private LcdView view;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        view = new LcdView(this);
        setContentView(view);
        view.setFocusable(true); view.requestFocus();
        if (!new File(getFilesDir(), ROM).exists() && checkSelfPermission(android.Manifest.permission.READ_EXTERNAL_STORAGE) != android.content.pm.PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{android.Manifest.permission.READ_EXTERNAL_STORAGE}, 1);
    }

    @Override public void onRequestPermissionsResult(int code, String[] p, int[] r) { recreate(); }

    @Override protected void onResume() {
        super.onResume();
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        running = true;
        keys = 0; buttons.clear();
        final int generation = ++emulationGeneration;
        thread = new Thread(() -> emulate(generation), "pokewalker");
        thread.setPriority(Thread.MAX_PRIORITY);
        thread.start();
    }

    @Override protected void onPause() {
        super.onPause();
        running = false; ++emulationGeneration; keys = 0;
        buttons.clear();
        try { if (thread != null) thread.join(2000); } catch (InterruptedException ignored) {}
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    static byte[] loadRom(Context c) throws IOException {
        File own = new File(c.getFilesDir(), ROM);
        if (!own.exists()) {
            // the owner's dump, imported once from the shared storage root
            File shared = new File(Environment.getExternalStorageDirectory(), "pokewalker-rom.bin");
            if (!shared.canRead()) throw new IOException("Copy your walker ROM dump to the phone as pokewalker-rom.bin");
            byte[] b = readAll(shared);
            validateRom(b);
            atomicWrite(own, b);
        }
        byte[] b = readAll(own);
        validateRom(b);
        return b;
    }

    static void validateRom(byte[] b) throws IOException {
        // 48 KiB H8/38606 image whose reset vector points into ROM
        int reset = (b.length >= 2) ? ((b[0] & 255) << 8 | (b[1] & 255)) : -1;
        if (b.length != 0xC000 || reset < 0x50 || reset >= 0xC000) throw new IOException("Not a 48 KiB Pokéwalker ROM dump");
    }

    /** Test transport (no Internet permission needed): the walker's IR over an abstract local
     *  socket that adb forwards — `walker-ir-relay.py --phone-socket localabstract:kyf37.walker.pclink`
     *  — to melonDS. Start the activity with --ez pclink true. */
    private static final class PcLink {
        private final android.net.LocalServerSocket server;
        private volatile android.net.LocalSocket client;
        private volatile boolean open = true;
        private final java.util.concurrent.LinkedBlockingQueue<byte[]> rx = new java.util.concurrent.LinkedBlockingQueue<>();
        PcLink() throws IOException {
            server = new android.net.LocalServerSocket("kyf37.walker.pclink");
            new Thread(() -> {
                while (open) try {
                    android.net.LocalSocket s = server.accept(); client = s;
                    DataInputStream in = new DataInputStream(new BufferedInputStream(s.getInputStream()));
                    while (true) { int n = in.readUnsignedShort(); byte[] b = new byte[n]; in.readFully(b); if (n > 0 && n <= 263) rx.put(b); }
                } catch (Exception ignored) { client = null; }
            }, "pclink").start();
        }
        void send(byte[] b) { android.net.LocalSocket s = client; if (s == null) return;
            try { DataOutputStream o = new DataOutputStream(s.getOutputStream()); o.writeShort(b.length); o.write(b); o.flush(); } catch (IOException ignored) {} }
        byte[] poll() { return rx.poll(); }
        void close() { open = false; try { server.close(); } catch (IOException ignored) {} }
    }

    /** IR trace for diagnosis: Android/data/org.kyf37.walker/files/emulated-ir-trace.txt */
    private PrintWriter trace;
    private void trace(String dir, byte[] b) {
        if (trace == null) return;
        StringBuilder s = new StringBuilder();
        for (byte x : b) s.append(String.format("%02x", (x ^ 0xAA) & 255));
        trace.println(SystemClock.uptimeMillis() + " " + dir + " " + b.length + " " + s);
        trace.flush();
    }

    private void emulate(int generation) {
        synchronized (CORE_LOCK) {
            if (!running || generation != emulationGeneration) return;
            emulateLocked(generation);
        }
    }

    private void emulateLocked(int generation) {
        try { File d = getExternalFilesDir(null); if (d != null) trace = new PrintWriter(new FileWriter(new File(d, "emulated-ir-trace.txt"), true)); } catch (IOException ignored) {}
        EmulatedIr ir = null;
        PcLink pc = null;
        long lastIr = 0, retryIrAt = 0;
        try {
            byte[] rom = loadRom(this);
            // Shared save with Flip Walker's menus once the game has registered this walker
            // ("nintendo" mark at 0); before that the firmware's factory image stays private.
            Walker shared = SaveFile.get(this);
            File own = new File(getFilesDir(), EEPROM);
            byte[] eeprom;
            if (registered(shared.snapshot())) eeprom = shared.snapshot();
            else if (own.exists() && own.length() == 65536) eeprom = readAll(own);
            else eeprom = blankEeprom();
            File backup = new File(getFilesDir(), "walker-before-emulator.eeprom");
            if (!backup.exists()) atomicWrite(backup, shared.snapshot()); // one-time safety copy of the Flip Walker save
            this.shared = shared; this.own = own;
            if (registered(eeprom)) persist(eeprom); // a walker registered earlier shows in the menus right away
            if (!PwCore.init(rom, eeprom)) throw new IOException("Emulator rejected the ROM");
            status = "";
            if (getIntent().getBooleanExtra("pclink", false)) { pc = new PcLink(); status = "PC link test mode"; }
            long next = SystemClock.uptimeMillis(), lastSave = 0;
            byte[] pending = null;
            while (running && generation == emulationGeneration) {
                // smaller slices while IR is live so replies meet the game's timing
                int slice = ir != null ? 4 : 16;
                int sampled = buttons.sample(slice);
                if (keys != sampled) { keys = sampled; view.postInvalidate(); }
                if (PwCore.run(slice, keys) != 0) { status = "Walker CPU stopped at " + Integer.toHexString(PwCore.pc()) + " (emulator limit). Reopen to restart."; android.util.Log.e("Pokewalker", status); view.postInvalidate(); break; }
                synchronized (lock) { if (PwCore.frame(lcd)) view.postInvalidate(); }
                int[] act;
                while ((act = actions.poll()) != null) {
                    boolean ok = act[0] == 0 ? PwCore.addSteps(act[1]) : PwCore.addWatts(act[1]);
                    toast = ok ? (act[0] == 0 ? "+" + act[1] + " " + UiText.tr("steps") : "+" + act[1] + " W") : UiText.tr("Walker busy, try again");
                    view.postInvalidate();
                }
                long st = PwCore.u32(PwCore.RAM_TODAY_LIVE), wt = PwCore.watts();
                if (st != liveSteps || wt != liveWatts) { liveSteps = st; liveWatts = wt; view.postInvalidate(); }
                byte[] burst;
                if (pc != null) {
                    while ((burst = PwCore.irPop()) != null) pc.send(burst);
                    while ((burst = pc.poll()) != null) PwCore.irPush(burst);
                }
                // Follow the firmware's receiver as well as its transmitter. A paired
                // walker may listen first; waiting for a TX burst deadlocks that reconnect.
                byte[] pendingBurst = pc == null ? PwCore.irPop() : null;
                boolean irEnabled = pc == null && PwCore.irEnabled();
                if (pc == null) {
                    try {
                        if (ir == null && (irEnabled || pendingBurst != null) && SystemClock.uptimeMillis() >= retryIrAt) {
                            irState = "IR opening…"; view.postInvalidate();
                            ir = new EmulatedIr(new IrSession(this)); status = ""; irState = "IR open";
                            lastIr = SystemClock.uptimeMillis(); view.postInvalidate();
                        }
                        while ((burst = pendingBurst) != null) {
                            pendingBurst = PwCore.irPop();
                            if (ir != null) ir.send(burst);
                        }
                        if (ir != null) {
                            byte[] completed;
                            while ((completed = ir.sent()) != null) { trace("TX", completed); irTx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            byte[] rx;
                            while ((rx = ir.poll()) != null) { trace("RX", rx); PwCore.irPush(rx); irRx++;
                                irFlash = lastIr = SystemClock.uptimeMillis(); view.postInvalidate(); }
                            if (!irEnabled && SystemClock.uptimeMillis() - lastIr > 15000) {
                                ir.close(); ir = null; irState = "IR idle"; view.postInvalidate();
                            }
                        }
                    } catch (IOException failure) {
                        // A closed helper/UART must not stop the emulated firmware or
                        // strand future connection attempts. Reopen on its next enable.
                        if (ir != null) ir.close(); ir = null;
                        retryIrAt = SystemClock.uptimeMillis() + 1000;
                        status = "Infrared unavailable: " + failure.getMessage(); irState = "IR failed";
                        android.util.Log.w("Pokewalker", "IR session failed; retrying", failure);
                        view.postInvalidate();
                    }
                }
                byte[] dirty = PwCore.eepromIfDirty();
                if (dirty != null) pending = dirty;
                long now = SystemClock.uptimeMillis();
                // persist after the firmware settles, at most once a second
                if (pending != null && (saveNow || now - lastSave > 1000)) { persist(pending); pending = null; lastSave = now; saveNow = false; saved = UiText.tr("Saved") + " " + android.text.format.DateFormat.format("HH:mm:ss", System.currentTimeMillis()); }
                next += slice;
                long wait = next - SystemClock.uptimeMillis();
                if (wait > 0) SystemClock.sleep(wait); else if (wait < -500) next = SystemClock.uptimeMillis();
            }
            byte[] last = PwCore.eepromIfDirty();
            if (last != null) pending = last;
            if (pending != null) persist(pending);
        } catch (IOException e) {
            status = e.getMessage();
            android.util.Log.w("Pokewalker", "emulation stopped", e);
        } finally {
            if (ir != null) ir.close();
            if (pc != null) pc.close();
            if (trace != null) trace.close();
            view.postInvalidate();
        }
    }

    static boolean registered(byte[] e) {
        byte[] mark = {'n', 'i', 'n', 't', 'e', 'n', 'd', 'o'};
        return e.length == 65536 && Arrays.equals(Arrays.copyOf(e, 8), mark) && (e[0xed + 0x5b] & 1) != 0 && e[0xed + 0x5b] != (byte) 0xFF;
    }

    /** Registered walkers live in Flip Walker's save (menus see them); others in the private file. */
    private void persist(byte[] e) throws IOException {
        if (registered(e)) { shared.replaceAll(e); if (own.exists()) own.renameTo(new File(own.getPath() + ".synced")); }
        else atomicWrite(own, e);
    }

    static byte[] blankEeprom() { byte[] b = new byte[65536]; Arrays.fill(b, (byte) 0xFF); return b; }

    static byte[] readAll(File f) throws IOException {
        try (InputStream in = new FileInputStream(f); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192]; int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        }
    }

    /** Write to a temp file, fsync, keep the previous version as .bak, then rename. */
    static void atomicWrite(File f, byte[] data) throws IOException {
        File tmp = new File(f.getPath() + ".tmp");
        try (FileOutputStream out = new FileOutputStream(tmp)) { out.write(data); out.getFD().sync(); }
        if (f.exists()) { File bak = new File(f.getPath() + ".bak"); bak.delete(); if (!f.renameTo(bak)) throw new IOException("Could not keep backup"); }
        if (!tmp.renameTo(f)) throw new IOException("Could not save walker");
    }

    private int keyBit(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_LEFT: case KeyEvent.KEYCODE_4: return PwCore.KEY_LEFT;
            case KeyEvent.KEYCODE_DPAD_CENTER: case KeyEvent.KEYCODE_ENTER: case KeyEvent.KEYCODE_5: return PwCore.KEY_ENTER;
            case KeyEvent.KEYCODE_DPAD_RIGHT: case KeyEvent.KEYCODE_6: return PwCore.KEY_RIGHT;
            default: return 0;
        }
    }
    // Minimum hold is counted by EmulatedButtons in emulated time, never UI wall time.
    private volatile boolean saveNow;
    private final java.util.concurrent.ConcurrentLinkedQueue<int[]> actions = new java.util.concurrent.ConcurrentLinkedQueue<>();
    private volatile long liveSteps = -1, liveWatts = -1;
    private volatile String toast = "";
    @Override public boolean onKeyDown(int code, KeyEvent e) {
        int scan = e.getScanCode();
        if (scan == 59 || code == KeyEvent.KEYCODE_F1 || scan == 62 || code == KeyEvent.KEYCODE_F4) { finish(); return true; }
        if (scan == 60 || code == KeyEvent.KEYCODE_F2) { help = !help; view.invalidate(); return true; }
        if (scan == 61 || code == KeyEvent.KEYCODE_F3) { saveNow = true; return true; }
        if (code == KeyEvent.KEYCODE_1) { actions.add(new int[]{0, 1000}); return true; }
        if (code == KeyEvent.KEYCODE_2) { actions.add(new int[]{0, 10000}); return true; }
        if (code == KeyEvent.KEYCODE_3) { actions.add(new int[]{1, 100}); return true; }
        if (code == KeyEvent.KEYCODE_7) { actions.add(new int[]{1, 1000}); return true; }
        int k = keyBit(code); if (k == 0) return super.onKeyDown(code, e); buttons.press(k); view.invalidate(); return true;
    }
    @Override public boolean onKeyUp(int code, KeyEvent e) {
        int k = keyBit(code); if (k == 0) return super.onKeyUp(code, e);
        buttons.release(k); view.invalidate();


        return true;
    }

    private volatile boolean help;
    private volatile long irFlash;
    private volatile String saved = "";

    /** Flip Walker styled screen: header, a drawn Pokéwalker shell around the real LCD, IR window
     *  that lights on traffic, buttons that sink when pressed, a status card and the corner-key bar. */
    private final class LcdView extends View {
        private static final int INK = 0xff20365b, PAPER = 0xfff6faff, RED = 0xffc2405a, GREEN = 0xffb6edcd;
        private final int[] accents = {0xff39bd95, 0xffe45e79, 0xfff0b94e, 0xff9478da, 0xff37b8d3, 0xff6191e0, 0xffa98cbf, 0xffe29a53};
        private final int[] shades = {0xffc5d1a8, 0xff8f9c74, 0xff56614a, 0xff1f2a1c};
        private final int[] pixels = new int[PwCore.W * PwCore.H];
        private final Bitmap bitmap = Bitmap.createBitmap(PwCore.W, PwCore.H, Bitmap.Config.ARGB_8888);
        private final Paint p = new Paint();
        private Canvas c;
        LcdView(Context ctx) { super(ctx); }
        void rect(float x, float y, float w, float h, int color) { p.setAntiAlias(false); p.setColor(color); c.drawRect(x, y, x + w, y + h, p); }
        void text(String s, float x, float y, float size, int color) { PixelArt.text(c, p, UiText.tr(s), x, y, size, color); }
        void box(float x, float y, float w, float h, int color) {
            rect(x + 4, y, w - 8, h, INK); rect(x, y + 4, w, h - 8, INK); rect(x + 4, y + 4, w - 8, h - 8, color);
            rect(x + 8, y + 4, w - 16, 3, 0xffffffff); rect(x + 8, y + h - 7, w - 16, 3, 0xff93b7cf);
        }
        void disc(float cx, float cy, float r, int color) { p.setAntiAlias(true); p.setColor(color); c.drawCircle(cx, cy, r, p); }
        void button(float cx, float cy, float r, boolean down) {
            disc(cx, cy + 4, r, INK);
            disc(cx, cy + (down ? 3 : 0), r - 4, down ? 0xff9fb4c9 : 0xffe9eef5);
            if (!down) disc(cx - r / 3, cy - r / 3, r / 4, 0xffffffff);
        }
        @Override protected void onDraw(Canvas canvas) {
            c = canvas; c.save(); c.scale(getWidth() / 480f, getHeight() / 854f);
            c.drawColor(PAPER);
            for (int y = 96; y < 774; y += 12) for (int x = 0; x < 480; x += 12) if (((x + y) / 12) % 2 == 0) rect(x, y, 12, 12, 0xffeaf2fc);
            rect(0, 0, 480, 90, 0xffc7e2fc); rect(0, 90, 480, 4, INK); rect(0, 94, 480, 4, 0xff79badf);
            for (int i = 0; i < 8; i++) rect(i * 60, 90, 60, 4, accents[i]);
            text("Emulated Pokewalker", 28, 48, 26, INK);
            text("Real firmware · your ROM", 28, 78, 14, RED);
            PixelArt.ball(c, p, 426, 22, 3);

            // IR window in the header, lit while infrared traffic flows
            boolean live = SystemClock.uptimeMillis() - irFlash < 250;
            p.setAntiAlias(true); p.setColor(INK); c.drawRoundRect(398, 62, 462, 86, 10, 10, p);
            p.setColor(live ? 0xffff4f5e : 0xff4a2633); c.drawRoundRect(403, 67, 457, 81, 7, 7, p);
            // LCD as large as the screen allows: full width at 5x (480x320)
            rect(0, 102, 480, 4, INK);
            synchronized (lock) { for (int i = 0; i < pixels.length; i++) pixels[i] = shades[lcd[i] & 3]; }
            bitmap.setPixels(pixels, 0, PwCore.W, 0, 0, PwCore.W, PwCore.H);
            p.setFilterBitmap(false); c.drawBitmap(bitmap, null, new Rect(0, 106, 480, 426), p);
            rect(0, 426, 480, 4, INK);
            int k = keys;
            button(120, 474, 24, (k & PwCore.KEY_LEFT) != 0);
            button(240, 482, 32, (k & PwCore.KEY_ENTER) != 0);
            button(360, 474, 24, (k & PwCore.KEY_RIGHT) != 0);
            text("4", 114, 522, 14, INK); text("OK", 230, 538, 12, INK); text("6", 354, 522, 14, INK);

            // status card
            box(18, 556, 444, 204, help ? 0xffe8dcff : 0xffcdf2fc);
            if (help) {
                lines(new String[]{"In the game open the Pokewalker", "transfer and wait until it searches.",
                        "Press OK here, then hold the IR", "windows 5-10 cm apart, facing.",
                        "Left / OK / Right are the walker", "buttons. Progress saves itself."}, 600);
            } else {
                int dot = irState.equals("IR open") ? 0xff39bd95 : irState.equals("IR failed") ? 0xffe45e79 : irState.startsWith("IR opening") ? 0xfff0b94e : 0xff93a4b8;
                p.setAntiAlias(true); p.setColor(INK); c.drawCircle(46, 596, 12, p); p.setColor(dot); c.drawCircle(46, 596, 8, p);
                text(irState, 68, 604, 21, INK);
                text(UiText.tr("Sent") + " " + irTx + "   " + UiText.tr("Received") + " " + irRx, 36, 636, 15, INK);
                if (liveSteps >= 0) text(UiText.tr("Today") + " " + liveSteps + " " + UiText.tr("steps") + " · " + liveWatts + " W", 36, 664, 17, INK);
                text("1 +1000  2 +10000 " + UiText.tr("steps") + " · 3 +100  7 +1000 W", 36, 740, 12, 0xff6b7d93);
                if (!toast.isEmpty()) text(toast, 300, 604, 15, 0xff2d7a5f);
                Walker w = shared;
                if (w != null && registered(w.snapshot())) text(UiText.tr("In Flip Walker menus") + " · #" + w.species(), 36, 690, 15, 0xff2d7a5f);
                else text("Not registered yet - send from the game", 36, 690, 15, 0xff6b7d93);
                if (!saved.isEmpty()) text(saved, 36, 714, 13, 0xff2d7a5f);
                if (!status.isEmpty()) wrap(status, 604);
            }
            box(0, 774, 480, 80, INK);
            SoftKeyBar.draw(c, p, "F1  Menu", "F2  Help", "F3  Save", "F4  Back", "OK Button");
            c.restore();
            if (SystemClock.uptimeMillis() - irFlash < 300) postInvalidateDelayed(120);
        }
        private void lines(String[] l, float y) { for (String s : l) { text(s, 36, y, 17, INK); y += 28; } }
        private void wrap(String s, float y) { if (s.length() > 40) s = s.substring(0, 39) + "…"; text(s, 36, y, 15, RED); }
    }
}
