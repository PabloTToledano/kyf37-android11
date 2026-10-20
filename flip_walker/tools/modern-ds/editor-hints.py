#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
s=s.replace('text((realMenu.row+1)+" / "+realMenu.count()+"  < > CHANGE · DIGITS: ID",28,573,15,red);','text(realMenu.editing?"ENTER VALUE / ID: "+(realMenu.digits.isEmpty()?"...":realMenu.digits)+" · OK DONE":(realMenu.row+1)+" / "+realMenu.count()+"  < > CHANGE · DIGITS: ID",28,573,15,red);')
s=s.replace('page==8?"F2  Select":"F2  Connect"','page==8?(realMenu.confirm||confirmRom?"F2  Apply":"F2  Select"):"F2  Connect"')
p.write_text(s)
