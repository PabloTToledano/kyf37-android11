import org.kyf37.walker.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

/** Differential test: replays a recorded game<->real-firmware session (ir_tap.py JSONL) into the app's
 *  Walker.java and compares each reply's command, extra byte and payload with the firmware's reply.
 *  Usage: java Replay <session.jsonl> [initial-eeprom.bin] */
public final class Replay {
    public static void main(String[] a) throws Exception {
        List<String[]> ev = new ArrayList<>();
        Pattern p = Pattern.compile("\"dir\": \"(\\w+)\", \"hex\": \"([0-9a-f]+)\"");
        for (String line : Files.readAllLines(Paths.get(a[0]))) { Matcher m = p.matcher(line); if (m.find()) ev.add(new String[]{m.group(1), m.group(2)}); }
        byte[] init = a.length > 1 ? Files.readAllBytes(Paths.get(a[1])) : null;
        Walker w = new Walker(init, b -> {});
        byte[] session = null; int ok = 0, bad = 0, skipped = 0;
        Map<String, Integer> diffs = new TreeMap<>();
        for (int i = 0; i < ev.size(); i++) {
            if (!ev.get(i)[0].equals("game")) continue;
            byte[] wire = hex(ev.get(i)[1]);
            int cmd = (wire[0] ^ 0xaa) & 255;
            // the firmware's reply may arrive after a game F4 sent back-to-back; F4 itself gets none
            byte[] expect = null;
            for (int j = i + 1; cmd != 0xf4 && j < ev.size(); j++) {
                if (ev.get(j)[0].equals("walker")) { expect = hex(ev.get(j)[1]); break; }
                int next = (hex(ev.get(j)[1])[0] ^ 0xaa) & 255;
                if (next != 0xf4) break;
            }
            if (cmd == 0xfa && expect == null) continue; // walker was not listening yet
            if (cmd != 0xfa && session != null) wire = rekey(wire, session);
            byte[] got;
            try { got = w.receive(wire); }
            catch (Exception e) { got = null; diffs.merge(String.format("%02X threw %s", cmd, e.getMessage()), 1, Integer::sum); bad++; continue; }
            if (cmd == 0xfa && got != null) {
                Packet fa = Packet.decode(wire), f8 = Packet.decode(got);
                session = new byte[4]; for (int k = 0; k < 4; k++) session[k] = (byte) (fa.session[k] ^ f8.session[k]);
            }
            if (expect == null && got == null) { ok++; continue; }
            if (expect == null || got == null) { diffs.merge(String.format("%02X reply %s, firmware %s", cmd, got == null ? "none" : "sent", expect == null ? "none" : "sent"), 1, Integer::sum); bad++; continue; }
            Packet e = Packet.decode(expect), g = Packet.decode(got);
            if (cmd == 0xfa) { ok++; continue; } // random session halves
            String why = e.command != g.command ? String.format("cmd %02X vs %02X", g.command, e.command)
                    : e.extra != g.extra ? String.format("extra %02X vs %02X", g.extra, e.extra)
                    : !Arrays.equals(e.payload, g.payload) ? "payload " + firstDiff(g.payload, e.payload) : null;
            if (why != null && System.getenv("REPLAY_VERBOSE") != null)
                System.out.printf("%02X%n  app %s%n  fw  %s%n", cmd, hexs(g.payload), hexs(e.payload));
            if (why == null) ok++; else { bad++; diffs.merge(String.format("%02X: %s", cmd, why), 1, Integer::sum); }
        }
        System.out.printf("matched %d, differed %d%n", ok, bad);
        diffs.forEach((k, v) -> System.out.println("  " + v + "x " + k));
        Files.write(Paths.get("replay-final-eeprom.bin"), w.snapshot());
        System.exit(bad == 0 ? 0 : 1);
    }
    static String firstDiff(byte[] g, byte[] e) {
        if (g.length != e.length) return "len " + g.length + " vs " + e.length;
        for (int i = 0; i < g.length; i++) if (g[i] != e[i]) return String.format("@%d %02X vs %02X", i, g[i] & 255, e[i] & 255);
        return "?";
    }
    static byte[] rekey(byte[] wire, byte[] session) {
        Packet q = Packet.decode(wire);
        return new Packet(q.command, q.extra, session, q.payload).encode();
    }
    static String hexs(byte[] b) { StringBuilder s = new StringBuilder(); for (byte x : b) s.append(String.format("%02x", x & 255)); return s.toString(); }
    static byte[] hex(String s) { byte[] b = new byte[s.length() / 2]; for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(s.substring(2 * i, 2 * i + 2), 16); return b; }
}
