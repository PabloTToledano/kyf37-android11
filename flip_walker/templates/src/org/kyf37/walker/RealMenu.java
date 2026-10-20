package org.kyf37.walker;
import java.util.*;
/** Keypad editor; all values are copied before a worker starts. */
final class RealMenu {
 static final String[] OPTIONS={"Read trainer & steps","Back up all data","Add watts & steps","Gift Pokemon","Gift item","Dump ROM"};
 int choice,mode,row;boolean confirm,editing;String digits="";
 final int[] watts={100,0,0};final int[] gift={25,0,33,0,0,0,50,0,0,9};final int[] item={4};
 int[] values(){return mode==1?watts:mode==2?gift:item;}
 int count(){return mode==0?6:values().length+1;}
 String title(){return mode==1?"WATTS & STEPS":mode==2?"POKEMON GIFT":mode==3?"ITEM GIFT":"REAL POKEWALKER";}
 String[] catalog(){if(mode==3)return WalkerCatalog.ITEM;if(mode!=2)return null;
  return row==0?WalkerCatalog.POKE:row==1?WalkerCatalog.ITEM:row>=2&&row<=5?WalkerCatalog.MOVE:row==9?WalkerCatalog.ABILITY:null;}
 int min(){return mode==1&&row==0||mode==2&&(row==0||row==6)||mode==3?1:0;}
 int max(){String[] c=catalog();if(c!=null)return c.length-1;if(mode==1)return row==0?65535:row==1?99999:1;return row==6?100:1;}
 void move(int delta){editing=false;digits="";if(mode==0)choice=(choice+delta+6)%6;else row=(row+delta+count())%count();}
 void change(int delta){if(mode==0){move(delta);return;}if(row==values().length)return;
  editing=false;digits="";int[] v=values();v[row]=Math.max(min(),Math.min(max(),v[row]+delta));}
 void digit(int n){if(mode==0||confirm||row==values().length)return;if(!editing){digits="";editing=true;}
  if(digits.length()>=5)digits="";String next=digits+n;int value=Integer.parseInt(next);if(value<=max()){digits=next;values()[row]=value;}}
 boolean valid(){if(mode==1)return watts[0]>=1;if(mode==3)return item[0]>=1;return gift[0]>=1&&gift[2]>=1&&gift[6]>=1;}
 String label(int i){if(mode==0)return OPTIONS[i];if(i==values().length)return "Review & connect";
  if(mode==1)return i==0?"Watts to add":i==1?"Today steps (0=keep)":"Max total steps";
  if(mode==3)return "Item";
  return new String[]{"Pokemon","Held item","Move 1","Move 2","Move 3","Move 4","Level","Gender","Shiny","Ability"}[i];}
 String value(int i){if(mode==0||i==values().length)return "";int old=row;row=i;String[] c=catalog();row=old;int v=values()[i];
  if(c!=null)return v+" "+UiText.catalog(c,v);if(mode==1&&i==2||mode==2&&i==8)return v==0?"No":"Yes";
  if(mode==2&&i==7)return v==0?"Male":"Female";return Integer.toString(v);}
 String description(){StringBuilder b=new StringBuilder(UiText.tr(title()));if(mode==0)return b.append(". ").append(UiText.tr(OPTIONS[choice])).toString();
  for(int i=0;i<values().length;i++)b.append(". ").append(UiText.tr(label(i))).append(": ").append(UiText.tr(value(i)));
  return b.append(". ").append(UiText.tr(confirm?"Confirm changes. OK applies; Back cancels.":"D-pad chooses; left/right changes; digits enter ID or value; OK edits.")).toString();}
}
