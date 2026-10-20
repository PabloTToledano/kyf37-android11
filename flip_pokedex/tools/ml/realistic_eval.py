#!/usr/bin/env python3
"""Clean and photo-like evaluation for the 649 + unknown TFLite classifier.

build: writes cache/realistic-eval/{validation,test}.npz from the held-out provider splits (no training data).
eval:  reports clean and realistic metrics for a TFLite model, mirroring LiteClassifier.java decisions.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'cache/classifier-dataset'
EVAL = ROOT / 'cache/realistic-eval'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from photo_sim import make_photo, OUT  # noqa: E402

UNKNOWN = 649


def load_rows(split):
    rows = json.loads((D / (split + '.json')).read_text())
    for r in rows:
        r['path'] = str(D / r['path']) if not Path(r['path']).is_absolute() else r['path']
    neg = ROOT / 'cache/classifier-training/negatives' / split
    if split == 'train':
        neg_split = 'train'
    else:
        neg_split = split
    negs = sorted(neg.glob('*.jpg'))
    rows += [{'path': str(f), 'label': UNKNOWN, 'national': 0} for f in negs]
    return rows


def load_img(path):
    return np.asarray(Image.open(path).convert('RGB').resize((OUT, OUT), Image.BILINEAR), np.uint8)


def build(seed_base=37):
    EVAL.mkdir(parents=True, exist_ok=True)
    for split, variants in [('validation', 1), ('test', 2)]:
        rows = load_rows(split)
        is_generic = lambda r: '/negatives/' in r['path']
        pool = [Image.open(r['path']).convert('RGB') for r in rows if is_generic(r)]
        xs, ys, src, kinds = [], [], [], []
        for i, r in enumerate(rows):
            obj = load_img(r['path'])
            opaque = is_generic(r)
            for v in range(variants):
                rng = np.random.default_rng([seed_base, 1 if split == 'test' else 2, i, v])
                xs.append(make_photo(rng, obj, pool, opaque=opaque)); ys.append(r['label']); src.append(i); kinds.append(v)
        # Empty scenes (no object) as unknown examples.
        n_empty = 250 if split == 'test' else 150
        for k in range(n_empty):
            rng = np.random.default_rng([seed_base, 3 if split == 'test' else 4, k])
            xs.append(make_photo(rng, np.zeros((OUT, OUT, 3), np.uint8), pool, empty=True)); ys.append(UNKNOWN); src.append(-1); kinds.append(-1)
        np.savez_compressed(EVAL / (split + '.npz'), x=np.asarray(xs, np.uint8), y=np.asarray(ys, np.int32), src=np.asarray(src, np.int32), variant=np.asarray(kinds, np.int32))
        print('BUILT', split, len(xs), 'photos', flush=True)
    # Clean sets (the original 160 px provider images) for comparison.
    for split in ['validation', 'test']:
        rows = load_rows(split)
        x = np.stack([load_img(r['path']) for r in rows]); y = np.asarray([r['label'] for r in rows], np.int32)
        np.savez_compressed(EVAL / ('clean-' + split + '.npz'), x=x, y=y)
        print('CLEAN', split, len(y), flush=True)


def run_tflite(model_path, x):
    import tensorflow as tf
    it_ = tf.lite.Interpreter(model_path=str(model_path), num_threads=4)
    it_.allocate_tensors()
    inp = it_.get_input_details()[0]; out = it_.get_output_details()[0]
    sc, zp = inp['quantization']; osc, ozp = out['quantization']
    res = np.zeros((len(x), 650), np.float32)
    for i in range(len(x)):
        q = np.clip(np.round(x[i].astype(np.float32) / sc + zp), 0, 255).astype(np.uint8)
        it_.set_tensor(inp['index'], q[None]); it_.invoke()
        res[i] = (it_.get_tensor(out['index'])[0].astype(np.float32) - ozp) * osc
    return res


def app_decide(logits, x, T, unk_thr, conf_thr, margin_thr, blank_var=12.0):
    """Mirror LiteClassifier.classify: blank check, temperature softmax, renormalise without unknown."""
    xf = x.astype(np.int64)
    lum = (xf[..., 0] * 77 + xf[..., 1] * 150 + xf[..., 2] * 29) >> 8
    lf = lum.reshape(len(x), -1).astype(np.float64)
    blank = (np.mean(lf ** 2, axis=1) - np.mean(lf, axis=1) ** 2) < blank_var
    z = logits / T
    z = z - z.max(1, keepdims=True)
    p = np.exp(z); p /= p.sum(1, keepdims=True)
    rest = np.maximum(1e-6, 1 - p[:, UNKNOWN])
    sp = p[:, :UNKNOWN] / rest[:, None]
    order = np.argsort(-sp, axis=1)
    best = sp[np.arange(len(sp)), order[:, 0]]; second = sp[np.arange(len(sp)), order[:, 1]]
    unknown = blank | (best < unk_thr)
    confident = (~unknown) & (best >= conf_thr) & (best - second >= margin_thr)
    return dict(order=order, best=best, second=second, unknown=unknown, confident=confident, blank=blank)


def metrics(dec, y):
    known = y < UNKNOWN
    neg = ~known
    top = dec['order']
    hit = lambda k: np.any(top[:, :k] == np.where(known, y, -1)[:, None], axis=1)
    shown = ~dec['unknown']
    m = {
        'n': int(len(y)), 'known': int(known.sum()), 'negatives': int(neg.sum()),
        'top1': float(hit(1)[known].mean()) if known.any() else None,
        'top3': float(hit(3)[known].mean()) if known.any() else None,
        'top5': float(hit(5)[known].mean()) if known.any() else None,
        'unknownRecall': float(dec['unknown'][neg].mean()) if neg.any() else None,
        'knownAnsweredRate': float(shown[known].mean()) if known.any() else None,
        'knownTop3WhenAnswered': float(hit(3)[known & shown].mean()) if (known & shown).any() else None,
        'negativeShownAsMatches': float(shown[neg].mean()) if neg.any() else None,
        'confidentCoverage': float(dec['confident'].mean()),
        'confidentPrecision': float((top[:, 0] == y)[dec['confident']].mean()) if dec['confident'].any() else None,
    }
    return m


def calibrate(logits, x, y, T):
    """Pick thresholds on realistic validation data only. Objective: correct species shown in top 3 minus negatives shown,
    subject to the confident label keeping at least 90% precision."""
    base = app_decide(logits, x, T, 0, 1, 1)
    known = y < UNKNOWN; neg = ~known
    top3 = np.any(base['order'][:, :3] == np.where(known, y, -1)[:, None], axis=1)
    best_scores = base['best']; margins = base['best'] - base['second']
    best = None
    for u in np.arange(.08, .45, .02):
        for c in np.arange(.3, .95, .05):
            for m in [.03, .05, .08, .1, .15, .2]:
                shown = ~(base['blank'] | (best_scores < u))
                score = (top3 & shown & known).sum() - (shown & neg).sum() - .5 * (shown & known & ~top3).sum()
                conf = shown & (best_scores >= c) & (margins >= m)
                if conf.sum() < 30 or (base['order'][conf, 0] == y[conf]).mean() < .9:
                    continue
                cand = (score, u, c, m)
                if best is None or cand > best:
                    best = cand
    if best is None:
        return dict(unk=.18, conf=.6, margin=.15, calibrated=False)
    return dict(unk=round(float(best[1]), 2), conf=round(float(best[2]), 2), margin=round(float(best[3]), 2), calibrated=True)


def evaluate(model_path, meta, labels=None):
    T = float(meta['temperature'])
    out = {}
    for split in ['clean-test', 'test']:
        z = np.load(EVAL / (split + '.npz'))
        logits = run_tflite(model_path, z['x'])
        dec = app_decide(logits, z['x'], T, meta.get('unknownBestThreshold', .18), meta.get('confidentBestThreshold', .6), meta.get('confidentMarginThreshold', .15))
        out[split] = metrics(dec, z['y'])
        if split == 'test':
            vv = z['variant']
            for name, mask in [('variant0', vv == 0), ('variant1', vv == 1)]:
                if mask.any():
                    out[split][name] = metrics({k: (v[mask] if isinstance(v, np.ndarray) else v) for k, v in dec.items()}, z['y'][mask])
    return out


def show(name, res):
    for k in ['clean-test', 'test']:
        m = res[k]
        print(f"{name} {k:10s} n={m['n']:5d} top1={m['top1']:.3f} top3={m['top3']:.3f} top5={m['top5']:.3f} "
              f"unkRecall={m['unknownRecall']:.3f} answered={m['knownAnsweredRate']:.3f} "
              f"top3|answered={m['knownTop3WhenAnswered']:.3f} negShown={m['negativeShownAsMatches']:.3f} "
              f"conf={m['confidentCoverage']:.3f} confPrec={m['confidentPrecision']:.3f}", flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'build':
        build()
    elif cmd == 'eval':
        model = Path(sys.argv[2]); meta = json.loads(Path(sys.argv[3]).read_text())
        res = evaluate(model, meta); show(model.name, res)
        print(json.dumps(res, indent=1))
