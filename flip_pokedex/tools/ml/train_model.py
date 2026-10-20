#!/usr/bin/env python3
"""Train/export a small, honest 649-species + unknown CPU classifier. Run under build lock."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];os.environ.setdefault('TF_USE_LEGACY_KERAS','1');os.environ.setdefault('KERAS_HOME',str(ROOT/'cache/keras'));os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2');os.environ.setdefault('OMP_NUM_THREADS','4')
import json,hashlib,time,collections
import numpy as np
import tensorflow as tf
from PIL import Image
from scipy.special import softmax
np.random.seed(37);tf.random.set_seed(37);tf.config.threading.set_inter_op_parallelism_threads(2);tf.config.threading.set_intra_op_parallelism_threads(4)
k=tf.keras;D=ROOT/'cache/classifier-dataset';OUT=ROOT/'cache/classifier-training';OUT.mkdir(exist_ok=True);ASSETS=OUT/'candidate-assets';ASSETS.mkdir(parents=True,exist_ok=True)
rows={s:json.loads((D/(s+'.json')).read_text()) for s in ['train','validation','test']}
# The only synthetic views are generated from the cached licensed training split.
photo_rows=json.loads((ROOT/'cache/classifier-training/photo-train.json').read_text())
rows['train'] += photo_rows
# Public generic-object negatives complement the later-generation Pokémon negatives.
for split in rows:
 for file in sorted((OUT/'negatives'/split).glob('*.jpg')):
  rows[split].append({'path':str(file),'label':649,'national':0})
assert len(rows['train'])>12000, 'Run prepare_negatives.py first'
def path(r):return str(D/r['path']) if not Path(r['path']).is_absolute() else r['path']
def dataset(split,batch=32,augment=False):
 rr=rows[split];ds=tf.data.Dataset.from_tensor_slices(([path(r) for r in rr],[r['label'] for r in rr]))
 if augment:ds=ds.shuffle(len(rr),seed=37,reshuffle_each_iteration=True)
 def load(p,y):return tf.cast(tf.io.decode_jpeg(tf.io.read_file(p),channels=3),tf.float32),y
 return ds.map(load,num_parallel_calls=2).batch(batch).prefetch(1)
base=k.applications.MobileNetV2(input_shape=(160,160,3),alpha=.35,include_top=False,weights='imagenet',pooling='avg');base.trainable=False
inp=k.Input((160,160,3),name='pixels');x=k.layers.Rescaling(1/127.5,offset=-1)(inp);features=base(x,training=False);extractor=k.Model(inp,features)
F={};Y={}
for split in rows:
 cache=OUT/(split+'-features.npz')
 if cache.exists() and len(np.load(cache)['y'])==len(rows[split]):
  z=np.load(cache);F[split]=z['x'];Y[split]=z['y']
 else:
  ff=[];yy=[]
  for i,(images,labels) in enumerate(dataset(split)):
   ff.append(extractor(images,training=False).numpy());yy.append(labels.numpy())
   if i%50==0:print('FEATURES',split,i*32,'/',len(rows[split]),flush=True)
  F[split]=np.concatenate(ff);Y[split]=np.concatenate(yy);np.savez_compressed(cache,x=F[split],y=Y[split])
head_in=k.Input((1280,));dense=k.layers.Dense(650,kernel_regularizer=k.regularizers.l2(1e-4),name='species_logits');head=k.Model(head_in,dense(k.layers.Dropout(.2)(head_in)))
head.compile(k.optimizers.Adam(.003),k.losses.SparseCategoricalCrossentropy(from_logits=True),metrics=['accuracy',k.metrics.SparseTopKCategoricalAccuracy(k=3,name='top3')])
counts=collections.Counter(Y['train']);cw={i:float(np.clip(np.sqrt(len(Y['train'])/(650*counts[i])),.1,4)) for i in range(650)}
head.fit(F['train'],Y['train'],batch_size=256,epochs=60,validation_data=(F['validation'],Y['validation']),class_weight=cw,callbacks=[k.callbacks.EarlyStopping(patience=8,restore_best_weights=True)],verbose=2)
# Fine-tune the last convolutional blocks; keep batch norm statistics frozen.
for layer in base.layers[-40:]:
 if not isinstance(layer,k.layers.BatchNormalization):layer.trainable=True
base.trainable=True
for layer in base.layers[:-40]:layer.trainable=False
for layer in base.layers:
 if isinstance(layer,k.layers.BatchNormalization):layer.trainable=False
aug=k.Sequential([k.layers.RandomFlip('horizontal'),k.layers.RandomRotation(.04),k.layers.RandomZoom(.08),k.layers.RandomContrast(.15)])
train_pixels=k.Input((160,160,3));train_features=base(k.layers.Rescaling(1/127.5,offset=-1)(aug(train_pixels)),training=False)
train=k.Model(train_pixels,dense(k.layers.Dropout(.15)(train_features)))
train.compile(k.optimizers.Adam(1e-4),k.losses.SparseCategoricalCrossentropy(from_logits=True),metrics=['accuracy',k.metrics.SparseTopKCategoricalAccuracy(k=3,name='top3')])
train.fit(dataset('train',32,True),epochs=8,validation_data=dataset('validation'),class_weight=cw,callbacks=[k.callbacks.EarlyStopping(patience=3,restore_best_weights=True)],verbose=2)
model=k.Model(inp,dense(base(k.layers.Rescaling(1/127.5,offset=-1)(inp),training=False)))
model.save(OUT/'pokemon-float.keras')
converter=tf.lite.TFLiteConverter.from_keras_model(model);converter.optimizations=[tf.lite.Optimize.DEFAULT]
representative=np.random.default_rng(37).choice(len(rows['train']),300,replace=False)
def calibration():
 for i in representative:
  yield [np.asarray(Image.open(path(rows['train'][int(i)])).convert('RGB'),dtype=np.float32)[None]]
converter.representative_dataset=calibration;converter.target_spec.supported_ops=[tf.lite.OpsSet.TFLITE_BUILTINS_INT8];converter.inference_input_type=tf.uint8;converter.inference_output_type=tf.int8
blob=converter.convert();(ASSETS/'pokemon-int8.tflite').write_bytes(blob)
interpreter=tf.lite.Interpreter(model_content=blob,num_threads=2);interpreter.allocate_tensors();it=interpreter.get_input_details()[0];ot=interpreter.get_output_details()[0]
def infer(split):
 out=[];ms=[]
 for i,r in enumerate(rows[split]):
  pixels=np.asarray(Image.open(path(r)).convert('RGB'),dtype=np.float32);sc,zp=it['quantization'];q=np.clip(np.round(pixels/sc+zp),0,255).astype(np.uint8)
  interpreter.set_tensor(it['index'],q[None]);start=time.perf_counter();interpreter.invoke();ms.append((time.perf_counter()-start)*1000);sc,zp=ot['quantization'];out.append((interpreter.get_tensor(ot['index'])[0].astype(np.float32)-zp)*sc)
  if i%500==0:print('INT8_EVAL',split,i,flush=True)
 return np.asarray(out),np.asarray(ms)
vl,vms=infer('validation');vy=np.asarray([r['label'] for r in rows['validation']]);tl,tms=infer('test');ty=np.asarray([r['label'] for r in rows['test']])
Ts=[.75,1,1.5,2,3];T=min(Ts,key=lambda t:-np.log(np.maximum(softmax(vl/t,axis=1)[np.arange(len(vy)),vy],1e-9)).mean());vp=softmax(vl/T,axis=1);top=np.argsort(vp,axis=1)[:,-2:];marg=vp[np.arange(len(vy)),top[:,-1]]-vp[np.arange(len(vy)),top[:,-2]];pred=vp.argmax(1)
threshold=.99;calibrated=False
for t in [.3,.4,.5,.6,.7,.8,.9,.95,.98,.99]:
 accept=(pred<649)&(vp[:,649]<.35)&(vp.max(1)>=t)&(marg>=.05)
 if accept.sum()>=30 and (pred[accept]==vy[accept]).mean()>=.95:threshold=t;calibrated=True;break
probs=softmax(tl/T,axis=1);pred=probs.argmax(1);known=ty<649;tops=np.argsort(probs,axis=1)[:,-3:];margin=np.sort(probs,axis=1)[:,-1]-np.sort(probs,axis=1)[:,-2];accepted=calibrated&(pred<649)&(probs[:,649]<.35)&(probs.max(1)>=threshold)&(margin>=.05)
index=json.loads((ROOT/'app/assets/data/index.json').read_text());names={r['id']:r['name'] for r in index if r['id']==r['species']}
labels=[{'id':i,'name':names[i]} for i in range(1,650)]+[{'id':0,'name':'Unknown'}];(ASSETS/'labels.json').write_text(json.dumps(labels,ensure_ascii=False))
meta={'version':1,'experimental':True,'architecture':'MobileNetV2 alpha=0.35','inputSize':160,'classes':650,'temperature':T,'confidenceThreshold':threshold,'marginThreshold':.05,'unknownThreshold':.35,'calibratedAcceptanceGateMet':calibrated,'modelSha256':hashlib.sha256(blob).hexdigest(),'modelBytes':len(blob),'dataset':json.loads((D/'manifest.json').read_text()),'genericNegatives':json.loads((OUT/'negative-source.json').read_text()),'test':{'images':len(ty),'knownImages':int(known.sum()),'knownTop1':float((pred[known]==ty[known]).mean()),'knownTop3':float(np.any(tops[known]==ty[known,None],axis=1).mean()),'unknownRecall':float(((pred[~known]==649)|(probs[~known,649]>=.35)).mean()),'acceptedCoverage':float(accepted.mean()),'acceptedPrecision':float((pred[accepted]==ty[accepted]).mean()) if accepted.any() else None,'hostMedianMs':float(np.median(tms)),'hostP95Ms':float(np.percentile(tms,95)),'hardwareVerified':False},'limitations':['Experimental public-dataset evaluation; actual KYF37 camera accuracy and latency are not hardware verified.','Exact duplicates removed but artist/object/source grouping and near-duplicate leakage not independently audited.','Confidence is not a guaranteed probability; user must confirm all matches.']}
(ASSETS/'model.json').write_text(json.dumps(meta,indent=2));(OUT/'evaluation.json').write_text(json.dumps(meta,indent=2))
fixtures=ROOT/'dist/qa-classifier';fixtures.mkdir(parents=True,exist_ok=True);cases=[]
for target in [1,25,133,150,252,393,494,501,646,649,0]:
 ids=[i for i,r in enumerate(rows['test']) if r['national']==target and (pred[i]==r['label'] or target==0)]
 if not ids:continue
 i=ids[0];dest=fixtures/f'input-{target}.jpg';dest.write_bytes(Path(path(rows['test'][i])).read_bytes());cases.append({'file':dest.name,'national':target,'expectedTop1Id':int(pred[i]+1) if pred[i]<649 else 0,'top3Ids':[int(j+1) if j<649 else 0 for j in np.argsort(probs[i])[::-1][:3]],'maxScore':float(probs[i].max())})
(fixtures/'golden.json').write_text(json.dumps(cases,indent=2));print('MODEL_READY',json.dumps(meta['test']),len(blob),flush=True)
