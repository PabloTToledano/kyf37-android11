#!/usr/bin/env python3
"""Rerunnable: the emulated Pokéwalker (menu 9) and Flip Walker share one save (walker.eeprom),
so what the game sends to the emulated walker shows in Walk, Pokémon & items and Trainer card."""
from pathlib import Path
root = Path(__file__).resolve().parents[1] / 'templates'
def patch(rel, old, new, tag):
    p = root / rel; t = p.read_text()
    if tag in t: return
    assert old in t, f'{rel}: anchor for {tag}'
    p.write_text(t.replace(old, new, 1)); print('applied', tag)
patch('src/org/kyf37/walker/Walker.java',
'''    public synchronized byte[] snapshot(){return memory.clone();}''',
'''    public synchronized byte[] snapshot(){return memory.clone();}
    /** shared-save: adopt the emulated firmware's EEPROM (same layout) and persist it. */
    public synchronized void replaceAll(byte[] bytes)throws IOException{
        if(bytes.length!=65536)throw new IllegalArgumentException("Save must be 64 KiB");
        if(java.util.Arrays.equals(bytes,memory))return;
        byte[] old=memory;memory=bytes.clone();disconnect();
        try{store.commit(memory.clone());}catch(IOException e){memory=old;throw e;}
    }''', 'shared-save: adopt')
