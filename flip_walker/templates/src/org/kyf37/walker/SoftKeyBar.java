package org.kyf37.walker;
import android.graphics.Canvas;
import android.graphics.Paint;
import java.util.regex.Pattern;

/** Physical button icons on a fixed three-column, two-row pixel grid. */
final class SoftKeyBar {
    private static final Pattern KEY_PREFIX=Pattern.compile("^(F[1-4]|OK) +");
    private static final int PAPER=0xfff6faff,MINT=0xffb6edcd,INK=0xff20365b;
    private static final String[][] ICONS={
        {"0111111110","0122222210","1122112210","0121111210","1122112210","0121221210","1122222210","0122222210","0111111110","0000000000"},
        {"0001111000","0012222100","1111111111","1222112221","1221221221","1221221221","1222112221","1222222221","1111111111","0000000000"},
        {"0000000000","1111111111","1122222211","1212222121","1221221221","1222112221","1221221221","1212222121","1111111111","0000000000"},
        {"0001111000","0012121100","0122122210","1121111211","1212222121","1212222121","1121111211","0122122210","0012121100","0001111000"}
    };
    static String action(String keyLabel){return KEY_PREFIX.matcher(UiText.tr(keyLabel)).replaceFirst("");}
    private static void corner(Canvas c,Paint p,int icon,int iconX,int baseline,String keyLabel){
        PixelArt.tile(c,p,ICONS[icon],iconX,baseline-17,2,new int[]{0,PAPER,MINT});
        String label=action(keyLabel);float size=PixelArt.width(label,17)<=112?17:9;
        PixelArt.text(c,p,label,iconX+28,baseline,size,PAPER);
    }
    static void draw(Canvas c,Paint p,String topLeft,String topRight,String bottomLeft,String bottomRight,String center){
        c.save();c.clipRect(8,782,472,846);
        p.setColor(0xff426083);p.setAntiAlias(false);
        c.drawRect(160,784,162,844,p);c.drawRect(318,784,320,844,p);
        corner(c,p,0,12,804,topLeft);corner(c,p,1,332,804,topRight);
        corner(c,p,2,12,838,bottomLeft);corner(c,p,3,332,838,bottomRight);
        // The center key sits above its label; the label shares the lower row baseline.
        PixelArt.tile(c,p,new String[]{"00001111110000","00011222211000","00122222221100","01222222222110","12222222222221","12222222222221","12222222222221","12222222222221","12222222222221","01222222222110","00122222221100","00011222211000","00001111110000","00000000000000"},226,784,2,new int[]{0,PAPER,MINT});
        PixelArt.text(c,p,"OK",234,801,9,INK);
        String label=action(center);float size=PixelArt.width(label,17)<=140?17:9;
        PixelArt.text(c,p,label,240-(PixelArt.width(label,size)-PixelArt.scale(size))/2,838,size,MINT);
        c.restore();
    }
}
