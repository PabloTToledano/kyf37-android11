import org.kyf37.pokedex.DexLogic;
public final class DexLogicTest {
    static void check(boolean ok) { if(!ok) throw new AssertionError(); }
    public static void main(String[] args) {
        check(DexLogic.t9("Pikachu").equals("7452248"));
        check(DexLogic.t9("Mr. Mime").equals("676463"));
        check(DexLogic.matches("Victini",0,"000",false));
        check(DexLogic.matches("Pikachu",25,"025",false));
        check(!DexLogic.matches("Pikachu",25,"2",false));
        check(DexLogic.matches("Oshawott",7,"674",true));
        check(!DexLogic.matches("Tepig",4,"674",true));
        check(!DexLogic.matches("Pikachu",25,"999999999999",false));
        check(DexLogic.matches("Pecharunt",1025,"1025",false));
        check(!DexLogic.matches("Pecharunt",1025,"102",false));
        check(DexLogic.t9("Ñandú").equals(DexLogic.t9("Nandu")));
        check(DexLogic.t9("Árbol").equals(DexLogic.t9("Arbol")));
        check(DexLogic.matches("Pingüino",0,"7464",true));
        check(DexLogic.spanish("es") && !DexLogic.spanish("en") && !DexLogic.spanish(""));
        check(DexLogic.wrap(-1,301)==300);
        check(DexLogic.wrap(301,301)==0);
        check(DexLogic.wrap(-6,0)==0);
        check(DexLogic.pageCount(0,4)==1);
        check(DexLogic.pageCount(5,4)==2);
        check(DexLogic.clamp(300,3)==2);
        System.out.println("KEYPAD_LOGIC_OK: T9, #000, leading zeros, overflow, list wrap, empty results, pagination");
    }
}
