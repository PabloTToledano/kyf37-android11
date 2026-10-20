#!/usr/bin/env python3
"""Calibrate a trained candidate on synthetic validation photos and promote only on held-out gains."""
import hashlib, json, shutil, sys
from pathlib import Path
import numpy as np
from scipy.special import softmax

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import realistic_eval as reval  # noqa: E402

APP = ROOT / 'app/assets/ml'
CANDIDATE = ROOT / 'cache/classifier-training/candidate-assets'
PREVIOUS = ROOT / 'cache/classifier-training/previous'
EVAL = ROOT / 'cache/realistic-eval'

def main():
    model = CANDIDATE / 'pokemon-int8.tflite'
    meta = json.loads((CANDIDATE / 'model.json').read_text())
    import tensorflow as tf
    blob = model.read_bytes()
    labels = json.loads((CANDIDATE / 'labels.json').read_text())
    assert len(blob) <= 6 * 1024 * 1024 and blob[4:8] == b'TFL3'
    assert hashlib.sha256(blob).hexdigest() == meta['modelSha256']
    assert len(labels) == 650 and [x['id'] for x in labels] == list(range(1, 650)) + [0]
    check = tf.lite.Interpreter(model_path=str(model), num_threads=2)
    check.allocate_tensors()
    inp, out = check.get_input_details()[0], check.get_output_details()[0]
    assert inp['shape'].tolist() == [1, meta['inputSize'], meta['inputSize'], 3]
    assert out['shape'].tolist() == [1, 650]
    assert inp['dtype'] == np.uint8 and out['dtype'] == np.int8
    check = None
    z = np.load(EVAL / 'validation.npz')
    logits = reval.run_tflite(model, z['x'])
    y = z['y']
    temps = [.5, .65, .8, 1., 1.25, 1.5, 2., 2.5, 3.]
    temperature = min(temps, key=lambda t: -np.log(np.maximum(softmax(logits / t, axis=1)[np.arange(len(y)), y], 1e-9)).mean())
    gate = reval.calibrate(logits, z['x'], y, temperature)
    meta.update({'temperature': temperature,
                 'unknownBestThreshold': gate['unk'],
                 'confidentBestThreshold': gate['conf'],
                 'confidentMarginThreshold': gate['margin'],
                 'realisticValidationCalibration': gate})
    test = reval.evaluate(model, meta)
    clean_runtime = meta['test']
    meta['test'] = test['test']
    meta['test']['hardwareVerified'] = False
    meta['cleanTest'] = test['clean-test']
    meta['test']['hostMedianMs'] = clean_runtime['hostMedianMs']
    meta['test']['hostP95Ms'] = clean_runtime['hostP95Ms']
    meta['modelSha256'] = hashlib.sha256(blob).hexdigest()
    meta['modelBytes'] = len(blob)
    (CANDIDATE / 'model.json').write_text(json.dumps(meta, indent=2))
    old_meta = json.loads((APP / 'model.json').read_text())
    old = reval.evaluate(APP / 'pokemon-int8.tflite', old_meta)
    new_known = meta['test']['known']
    old_known = old['test']['known']
    print('BASELINE_REALISTIC', json.dumps(old['test'], sort_keys=True), flush=True)
    print('CANDIDATE_REALISTIC', json.dumps(meta['test'], sort_keys=True), flush=True)
    print('CANDIDATE_CLEAN', json.dumps(meta['cleanTest'], sort_keys=True), flush=True)
    # Require practical gains on transformed held-out images and limit clean-image regression.
    improved = (meta['test']['top1'] >= old['test']['top1'] + .02 and
                meta['test']['top5'] >= old['test']['top5'] + .02 and
                meta['cleanTest']['top1'] >= old['clean-test']['top1'] - .03 and
                meta['cleanTest']['top5'] >= old['clean-test']['top5'] - .03 and
                len(blob) <= 6 * 1024 * 1024 and len(json.loads((CANDIDATE/'labels.json').read_text())) == 650)
    print('PROMOTION_GATE', improved, flush=True)
    if not improved:
        raise SystemExit('Candidate did not meet improvement and regression gates; current model retained')
    PREVIOUS.mkdir(parents=True, exist_ok=True)
    template_assets = ROOT / 'templates/assets/ml'
    template_assets.mkdir(parents=True, exist_ok=True)
    for name in ['pokemon-int8.tflite', 'labels.json', 'model.json']:
        src = APP / name
        prev = PREVIOUS / (name + '.prev')
        if not prev.exists(): shutil.copy2(src, prev)
        shutil.copy2(CANDIDATE / name, src)
        shutil.copy2(CANDIDATE / name, template_assets / name)
    print('MODEL_PROMOTED', meta['modelSha256'], meta['modelBytes'], flush=True)

if __name__ == '__main__': main()
