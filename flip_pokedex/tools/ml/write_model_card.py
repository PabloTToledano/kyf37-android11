#!/usr/bin/env python3
"""Render the measured exported model card; no invented hardware figures."""
import json
from pathlib import Path
r=Path(__file__).resolve().parents[2];m=json.loads((r/'app/assets/ml/model.json').read_text());t=m['test'];pct=lambda x:f'{x*100:.1f}%'
s=f'''# Experimental classifier model card

Model: MobileNetV2 alpha 0.35, 160 × 160 RGB, 649 species + unknown.
Bundled full INT8 weights: **{m['modelBytes']:,} bytes**.
SHA-256: `{m['modelSha256']}`.

| Held-out quantized-model measurement | Result |
|---|---:|
| Deterministic transformed test images | {t['n']} |
| Known-species transformed images | {t['known']} |
| Known species transformed top-1 accuracy | {pct(t['top1'])} |
| Known species transformed top-5 accuracy | {pct(t['top5'])} |
| Unknown recall on transformed negatives | {pct(t['unknownRecall'])} |
| High-confidence transformed coverage | {pct(t['confidentCoverage'])} |
| High-confidence transformed precision | {pct(t['confidentPrecision'])} |
| Clean held-out top-1 accuracy | {pct(m['cleanTest']['top1'])} |
| Clean held-out top-5 accuracy | {pct(m['cleanTest']['top5'])} |
| Host CPU median inference | {m['test']['hostMedianMs']:.1f} ms |
| Host CPU P95 inference | {m['test']['hostP95Ms']:.1f} ms |

The host timing excludes image loading and model initialization and is **not a
KYF37 measurement**. Phone latency, peak PSS, thermal behavior, camera capture
and camera-photo accuracy remain unverified. All results need manual confirmation.

Realistic-validation-selected temperature: {m['temperature']}; species-score
abstention threshold: {m['unknownBestThreshold']}; high-confidence score threshold:
{m['confidentBestThreshold']}; top-two margin: {m['confidentMarginThreshold']}. Validation acceptance gate met:
**{m['realisticValidationCalibration']['calibrated']}**. “High confidence” is an experimental
validation gate, not a guarantee or a calibrated probability. Runtime abstains
on blank crops or when the best species score, renormalized over species after
discarding the unknown logit, falls below the learned threshold.
Top-1/top-3 are raw class-rank metrics; the UI may abstain despite a known top rank.

The transformed set is generated deterministically from held-out images, with perspective, blur,
JPEG artifacts, low light, color casts, screen moiré, clutter, and crop variation. It is a
simulation, not a curated real-camera benchmark. The Pokémon image splits remove exact decoded-pixel duplicates across
splits; generic CIFAR negatives retain provider splits and were not separately
deduplication-audited. Near duplicates and artist/object/source grouping have
not been independently audited. Reported ranks use prepared 160-pixel test
inputs; Android preview/crop interpolation can change rankings. Inspected samples include sprites, anime art and rendered game artwork, not
a curated real-camera benchmark. It may overestimate real camera performance. These
metrics cover this split and do not establish equal accuracy for every species.

Dataset provenance, pinned downloads, split counts and full numerical results
are in `app/assets/ml/model.json`. See [implementation and reproduction](AI-CLASSIFIER.md)
and [third-party notices](THIRD_PARTY.md). Experimental, noncommercial distribution.
'''
(r/'MODEL-CARD.md').write_text(s);print(s)
