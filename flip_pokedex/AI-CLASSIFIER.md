# Offline Pokémon identification

Implemented as an experimental feature in version 1.1. Press **9 on the list**
or choose **Options → Identify**. Take a photo with the system camera or import
an image with the system document picker. Use D-pad to move the crop, **2 / 8**
to zoom, **5** to reset, and **OK** to analyze. Choose a suggestion and press OK
to open its National dex entry. Clear cancels or returns to the crop. Caught
and favorite marks are never changed by recognition.

The model covers species 1–649 plus an unknown class. It is a MobileNetV2
alpha 0.35, 160 × 160 RGB classifier, fully integer quantized, with UINT8 input
and INT8 logits. The app bundles Google LiteRT Interpreter 1.4.2 and its 32-bit
ARMv7 native library; the development emulator APK also includes x86_64.
Inference uses two CPU threads on a single worker. No cloud, network permission,
GPU or NNAPI delegate is involved. Images are copied to private cache, size
limited to 32 MiB, decoded with downsampling, EXIF corrected and padded to a
512-pixel preview before cropping. The camera receives a temporary grant to
one nonexported capture-provider URI. There is no broad storage or camera
permission. Private cached inputs can persist until replaced or Android clears
cache; the app does not upload them.

A scan-line animation indicates work, with no fabricated percentage. Results
are suggestions requiring confirmation. Low confidence is labelled uncertain;
unknown and blank images can produce no suggestions. Confidence is not a
reliable probability of correctness. The model unloads when the screen pauses,
and cancellation suppresses stale results without racing native inference.

## Training and provenance

Training uses the public Hugging Face
[JJMack/pokemon-classification-gen1-9](https://huggingface.co/datasets/JJMack/pokemon-classification-gen1-9)
dataset at revision `959ff557b102fc3b4f912d0ca769273be5b9ca7f`, whose card
specifies **CC-BY-NC-SA-4.0**. Later-generation Pokémon are sampled as unknown
examples. Generic object negatives come from
[uoft-cs/cifar10](https://huggingface.co/datasets/uoft-cs/cifar10) at revision
`0b2714987fa478483af9968de7c934580d0bb9a2`. ImageNet pretrained MobileNetV2
weights initialize the backbone. Dataset download hashes, revisions, split
counts, quantized-model hash and actual test metrics are bundled in
`app/assets/ml/model.json`; species order is in `labels.json`.

Exact decoded-pixel duplicates are removed across the Pokémon splits, reserving
test first, then validation. Generic CIFAR negatives retain provider splits and
were not separately deduplication-audited. Artist/object/source grouping and near-duplicate leakage have
not been independently audited. Inspected samples include game sprites, anime art and rendered game artwork;
this is not a curated real-camera photo benchmark. Public artwork evaluation does not establish
performance on photos of toys, cards, screens, unusual fan art or the KYF37
camera. All species have training examples, but coverage is not equal accuracy
for every species. Keep this feature experimental and noncommercial; the
source dataset's license does not grant ownership of Pokémon art or trademarks.
See also the base app's data notices.

The training pipeline creates one deterministic cached photo-like view per
training image with `tools/ml/prepare_photo_augment.py`. It uses `photo_sim.py`
and only the cached training split and generic negatives, without downloading
training data. The views model camera framing, perspective, blur, compression,
low light, color casts, moiré and clutter. The 650-class head trains on original
and augmented views, then fine-tunes the last convolutional blocks with light
augmentation. `realistic_eval.py` builds fixed transformed validation/test sets
from held-out inputs. `accept_candidate.py` calibrates thresholds on transformed
validation images and promotes only if transformed top-1 and top-5 each improve
by at least two points, clean top-1/top-5 each stay within three points, and
the candidate passes the size, label and INT8 shape checks. Test remains held
out for reporting. Model quality numbers are summarized in `MODEL-CARD.md`;
retraining is seeded but not guaranteed byte-identical across TensorFlow/platform
versions.

## Reproduction

```sh
uv venv --python 3.11 flip_pokedex/cache/ml-venv
uv pip install --python flip_pokedex/cache/ml-venv/bin/python \
  -r flip_pokedex/tools/ml/requirements.lock --no-deps
flip_pokedex/cache/ml-venv/bin/python flip_pokedex/tools/ml/prepare_dataset.py
flip_pokedex/cache/ml-venv/bin/python flip_pokedex/tools/ml/prepare_negatives.py
bash device-inspection/build-locked.sh "$PWD/flip_pokedex/ml-train.log" \
  --script "$PWD/flip_pokedex/tools/ml/train-locked.sh"
bash device-inspection/build-locked.sh "$PWD/flip_pokedex/build.log" \
  --script "$PWD/flip_pokedex/tools/build.sh"
python3 flip_pokedex/tools/verify_apk.py
```

For emulator validation, build with `tools/build.sh --emulator` through the same
lock, install `dist/FlipPokedex-emulator.apk` on emulator-5580, and run
`cache/ml-venv/bin/python tools/ml/test_emulator.py`. This uses actual JNI
inference and the standard document picker. The shipping APK contains only
ARMv7; a host emulator result is not phone verification.

KYF37 latency, peak memory, real camera capture and thermal behavior remain
hardware acceptance gates. The original ≤5 MiB model, ≤30 MiB extra PSS,
median ≤2 s and P95 ≤4 s phone targets are targets, not measured claims.

`python3 tools/ml/apply_photo_thresholds.py` reapplies the idempotent runtime template fix that reads validation-selected thresholds from model metadata.
