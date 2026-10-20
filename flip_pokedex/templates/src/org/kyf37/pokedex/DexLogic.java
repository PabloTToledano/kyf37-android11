package org.kyf37.pokedex;

import java.text.Normalizer;
import java.util.*;

/** Android-free navigation and search rules, shared with host tests. */
public final class DexLogic {
    private DexLogic() {}
    /** Lowercase letters with accents removed, so Spanish names such as Ñ and É match T9 keys. */
    public static String fold(String name) {
        return Normalizer.normalize(name, Normalizer.Form.NFD).replaceAll("\\p{M}+", "").toLowerCase(Locale.ROOT);
    }
    /** True for the Spanish locale language code. */
    public static boolean spanish(String language) { return "es".equals(language); }
    public static String t9(String name) {
        StringBuilder out = new StringBuilder();
        for (char c : fold(name).toCharArray()) {
            if (c >= 'a' && c <= 'z') out.append("22233344455566677778889999".charAt(c - 'a'));
        }
        return out.toString();
    }
    public static boolean matches(String name, int number, String query, boolean byName) {
        if (query.isEmpty()) return true;
        if (byName) return t9(name).startsWith(query);
        try { return number == Integer.parseInt(query); } catch (NumberFormatException e) { return false; }
    }
    public static int wrap(int value, int count) { return count == 0 ? 0 : (value % count + count) % count; }
    public static int clamp(int value, int count) { return Math.max(0, Math.min(value, count - 1)); }
    public static int pageCount(int items, int size) { return Math.max(1, (items + size - 1) / size); }
}
