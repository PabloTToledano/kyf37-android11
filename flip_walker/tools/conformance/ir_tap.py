#!/usr/bin/env python3
"""Record a game <-> real-firmware session: melonDS (UDP 34560/34561) <-> tap <-> Powar (34571/34572).
Writes one JSON object per IR burst: {"t": seconds, "dir": "game"|"walker", "hex": raw wire bytes}.
Start Powar with POWAR_IR_PORT=34571 POWAR_IR_PEER=34572."""
import json, select, socket, sys, time
out = open(sys.argv[1], "a", buffering=1)
game = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); game.bind(("127.0.0.1", 34561))
walk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); walk.bind(("127.0.0.1", 34572))
t0 = time.time()
while True:
    r, _, _ = select.select([game, walk], [], [])
    for s in r:
        d, _ = s.recvfrom(2048)
        src = "game" if s is game else "walker"
        if s is game: walk.sendto(d, ("127.0.0.1", 34571))
        else: game.sendto(d, ("127.0.0.1", 34560))
        if len(d) > 1:
            out.write(json.dumps({"t": round(time.time() - t0, 4), "dir": src, "hex": d.hex()}) + "\n")
            dec = bytes(x ^ 0xAA for x in d)
            print(f"{src:6s} {dec[0]:02x} {dec[1]:02x} len={len(d)}", flush=True)
