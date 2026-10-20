#!/usr/bin/env python3
"""Implement Timer W clock selection/compare flags from H8/38602R manual §10."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'native/pwcore/main.h';s=p.read_text().replace('    uint8_t tmrw_rem;','    uint32_t tmrw_rem;');p.write_text(s)
p=r/'native/pwcore/main.c';s=p.read_text();a=s.index('static void tmrw_update(pw_context_t *ctx, int states) {');b=s.index('\n// ~115200 baud',a)
s=s[:a]+'''static void tmrw_update(pw_context_t *ctx, int states) {
    /* Peripheral clocks keep running while CPU interrupts are masked. */
    if (!(ctx->tmrw & 0x80) || states <= 0) return;
    static const uint32_t rates[8] = {STATES_PER_SECOND, STATES_PER_SECOND/2,
        STATES_PER_SECOND/4, STATES_PER_SECOND/8, 32768, 8192, 2048, 0};
    unsigned clock=(ctx->tcrw >> 4) & 7;
    uint64_t phase=(uint64_t)ctx->tmrw_rem + (uint64_t)(unsigned)states*rates[clock];
    uint32_t ticks=phase/STATES_PER_SECOND;
    ctx->tmrw_rem=phase%STATES_PER_SECOND;
    while (ticks) {
        uint32_t distance[4];
        uint16_t compare[4]={ctx->gra,ctx->grb,ctx->grc,ctx->grd};
        uint32_t overflow=65536u-ctx->tcnt, next=overflow;
        for (int channel=0;channel<4;channel++) {
            distance[channel]=(uint32_t)(uint16_t)(compare[channel]-ctx->tcnt)+1;
            if ((channel==2 && (ctx->tmrw & 0x10)) ||
                (channel==3 && (ctx->tmrw & 0x20))) distance[channel]=65537;
            if (distance[channel]<next) next=distance[channel];
        }
        uint32_t advance=ticks<next ? ticks : next;
        ctx->tcnt=(uint16_t)(ctx->tcnt+advance);ticks-=advance;
        if (advance!=next) break;
        if (advance==overflow) ctx->tsrw |= 0x80;
        for (int channel=0;channel<4;channel++)
            if (advance==distance[channel]) ctx->tsrw |= 1 << channel;
        if (advance==distance[0]) {
            if (ctx->tcrw & 0x80) ctx->tcnt=0;
            if (ctx->tmrw & 0x10) ctx->gra=ctx->grc;
        }
        if (advance==distance[1] && (ctx->tmrw & 0x20)) ctx->grb=ctx->grd;
    }
}
''' +s[b:];p.write_text(s)
p=r/'native/pwcore/pwcore_glue.inc';s=p.read_text();anchor='        done += d;';new='''        if (g_ctx.int_enabled && !get_ccr_bit(&g_ctx, CCR_I) && (g_ctx.tsrw & g_ctx.tierw & 0x8f))
            interrupt(&g_ctx, INT_TIMER_W);
''';s=s if new in s else s.replace(anchor,new+anchor,1);p.write_text(s)
