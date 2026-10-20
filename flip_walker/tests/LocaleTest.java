package org.kyf37.walker;
public final class LocaleTest {
 static int n;static void eq(String a,String b){if(!a.equals(b))throw new AssertionError(a+" != "+b);n++;}
 public static void main(String[] args){
  UiText.choose("en");eq(UiText.tr("Walk"),"Walk");eq(UiText.catalog(WalkerCatalog.ITEM,50),"Rare Candy");
  eq(UiText.defaultLanguage("es-ES"),"es-ES");eq(UiText.defaultLanguage("es-MX"),"es-ES");eq(UiText.defaultLanguage("en-GB"),"en");
  UiText.choose("es-ES");eq(UiText.tr("Walk"),"Pasear");eq(UiText.tr("CONNECT TO GAME"),"Conectar con juego");eq(UiText.tr("F2  Apply"),"F2  Aplicar");
  eq(UiText.catalog(WalkerCatalog.ITEM,50),"Caramelo Raro");eq(UiText.catalog(WalkerCatalog.MOVE,33),"Placaje");eq(UiText.catalog(WalkerCatalog.ABILITY,9),"Electricidad Estática");
  eq(UiText.catalog(WalkerCatalog.ITEM,135),"Diamansfera");eq(UiText.catalog(WalkerCatalog.ITEM,328),"MT01");eq(UiText.catalog(WalkerCatalog.ITEM,536),"Misticristal");
  eq(UiText.tr("Trainer: Walk"),"Entrenador: Walk");eq(UiText.tr("Trainer: None"),"Entrenador: None");eq(UiText.tr("ID 42 · Walk · 3 steps"),"ID 42 · Walk · 3 pasos");
  eq(UiText.tr("Reading ROM: 25% · F2 stops"),"Leyendo ROM: 25% · F2 para parar");eq(UiText.tr("Today steps (0=keep): 500"),"Pasos hoy (0=igual): 500");
  eq(UiText.tr("Paired: true"),"Vinculado: Sí");eq(UiText.tr("Has Pokemon: false"),"Tiene Pokémon: No");
  eq(UiText.tr("Operation cancelled. Changes may be partial; pre-change backup retained."),"Operación cancelada. Los cambios pueden ser parciales. Se conserva la copia previa.");
  RealMenu m=new RealMenu();m.mode=3;eq(m.value(0),"4 Poké Ball");m.item[0]=50;eq(m.value(0),"50 Caramelo Raro");
  for(int i=0;i<WalkerCatalog.ITEM.length;i++){if(UiText.catalog(WalkerCatalog.ITEM,i).isEmpty())throw new AssertionError("empty item");}n++;
  UiText.choose("en");eq(m.value(0),"50 Rare Candy");eq(UiText.tr("Unknown diagnostic 123"),"Unknown diagnostic 123");
  System.out.println("LOCALE_CHECKS="+n);
 }
}
