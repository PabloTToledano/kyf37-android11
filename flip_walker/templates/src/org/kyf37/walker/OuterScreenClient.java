package org.kyf37.walker;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;

/**
 * KYF37 outer screen client, API level 2 (level 1 services ignore animations: check info().apiLevel). Copy this file into your app (any package name)
 * and follow docs/ui/OUTER-SCREEN-CLIENT-API.md. No other library is needed.
 *
 * The outer panel is 128x36 monochrome. A frame is 576 bytes: rows top to bottom, 16 bytes
 * per row, most significant bit = leftmost pixel, 1 = lit pixel.
 */
public final class OuterScreenClient implements ServiceConnection {
    public static final String SERVICE_PACKAGE = "org.kyf37.subdisplay";
    public static final String ACTION_BIND = "org.kyf37.outerscreen.BIND";
    public static final String PERMISSION = "org.kyf37.permission.OUTER_SCREEN_CLIENT";
    public static final String DESCRIPTOR = "org.kyf37.outerscreen.IOuterScreen";
    /** Broadcast to your app when the user presses the side key on your lit page (API level 2).
     *  Declare the receiver with android:permission="org.kyf37.permission.OUTER_SCREEN" so only
     *  the system display service can send it. */
    public static final String ACTION_BUTTON = "org.kyf37.outerscreen.action.BUTTON";
    public static final String EXTRA_BUTTON = "org.kyf37.outerscreen.extra.BUTTON";
    public static final int BUTTON_SIDE = 1;
    public static final int MAX_FRAMES = 16, MIN_INTERVAL_MS = 100, MAX_INTERVAL_MS = 5000;
    public static final int WIDTH = 128, HEIGHT = 36, FRAME_BYTES = WIDTH * HEIGHT / 8;

    /** post() durationMs = 0: ambient frame shown instead of the clock while the panel is lit. */
    public static final int AMBIENT = 0;
    /** post() flag: light the panel (restart its screen-off timeout) when the lid is closed. */
    public static final int FLAG_WAKE = 1;

    /** Results of post() and clear(). */
    public static final int OK = 0, ERROR_DISABLED = -1, ERROR_BAD_FRAME = -2, ERROR_RATE_LIMITED = -3,
            ERROR_BUSY = -4, ERROR_UNAVAILABLE = -5;

    static final int TX_INFO = IBinder.FIRST_CALL_TRANSACTION, TX_POST = TX_INFO + 1, TX_CLEAR = TX_INFO + 2, TX_ANIMATION = TX_INFO + 3;

    public interface Listener {
        void onConnected(OuterScreenClient client);
        void onDisconnected(OuterScreenClient client);
    }

    /** Snapshot returned by info(). */
    public static final class Info {
        public int apiLevel, width, height;
        /** The user turned this app on in Settings > Outer screen. */
        public boolean enabled;
        public boolean lidClosed;
        /** The panel is lit right now (lid closed and inside the screen-off timeout). */
        public boolean visible;
    }

    private final Context context;
    private final Listener listener;
    private volatile IBinder remote;

