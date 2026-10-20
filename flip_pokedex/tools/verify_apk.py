#!/usr/bin/env python3
"""Verify the exact offline data, trained weights, labels and pinned runtime in an APK."""
import hashlib,json,zipfile,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1];apk=Path(sys.argv[1]) if len(sys.argv)>1 else r/'dist/FlipPokedex.apk'
sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(apk) as z:
 packaged=json.loads(z.read('assets/data/manifest.json'));source=json.loads((r/'app/assets/data/manifest.json').read_text());assert packaged==source,'APK contains an older data import'
 for name,expected in packaged['files'].items():assert sha(z.read('assets/'+name))==expected,name
 model=json.loads(z.read('assets/ml/model.json'))
 for name in ['model.json','labels.json','pokemon-int8.tflite']:assert z.read('assets/ml/'+name)==(r/'app/assets/ml'/name).read_bytes(),name
 assert sha(z.read('assets/ml/pokemon-int8.tflite'))==model['modelSha256']
 assert z.getinfo('assets/ml/pokemon-int8.tflite').compress_type==zipfile.ZIP_STORED,'Model must be memory-mappable'
 assert 'lib/armeabi-v7a/libtensorflowlite_jni.so' in z.namelist()
 abis=[]
 for name in z.namelist():
  if name.endswith('/libtensorflowlite_jni.so'):
   abi=name.split('/')[1];assert z.read(name)==(r/'app/libs'/abi/'libtensorflowlite_jni.so').read_bytes();abis.append(abi)
 record={'apkSha256':sha(apk.read_bytes()),'dexSha256':sha(z.read('classes.dex')),'sizeBytes':apk.stat().st_size,'assetFilesVerified':len(packaged['files']),'species':packaged['species'],'entries':packaged['entries'],'sprites':packaged['sprites'],'cries':packaged['cries'],'modelSha256':model['modelSha256'],'modelBytes':model['modelBytes'],'classifierLabels':650,'nativeAbis':abis,'hardwareVerified':False}
(r/'dist'/(apk.stem+'-packaged-validation.json')).write_text(json.dumps(record,indent=2));print('PACKAGED_ASSETS_OK',json.dumps(record))
