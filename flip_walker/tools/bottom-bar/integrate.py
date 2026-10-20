#!/usr/bin/env python3
"""Rerunnable fixed-grid corner-button icon integration; controls unchanged."""
from pathlib import Path
r=Path(__file__).resolve().parents[2]
(r/'templates/src/org/kyf37/walker/SoftKeyBar.java').write_text((r/'tools/bottom-bar/SoftKeyBar.java.txt').read_text())
p=r/'templates/src/org/kyf37/walker/WalkerActivity.java';s=p.read_text()
if 'SoftKeyBar.draw(' not in s:
 start=s.index('            text(page==0?"F1  Walk"');end=s.index('            c.restore();',start)
 s=s[:start]+'''            SoftKeyBar.draw(c,p,
                    page==0?"F1  Walk":"F1  Menu",
                    page==7?"F2  Language":page==2?"F2  Catch":connecting?"F2  Stop":page==8?(realMenu.confirm||confirmRom?"F2  Apply":"F2  Select"):"F2  Connect",
                    page==7?"F3  Mode":page==8?"F3  Export":"F3  Settings",
                    "F4  Back",
                    page==8?(connecting?"OK Stop":realMenu.confirm||confirmRom?"OK Apply":"OK Select"):page==5?"OK Link":page==1&&StepService.running?"OK Pause":page==1?"OK Walk":"OK Select");
''' +s[end:]
 p.write_text(s)
p=r/'templates/AndroidManifest.xml';s=p.read_text().replace('versionCode="4"','versionCode="5"').replace('0.4-es-ES','0.5-button-icons');p.write_text(s)
