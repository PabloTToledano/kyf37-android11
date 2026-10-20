/* No game ROM needed: exercise the real emulated SCI/queues across two sessions. */
#define PW_LIBRARY
#include "../../native/pwcore/main.c"
#undef puts
#undef printf
#include <assert.h>
int main(void) {
    uint8_t rom[0xc000]={0}, ee[65536], out[263];
    memset(ee,255,sizeof ee);rom[1]=0x50;
    assert(pwcore_init(rom,sizeof rom,ee)==0);
    /* Firmware flags are RAM, never forced development-mode bits. */
    for (int value=0; value<256; value++) {
        g_ctx.ram[0xF7B5-RAM_start]=(uint8_t)value;
        assert(read8(&g_ctx,0xF7B5)==value);
    }
    /* Firmware flags are RAM, never forced development-mode bits. */
    for (int value=0; value<256; value++) {
        g_ctx.ram[0xF7B5-RAM_start]=(uint8_t)value;
        assert(read8(&g_ctx,0xF7B5)==value);
    }
    assert(g_ctx.rtc.rtccr1 & (1 << RTCCR1_RUN_BIT));
    assert(g_ctx.rtc.time.tm_hour >= 0 && g_ctx.rtc.time.tm_hour < 24);
    rtc_set_cr2(&g_ctx.rtc,1);
    rtc_tick(STATES_PER_SECOND/4);
    assert(rtc_get_flg(&g_ctx.rtc) & 1);
    assert(rtc_poll_int(&g_ctx.rtc)==INT_QUARTER_SEC);
    rtc_set_flg(&g_ctx.rtc,0);assert(rtc_get_flg(&g_ctx.rtc)==0);
    g_ctx.ram[0xF78E - RAM_start]=0xbe;g_ctx.ram[0xF78F - RAM_start]=0xef;
    assert(read16(&g_ctx,0xF78E)==0xbeef);
    g_ctx.ccr=0x21;assert(decw(&g_ctx,1,1)==0);assert(get_ccr_bit(&g_ctx,CCR_Z));assert((g_ctx.ccr&0x21)==0x21);
    assert(decw(&g_ctx,0x8000,1)==0x7fff);assert(get_ccr_bit(&g_ctx,CCR_V));
    assert(!pwcore_ir_enabled());
    for(int attempt=0;attempt<2;attempt++) {
        sci_set_scr(&g_ctx,0x10); /* receiver-first: no TX burst to open hardware */
        assert(pwcore_ir_enabled());assert(pwcore_ir_pop(out,sizeof out)==0);
        uint8_t b=(uint8_t)(0x50+attempt);pwcore_ir_push(&b,1);
        ir_update(&g_ctx,8001);assert(g_ctx.ssr & SCI_SSR_RDRF);
        assert(sci_get_rdr(&g_ctx)==b);
        sci_set_scr(&g_ctx,0x30);sci_set_tdr(&g_ctx,(uint8_t)(0xa0+attempt));
        ir_update(&g_ctx,IR_TX_FLUSH_STATES);
        assert(pwcore_ir_pop(out,sizeof out)==1);assert(out[0]==0xa0+attempt);
        sci_set_scr(&g_ctx,0);assert(!pwcore_ir_enabled());
    }
    assert(pwcore_init(rom,sizeof rom,ee)==0);assert(!pwcore_ir_enabled());
    puts("IR_RECONNECT_OK: receiver-first open, second RX/TX session, disable, reinitialization");
    return 0;
}
