#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,io,hashlib
import pyarrow.parquet as pq
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'cache/classifier-training';OUT.mkdir(exist_ok=True)
REV='0b2714987fa478483af9968de7c934580d0bb9a2'
def fetch(split):
 p=OUT/f'cifar-{split}.parquet'
 if not p.exists():
  with urllib.request.urlopen(f'https://huggingface.co/datasets/uoft-cs/cifar10/resolve/{REV}/plain_text/{split}-00000-of-00001.parquet',timeout=120) as src,p.with_suffix('.part').open('wb') as dst:
   while b:=src.read(4*1024*1024):dst.write(b)
  p.with_suffix('.part').replace(p)
 print('NEGATIVE_SOURCE',split,flush=True);return p
list(ThreadPoolExecutor(2).map(fetch,['train','test']))
for source,limit in [('train',2000),('test',500)]:
 count=0
 for batch in pq.ParquetFile(OUT/f'cifar-{source}.parquet').iter_batches(batch_size=128):
  for row in batch.to_pylist():
   if count>=limit:break
   split=source if source=='train' else 'validation' if count<250 else 'test';i=count if source=='train' or count<250 else count-250
   dest=OUT/'negatives'/split/f'{i:04d}.jpg';dest.parent.mkdir(parents=True,exist_ok=True)
   img=row.get('img',row.get('image'))
   with Image.open(io.BytesIO(img['bytes'])) as im:im.convert('RGB').resize((160,160),Image.Resampling.BILINEAR).save(dest,quality=92)
   count+=1
  if count>=limit:break
(OUT/'negative-source.json').write_text(json.dumps({'repo':'uoft-cs/cifar10','revision':REV,'sha256':{s:hashlib.sha256((OUT/f'cifar-{s}.parquet').read_bytes()).hexdigest() for s in ['train','test']}},indent=2));print('NEGATIVES_READY',flush=True)
