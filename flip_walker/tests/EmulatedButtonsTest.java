package org.kyf37.walker;
public final class EmulatedButtonsTest {
 public static void main(String[] args) {
  EmulatedButtons b=new EmulatedButtons(); b.press(1); b.release(1);
  for(int i=0;i<50;i++) if(b.sample(4)!=1)throw new AssertionError("quick tap lost");
  if(b.sample(4)!=0)throw new AssertionError("button stuck");
  b.press(4);for(int i=0;i<100;i++)if(b.sample(16)!=4)throw new AssertionError("held button lost");
  b.press(4); // OS autorepeat must not restart the minimum hold
  b.release(4);if(b.sample(16)!=0)throw new AssertionError("release lost");
  b.press(16);b.clear();if(b.sample(16)!=0)throw new AssertionError("pause leaves held key");
  System.out.println("EMULATED_BUTTONS_OK: quick tap, physical hold, release, pause");
 }
}
