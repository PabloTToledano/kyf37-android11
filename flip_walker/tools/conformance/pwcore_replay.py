#!/usr/bin/env python3
"""Drive the pwcore library (real walker ROM) with a recorded game session, in-process.
Usage: pwcore_replay.py libpwcore.so rom.bin eeprom.bin session.jsonl [out-eeprom.bin]
Re-keys each game packet to the session the emulated walker negotiates, waits for its
reply, and checks every EEPROM write chunk landed exactly as the game sent it."""
import ctypes, json, sys
lib = ctypes.CDLL(sys.argv[1])
rom = open(sys.argv[2], 'rb').read(); ee = bytearray(open(sys.argv[3], 'rb').read())
ev = [json.loads(l) for l in open(sys.argv[4])]
A = lambda b: bytes(x ^ 0xAA for x in b)
def ck(d):
    c = 2
    for i, v in enumerate(d): c += 0 if i in (2, 3) else (v << 8 if i % 2 == 0 else v)
    while c >> 16: c = (c & 0xffff) + (c >> 16)
    return c
def pack(cmd, extra, sess, payload):
    d = bytearray([cmd, extra, 0, 0]) + sess + payload; c = ck(d); d[2], d[3] = c & 0xff, c >> 8  # little-endian on the wire
    return A(d)
def lz(b):
    out = bytearray(); p = 4
    while len(out) < 128:
        f = b[p]; p += 1
        for bit in range(7, -1, -1):
            if len(out) >= 128: break
            if not f & (1 << bit): out.append(b[p]); p += 1
            else:
                a, c = b[p], b[p + 1]; p += 2
                for _ in range((a >> 4) + 3): out.append(out[-(((a & 15) << 8 | c) + 1)])
    return bytes(out)
assert lib.pwcore_init(rom, len(rom), bytes(ee)) == 0
buf = ctypes.create_string_buffer(300)
def run(ms, keys=0):
    for _ in range(ms // 4):
        if lib.pwcore_run(4, keys): sys.exit('CPU halted')
def pop():
    n = lib.pwcore_ir_pop(buf, 300); return buf.raw[:n] if n > 0 else None
def wait_reply(ms=400):
    for _ in range(ms // 4):
        run(4); r = pop()
        while r is not None and len(r) < 8: r = pop()
        if r: return A(r)
    return None
run(2000)
for _ in range(10): run(16, 1)
# wait for beacon
for _ in range(500):
    run(4); r = pop()
    if r == A(b'\xfc'): break
else: sys.exit('no beacon')
# last session in the capture
starts = [i for i, e in enumerate(ev) if e['dir'] == 'game' and A(bytes.fromhex(e['hex']))[0] == 0xfa]
games = [A(bytes.fromhex(e['hex'])) for e in ev[starts[-1]:] if e['dir'] == 'game']
master = games[0][4:8]
for _ in range(40):  # like the game, repeat SYN until the walker's receiver is on
    lib.pwcore_ir_push(pack(0xfa, 1, master, b''), 8)
    r = wait_reply(60)
    if r and r[0] == 0xf8: break
else: sys.exit('no F8')
sess = bytes(a ^ b for a, b in zip(master, r[4:8]))
bad = 0; replies = 0
for g in games[1:]:
    pkt = pack(g[0], g[1], sess, g[8:])
    lib.pwcore_ir_push(pkt, len(pkt))
    r = wait_reply()
    if g[0] == 0xf4: break
    if not r: print('no reply to %02x %02x' % (g[0], g[1])); bad += 1; continue
    replies += 1
    if g[0] in (0, 0x80, 2, 0x82):
        addr = (g[1] << 8) | (g[0] & 0x80)
        data = g[8:] if g[0] & 2 else lz(g[8:])
        ee_now = ctypes.string_at(lib.pwcore_eeprom(), 65536) if False else None
lib.pwcore_eeprom.restype = ctypes.POINTER(ctypes.c_uint8 * 65536)
final = bytes(lib.pwcore_eeprom().contents)
for g in games[1:]:
    if g[0] in (0, 0x80, 2, 0x82):
        addr = (g[1] << 8) | (g[0] & 0x80); data = g[8:] if g[0] & 2 else lz(g[8:])
        diff = [i for i in range(len(data)) if final[addr + i] != data[i]]
        if diff: bad += 1; print('chunk %04x: %d bytes differ, first at +%d (want %02x got %02x)' % (addr, len(diff), diff[0], data[diff[0]], final[addr + diff[0]]))
print('replies %d, problems %d' % (replies, bad))
if len(sys.argv) > 5: open(sys.argv[5], 'wb').write(final)
sys.exit(1 if bad else 0)
