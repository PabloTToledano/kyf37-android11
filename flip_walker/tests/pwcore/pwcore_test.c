/* Host smoke test for the pwcore library: boot, render, IR beacon after a button press. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../native/pwcore/pwcore.h"
static uint8_t *load(const char *p, int *n) {
    FILE *f = fopen(p, "rb"); if (!f) { perror(p); exit(2); }
    uint8_t *b = calloc(1, 1 << 16); *n = fread(b, 1, 1 << 16, f); fclose(f); return b;
}
int main(int argc, char **argv) {
    int rn, en; uint8_t *rom = load(argv[1], &rn), *ee = load(argv[2], &en);
    if (pwcore_init(rom, rn, ee)) return 1;
    for (int i = 0; i < 120; i++) if (pwcore_run(16, 0)) { puts("HALT during boot"); return 1; }
    uint8_t fb[PWCORE_W * PWCORE_H]; pwcore_frame(fb);
    int dark = 0; for (int i = 0; i < PWCORE_W * PWCORE_H; i++) dark += fb[i] != 0;
    FILE *o = fopen(argv[3], "wb"); fprintf(o, "P5 %d %d 3\n", PWCORE_W, PWCORE_H);
    for (int i = 0; i < PWCORE_W * PWCORE_H; i++) fputc(3 - fb[i], o); fclose(o);
    printf("boot ok, %d non-blank pixels\n", dark);
    for (int i = 0; i < 10; i++) pwcore_run(16, PWCORE_KEY_ENTER);
    int beacons = 0; uint8_t buf[300];
    for (int i = 0; i < 120; i++) { pwcore_run(16, 0); int n; while ((n = pwcore_ir_pop(buf, sizeof buf)) > 0) if (n == 1 && (buf[0] ^ 0xAA) == 0xFC) beacons++; }
    printf("IR beacons after press: %d\n", beacons);
    return dark > 100 && beacons > 0 ? 0 : 1;
}
