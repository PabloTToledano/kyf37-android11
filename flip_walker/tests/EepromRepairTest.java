package org.kyf37.walker;
import java.util.Arrays;
public class EepromRepairTest {
 static void check(boolean b){if(!b)throw new AssertionError();}
 static int sum(byte[] b,int a,int n){int s=1;for(int i=0;i<n;i++)s+=b[a+i]&255;return s&255;}
 public static void main(String[] args){
  byte[] fresh=new Walker(null,b->{}).snapshot();
  for(int[] r:new int[][]{{0xed,104},{0x156,24},{0x83,40},{0x16f,2}})check((fresh[r[0]+r[1]]&255)==sum(fresh,r[0],r[1]));
  byte[] old=fresh.clone();old[0xed+0x5b]=old[0x1ed+0x5b]=3;
  for(int[] r:new int[][]{{0xed,0x1ed,104},{0x156,0x256,24},{0x83,0x183,40},{0x16f,0x26f,2}})old[r[0]+r[2]]=old[r[1]+r[2]]=(byte)(sum(old,r[0],r[2])-1);
  byte[] fixed=EepromRepair.repair(old,null);check((fixed[0x155]&255)==sum(fixed,0xed,104));check(fixed[0xed+0x5b]==3);check(old[0x155]!=fixed[0x155]);
  byte[] erased=old.clone();Arrays.fill(erased,0xed,0x156,(byte)255);Arrays.fill(erased,0x1ed,0x256,(byte)255);
  byte[] restored=EepromRepair.repair(erased,old);check(restored[0xed+0x5b]==3);check((restored[0x155]&255)==sum(restored,0xed,104));
  check(Arrays.equals(restored,EepromRepair.repair(restored,old)));
  byte[] lostHealth=fixed.clone();Arrays.fill(lostHealth,0x156,0x16f,(byte)255);Arrays.fill(lostHealth,0x256,0x26f,(byte)255);
  byte[] recoveredHealth=EepromRepair.repair(lostHealth,old);check(recoveredHealth[0x164]==old[0x164]);check((recoveredHealth[0x16e]&255)==sum(recoveredHealth,0x156,24));
  byte[] unknown=old.clone();unknown[0xed]^=7;check(Arrays.equals(unknown,EepromRepair.repair(unknown,null))==false); // other legacy records upgrade
  check(EepromRepair.repair(unknown,null)[0xed]==unknown[0xed]);
  check(EepromRepair.repair(erased,null)[0xed]==(byte)255);
  check(Arrays.equals(fresh,EepromRepair.repair(fresh,old)));
  System.out.println("EEPROM_CHECKSUM_AND_RECOVERY_OK");
 }
}
