#!/usr/bin/env python3
"""Rerunnable fixes to templates/ from the real-firmware conformance captures
(tests/conformance/*.jsonl, recorded melonDS + HG/SS <-> Powar running the walker ROM)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def patch(rel, old, new, tag):
    p = root / 'templates' / rel
    t = p.read_text()
    if tag in t: return
    assert old in t, f'{rel}: anchor for {tag} not found'
    p.write_text(t.replace(old, new, 1))
    print('applied', tag)

# 1. Uncompressed writes (02/82) may carry fewer than 128 bytes: HG/SS sends a 36-byte 82 D6
#    during registration; firmware writes the bytes and ACKs 04 D6.
patch('src/org/kyf37/walker/Walker.java',
'''                    byte[] decoded=(p.command&2)==0?Packet.decompress(p.payload):p.payload;
                    size(decoded,128);int a=(p.extra<<8)|(p.command&0x80);range(a,128);
                    System.arraycopy(decoded,0,memory,a,128);reply=4;extra=p.extra;break;''',
'''                    // conformance: short-write — raw writes may be 1..128 bytes (HG/SS sends 36 at D680)
                    byte[] decoded=(p.command&2)==0?Packet.decompress(p.payload):p.payload;
                    if(decoded.length<1||decoded.length>128)throw new IllegalArgumentException("write size");
                    int a=(p.extra<<8)|(p.command&0x80);range(a,decoded.length);
                    System.arraycopy(decoded,0,memory,a,decoded.length);reply=4;extra=p.extra;break;''',
'conformance: short-write')

# 2. Resilience: an identical repeat of the last game packet (IR echo or a resend after a lost
#    reply) gets the cached reply instead of re-executing — e.g. a repeated 38/5A must not restart the walk.
patch('src/org/kyf37/walker/Walker.java',
'''        if(!connected || !Arrays.equals(p.session,session))return null;''',
'''        if(!connected || !Arrays.equals(p.session,session))return null;
        // conformance: replay-safe — same request again means our reply was lost
        if(lastRequest!=null && Arrays.equals(lastRequest,wire))return lastReply==null?null:lastReply.clone();''',
'conformance: replay-safe')
patch('src/org/kyf37/walker/Walker.java',
'''            if(!Arrays.equals(old,memory))store.commit(memory.clone());
            return reply<0?null:new Packet(reply,extra,session,data).encode();''',
'''            if(!Arrays.equals(old,memory))store.commit(memory.clone());
            byte[] out=reply<0?null:new Packet(reply,extra,session,data).encode();
            lastRequest=wire.clone();lastReply=out==null?null:out.clone(); // conformance: cache reply
            return out;''',
'conformance: cache reply')
patch('src/org/kyf37/walker/Walker.java',
'''    private boolean connected, collectingGifts;''',
'''    private boolean connected, collectingGifts;
    private byte[] lastRequest, lastReply; // conformance: replay-safe cache''',
'conformance: replay-safe cache')
patch('src/org/kyf37/walker/Walker.java',
'''    public synchronized void disconnect(){connected=false;''',
'''    public synchronized void disconnect(){lastRequest=null;lastReply=null;connected=false;''',
'lastRequest=null;lastReply=null;connected')
