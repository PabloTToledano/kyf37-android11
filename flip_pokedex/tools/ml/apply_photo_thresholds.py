#!/usr/bin/env python3
"""Idempotent template fix: load validation-selected photo thresholds from metadata."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'templates/src/org/kyf37/pokedex/LiteClassifier.java';s=p.read_text()
pairs=[('boolean unknown=best<0.18;','boolean unknown=best<metadata.optDouble("unknownBestThreshold",0.18);'),('boolean confident=!unknown && best>=0.6 && best-second>=0.15;','boolean confident=!unknown && best>=metadata.optDouble("confidentBestThreshold",0.6) && best-second>=metadata.optDouble("confidentMarginThreshold",0.15);')]
for old,new in pairs:
    if new in s:continue
    if s.count(old)!=1:raise SystemExit('Classifier threshold anchor mismatch; template unchanged')
    s=s.replace(old,new)
if s!=p.read_text():p.write_text(s)
print('PHOTO_THRESHOLDS_SOURCE_OK')
