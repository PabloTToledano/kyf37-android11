#!/usr/bin/env python3
"""Pinned public photo/artwork dataset import; labels map directly to National IDs."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,io,collections
import pyarrow.parquet as pq
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[2];CACHE=ROOT/'cache/classifier-dataset';CACHE.mkdir(parents=True,exist_ok=True)
REPO='JJMack/pokemon-classification-gen1-9';REV='959ff557b102fc3b4f912d0ca769273be5b9ca7f'
def fetch(split):
 p=CACHE/(split+'.parquet');u=f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{split}.parquet'
 if not p.exists():
  with urllib.request.urlopen(u,timeout=120) as src,p.with_suffix('.part').open('wb') as dst:
   while chunk:=src.read(4*1024*1024):dst.write(chunk)
  p.with_suffix('.part').replace(p)
 print('FETCHED',split,p.stat().st_size,flush=True);return p
paths=list(ThreadPoolExecutor(3).map(fetch,['train','validation','test']))
# Deduplicate decoded pixels across splits, reserving independent evaluation first.
seen=set();report={'repo':REPO,'revision':REV,'license':'CC-BY-NC-SA-4.0','inputSha256':{},'splits':{},'notes':['Provider splits, exact decoded-pixel duplicates removed across splits; near-duplicate/source grouping not independently audited.','Later-generation Pokémon supply negative examples; arbitrary-object rejection still requires field validation.']}
for split in ['test','validation','train']:
 p=CACHE/(split+'.parquet');report['inputSha256'][split]=hashlib.sha256(p.read_bytes()).hexdigest();rows=[];counts=collections.Counter();duplicates=0
 for batch in pq.ParquetFile(p).iter_batches(batch_size=128):
  for row in batch.to_pylist():
   label=int(row['label']);
   if label<=0:continue
   imgdata=row['image_data'];blob=imgdata.get('bytes') if isinstance(imgdata,dict) else imgdata
   if not blob:continue
   try:
    with Image.open(io.BytesIO(blob)) as im:
     rgba=ImageOps.exif_transpose(im).convert('RGBA');rgb=Image.alpha_composite(Image.new('RGBA',rgba.size,'white'),rgba).convert('RGB');digest=hashlib.sha256(rgb.tobytes()+str(rgb.size).encode()).hexdigest()
     if digest in seen:duplicates+=1;continue
     seen.add(digest)
     category=label-1 if label<=649 else 649
     if category==649 and counts[category]>=({'train':1000,'validation':400,'test':400}[split]):continue
     file=CACHE/'images'/split/f'{label:04d}-{digest[:16]}.jpg';file.parent.mkdir(parents=True,exist_ok=True)
     if not file.exists():ImageOps.pad(rgb,(160,160),method=Image.Resampling.BILINEAR,color=(255,255,255)).save(file,quality=92)
     rows.append({'path':str(file.relative_to(CACHE)),'label':category,'national':label,'source':row.get('file_name',''),'pixelHash':digest});counts[category]+=1
   except (OSError,ValueError):continue
 (CACHE/(split+'.json')).write_text(json.dumps(rows))
 report['splits'][split]={'images':len(rows),'counts':dict(sorted(counts.items())),'exactDuplicatesRemoved':duplicates}
 print('EXTRACTED',split,len(rows),'classes',len(counts),flush=True)
assert all(int(k) in range(650) for k in report['splits']['train']['counts'])
assert len(report['splits']['train']['counts'])==650,'Missing training classes'
(CACHE/'manifest.json').write_text(json.dumps(report,indent=2));print('DATASET_READY',flush=True)
