#define PW_LIBRARY
#include "../../native/pwcore/main.c"
#undef puts
#undef printf
#include <assert.h>
static pw_context_t t;
static void fresh(unsigned clock) {memset(&t,0,sizeof t);t.tmrw=0x80;t.tcrw=clock<<4;t.gra=t.grb=t.grc=t.grd=65535;}
int main(void) {
 for(unsigned clock=0;clock<4;clock++){fresh(clock);tmrw_update(&t,80);assert(t.tcnt==(80u>>clock));}
 fresh(4);tmrw_update(&t,STATES_PER_SECOND);assert(t.tcnt==32768);
 fresh(5);tmrw_update(&t,STATES_PER_SECOND);assert(t.tcnt==8192);
 fresh(6);tmrw_update(&t,STATES_PER_SECOND);assert(t.tcnt==2048);
 fresh(7);tmrw_update(&t,STATES_PER_SECOND);assert(t.tcnt==0);
 fresh(0);t.gra=10;t.grb=20;t.grc=30;t.grd=40;tmrw_update(&t,45);assert(t.tcnt==45);assert((t.tsrw&15)==15);
 fresh(0);t.tcnt=65534;tmrw_update(&t,3);assert(t.tcnt==1);assert(t.tsrw&128);
 fresh(0);t.gra=10;t.tcrw|=128;tmrw_update(&t,25);assert(t.tcnt==3);assert(t.tsrw&1);
 fresh(0);t.gra=10;t.grc=20;t.tmrw|=16;t.tcrw|=128;tmrw_update(&t,35);assert(t.gra==20);assert(t.tcnt==3);assert(!(t.tsrw&4));
 fresh(0);t.gra=0;t.tcrw|=128;tmrw_update(&t,1);assert(t.tcnt==0);assert(t.tsrw&1);
 fresh(0);t.tmrw=0;tmrw_update(&t,80);assert(t.tcnt==0);
 puts("TIMER_W_OK: clock dividers, subclock, masked CPU, compare A-D, overflow, reload, buffers, stop");
}
