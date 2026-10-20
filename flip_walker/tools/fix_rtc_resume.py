#!/usr/bin/env python3
"""Restore the battery-backed clock on native core startup; no game/save patching."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
p=r/'native/pwcore/rtc.c';s=p.read_text();s=s.replace('''void rtc_init(rtc_t *rtc) {
    memset(rtc, 0, sizeof(rtc_t));
}''','''void rtc_init(rtc_t *rtc) {
    memset(rtc, 0, sizeof(rtc_t));
    /* Restarting Android's activity is not removal of the walker's battery.
     * Keep the virtual clock running; firmware still controls interrupt enables. */
    time_t now = time(NULL);
    rtc->time = *localtime(&now);
    rtc->rtccr1 = (1 << RTCCR1_RUN_BIT) | (1 << RTCCR1_12_24_BIT);
}''');p.write_text(s)

p=r/'tests/pwcore/ir_reconnect_test.c';s=p.read_text();test="""    assert(g_ctx.rtc.rtccr1 & (1 << RTCCR1_RUN_BIT));
    assert(g_ctx.rtc.time.tm_hour >= 0 && g_ctx.rtc.time.tm_hour < 24);
    rtc_set_cr2(&g_ctx.rtc,1);
    rtc_tick(STATES_PER_SECOND/4);
    assert(rtc_get_flg(&g_ctx.rtc) & 1);
    assert(rtc_poll_int(&g_ctx.rtc)==INT_QUARTER_SEC);
    rtc_set_flg(&g_ctx.rtc,0);assert(rtc_get_flg(&g_ctx.rtc)==0);
"""
if test not in s:s=s.replace('    assert(!pwcore_ir_enabled());',test+'    assert(!pwcore_ir_enabled());',1)
p.write_text(s)
