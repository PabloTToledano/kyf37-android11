#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[2];a=r/'app/assets/ml';m=json.loads((a/'model.json').read_text());labels=json.loads((a/'labels.json').read_text());b=(a/'pokemon-int8.tflite').read_bytes()
assert hashlib.sha256(b).hexdigest()==m['modelSha256']
assert len(b)<=5*1024*1024
assert len(labels)==650 and [x['id'] for x in labels]==list(range(1,650))+[0]
assert m['experimental'] and not m['test']['hardwareVerified']
assert b[4:8]==b'TFL3'
print('MODEL_OK:',len(b),'bytes; 649 National IDs + unknown; INT8 export; experimental')
