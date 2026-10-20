import org.kyf37.walker.*;
import java.net.*;
import java.nio.file.*;
import java.util.Locale;

/** Runs the app's own virtual walker (Walker.java) against melonDS's IR UDP bridge.
 *  Usage: java HostWalker <save.bin> [listenPort=34561] [melonDSPort=34560] */
public final class HostWalker {
    public static void main(String[] a) throws Exception {
        Path save = Paths.get(a[0]);
        int port = a.length > 1 ? Integer.parseInt(a[1]) : 34561, peer = a.length > 2 ? Integer.parseInt(a[2]) : 34560;
        byte[] saved = Files.exists(save) ? Files.readAllBytes(save) : null;
        Walker walker = new Walker(saved, bytes -> Files.write(save, bytes));
        if (saved == null) Files.write(save, walker.snapshot());
        DatagramSocket s = new DatagramSocket(new InetSocketAddress("127.0.0.1", port));
        InetSocketAddress ds = new InetSocketAddress("127.0.0.1", peer);
        s.setSoTimeout(100);
        long lastAdvert = 0, lastPacket = 0;
        System.out.println("Virtual walker listening on UDP " + port + " (save " + save + ")");
        byte[] buf = new byte[1024];
        while (true) {
            long now = System.currentTimeMillis();
            if (walker.connected() && now - lastPacket > 5000) { walker.disconnect(); log("timeout -> disconnected"); }
            if (!walker.connected() && now - lastAdvert >= 300) { send(s, ds, new byte[]{0x56}); lastAdvert = now; }
            DatagramPacket p = new DatagramPacket(buf, buf.length);
            try { s.receive(p); } catch (SocketTimeoutException e) { continue; }
            byte[] b = java.util.Arrays.copyOf(p.getData(), p.getLength());
            if (b.length < 8) continue;
            log(String.format(Locale.ROOT, "game -> %02X %02X len=%d", (b[0] ^ 0xaa) & 255, (b[1] ^ 0xaa) & 255, b.length));
            try {
                byte[] reply = walker.receive(b); lastPacket = now;
                if (reply != null) { send(s, ds, reply); log(String.format(Locale.ROOT, "walker -> %02X %02X len=%d", (reply[0] ^ 0xaa) & 255, (reply[1] ^ 0xaa) & 255, reply.length)); }
                else log("  (no reply)");
            } catch (Exception e) { log("  REJECTED: " + e); }
            System.out.println("  status: " + walker.status + " | paired=" + walker.paired() + " strolling=" + walker.strolling() + " species=" + walker.species());
        }
    }
    static void send(DatagramSocket s, InetSocketAddress to, byte[] b) throws Exception { s.send(new DatagramPacket(b, b.length, to)); }
    static void log(String m) { System.out.printf(Locale.ROOT, "%tT.%<tL %s%n", System.currentTimeMillis(), m); }
}