    private OuterScreenClient(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    /** Binds to the outer screen service. Returns null when this phone has no outer screen API. */
    public static OuterScreenClient bind(Context context, Listener listener) {
        OuterScreenClient c = new OuterScreenClient(context, listener);
        Intent i = new Intent(ACTION_BIND).setPackage(SERVICE_PACKAGE);
        try {
            if (c.context.bindService(i, c, Context.BIND_AUTO_CREATE)) return c;
            c.context.unbindService(c);
        } catch (SecurityException | IllegalArgumentException ignored) {}
        return null;
    }

    public void unbind() {
        remote = null;
        try { context.unbindService(this); } catch (IllegalArgumentException ignored) {}
    }

    public boolean isConnected() { return remote != null; }

    public Info info() throws RemoteException {
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try {
            d.writeInterfaceToken(DESCRIPTOR);
            binder().transact(TX_INFO, d, r, 0);
            r.readException();
            Info info = new Info();
            info.apiLevel = r.readInt(); info.width = r.readInt(); info.height = r.readInt();
            info.enabled = r.readInt() != 0; info.lidClosed = r.readInt() != 0; info.visible = r.readInt() != 0;
            return info;
        } finally { d.recycle(); r.recycle(); }
    }

    /** Shows a frame. durationMs AMBIENT (0) = replace the clock until clear(); 1..60000 = temporary alert. */
    public int post(byte[] frame, int durationMs, int flags) throws RemoteException {
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try {
            d.writeInterfaceToken(DESCRIPTOR);
            d.writeByteArray(frame);
            d.writeInt(durationMs);
            d.writeInt(flags);
            binder().transact(TX_POST, d, r, 0);
            r.readException();
            return r.readInt();
        } finally { d.recycle(); r.recycle(); }
    }

    /** API level 2: an ambient animation the service loops by itself while the panel is lit
     *  (2..16 frames, intervalMs 100..5000). Your app does not need to stay running. */
    public int postAnimation(byte[][] frames, int intervalMs, int flags) throws RemoteException {
        byte[] all = new byte[frames.length * FRAME_BYTES];
        for (int i = 0; i < frames.length; i++) {
            if (frames[i].length != FRAME_BYTES) return ERROR_BAD_FRAME;
            System.arraycopy(frames[i], 0, all, i * FRAME_BYTES, FRAME_BYTES);
        }
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try {
            d.writeInterfaceToken(DESCRIPTOR);
            d.writeByteArray(all);
            d.writeInt(intervalMs);
            d.writeInt(flags);
            binder().transact(TX_ANIMATION, d, r, 0);
            r.readException();
            return r.readInt();
        } finally { d.recycle(); r.recycle(); }
    }

    /** Removes this app's ambient frame and any alert it is showing. */
    public int clear() throws RemoteException {
        Parcel d = Parcel.obtain(), r = Parcel.obtain();
        try {
            d.writeInterfaceToken(DESCRIPTOR);
            binder().transact(TX_CLEAR, d, r, 0);
            r.readException();
            return r.readInt();
        } finally { d.recycle(); r.recycle(); }
    }

    private IBinder binder() throws RemoteException {
        IBinder b = remote;
        if (b == null) throw new RemoteException("Outer screen service not connected");
        return b;
    }

    /** Packs WIDTH*HEIGHT pixels (non-zero = lit) into a 576-byte frame. */
    public static byte[] pack(byte[] pixels) {
        if (pixels.length != WIDTH * HEIGHT) throw new IllegalArgumentException("need 128x36 pixels");
        byte[] f = new byte[FRAME_BYTES];
        for (int i = 0; i < pixels.length; i++) if (pixels[i] != 0) f[i >> 3] |= (byte) (0x80 >>> (i & 7));
        return f;
    }

    /** Converts a 128x36 bitmap: pixels darker than `threshold` (0..255 luminance) become lit. */
    public static byte[] fromBitmap(Bitmap b, int threshold) {
        if (b.getWidth() != WIDTH || b.getHeight() != HEIGHT) b = Bitmap.createScaledBitmap(b, WIDTH, HEIGHT, false);
        byte[] px = new byte[WIDTH * HEIGHT];
        for (int y = 0; y < HEIGHT; y++) for (int x = 0; x < WIDTH; x++) {
            int c = b.getPixel(x, y);
            int lum = (Color.red(c) * 299 + Color.green(c) * 587 + Color.blue(c) * 114) / 1000;
            if (Color.alpha(c) >= 128 && lum < threshold) px[y * WIDTH + x] = 1;
        }
        return pack(px);
    }

    @Override public void onServiceConnected(ComponentName name, IBinder service) {
        remote = service;
        if (listener != null) listener.onConnected(this);
    }

    @Override public void onServiceDisconnected(ComponentName name) {
        remote = null;
        if (listener != null) listener.onDisconnected(this);
    }
}
