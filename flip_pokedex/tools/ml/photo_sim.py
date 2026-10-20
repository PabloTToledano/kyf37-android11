#!/usr/bin/env python3
"""Photo-like corruption of 160 px artwork, used for training augmentation and the realistic evaluation set.

The pipeline imitates a low-end phone camera capture: the object is placed on a cluttered or screen-like
background, perspective and rotation are applied, light is dimmed and colour cast, the frame is blurred, noised,
moire-screened, low-resolution and JPEG-compressed, and finally cropped to the app's 82% framing square and
resized to the 160 px model input.
"""
import io
import numpy as np
from PIL import Image, ImageFilter

FRAME = 224      # simulated camera frame
CROP = 0.82      # IdentifyActivity keeps the centre 82% square of the capture
OUT = 160        # model input size
BILINEAR = Image.BILINEAR


def _perspective_coeffs(src, dst):
    """PIL PERSPECTIVE coefficients mapping output quad dst to input quad src."""
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); rhs.append(u)
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y]); rhs.append(v)
    return np.linalg.solve(np.asarray(rows, np.float64), np.asarray(rhs, np.float64))


def _alpha_from_white(arr):
    """Soft object mask: sprites and artwork are drawn on white, so near-white pixels become background."""
    d = 255.0 - arr.min(axis=2)
    return np.clip((d - 10.0) / 25.0, 0.0, 1.0)


def _background(rng, pool):
    S = FRAME
    kind = int(rng.integers(0, 8))
    if kind <= 2 and pool:  # real-world-ish texture from the generic-object pool
        src = pool[int(rng.integers(len(pool)))]
        side = int(rng.integers(90, 161))
        x, y = int(rng.integers(0, 161 - side)), int(rng.integers(0, 161 - side))
        bg = src.crop((x, y, x + side, y + side)).resize((S, S), BILINEAR)
        if rng.random() < .5:
            bg = bg.transpose(Image.FLIP_LEFT_RIGHT)
        return bg
    if kind == 3:  # plain coloured wall or cloth with grain
        c = rng.uniform(40, 230, 3)
        arr = np.ones((S, S, 3), np.float32) * c + rng.normal(0, rng.uniform(3, 14), (S, S, 3))
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if kind == 4:  # room: two-tone vertical gradient plus soft blobs
        top, bottom = rng.uniform(30, 240, 3), rng.uniform(30, 240, 3)
        t = np.linspace(0, 1, S, dtype=np.float32)[:, None, None]
        arr = top * (1 - t) + bottom * t + np.zeros((S, S, 3), np.float32)
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        for _ in range(int(rng.integers(1, 4))):
            cx, cy, r = rng.uniform(0, S, 2).tolist() + [rng.uniform(20, 120)]
            arr += rng.uniform(-70, 70, 3) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))[..., None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if kind == 5:  # dark monitor or TV: near-black with coloured blocks and scanlines
        arr = rng.uniform(0, 35, (S, S, 3)).astype(np.float32)
        for _ in range(int(rng.integers(2, 8))):
            x0, y0 = rng.integers(0, S - 20, 2)
            w, h = rng.integers(20, 120, 2)
            arr[y0:y0 + h, x0:x0 + w] += rng.uniform(40, 220, 3)
        arr[::2] *= 0.8
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if kind == 6:  # bright paper, card table or shop shelf
        base = rng.uniform(200, 255)
        arr = np.full((S, S, 3), base, np.float32) + rng.normal(0, 5, (S, S, 3))
        arr *= rng.uniform(0.85, 1.0, 3)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # kind 7: mottled clutter (fabric, carpet, foliage-like noise)
    small = rng.uniform(0, 255, (S // 8, S // 8, 3)).astype(np.uint8)
    img = Image.fromarray(small).resize((S, S), Image.BICUBIC)
    arr = np.asarray(img, np.float32) * rng.uniform(0.3, 0.8, 3)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _place(rng, frame, obj, opaque):
    S = FRAME
    alpha = np.ones(obj.shape[:2], np.float32) if opaque else _alpha_from_white(obj)
    side = int(S * rng.uniform(0.42, 0.95))
    im = Image.fromarray(obj.astype(np.uint8)).resize((side, side), BILINEAR)
    am = Image.fromarray((alpha * 255).astype(np.uint8)).resize((side, side), BILINEAR)
    ang = float(rng.uniform(-14, 14))
    im = im.rotate(ang, resample=BILINEAR, expand=True)
    am = am.rotate(ang, resample=BILINEAR, expand=True)
    cx = S / 2 + rng.uniform(-0.12, 0.12) * S
    cy = S / 2 + rng.uniform(-0.12, 0.12) * S
    frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), am)
    return frame


def _lighting(rng, arr):
    gain = rng.uniform(0.32, 1.18) if rng.random() < .55 else rng.uniform(0.8, 1.15)  # often dim indoor light
    arr = arr * gain
    arr = arr * rng.uniform(0.88, 1.12, 3)  # colour cast per channel
    if rng.random() < .3:  # warm tungsten or cool fluorescent
        arr = arr * (np.array([1.08, 1.0, 0.85]) if rng.random() < .5 else np.array([0.9, 1.0, 1.08]))
    arr = np.clip(arr, 0, 255) / 255.0
    arr = arr ** rng.uniform(0.8, 1.45)
    if rng.random() < .35:  # vignette
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        arr = arr * np.clip(1.15 - 0.35 * r, 0.4, 1.0)[..., None]
    return arr * 255.0


def _motion_blur(arr, n, horizontal):
    out = np.zeros_like(arr)
    for k in range(n):
        out += np.roll(arr, k - n // 2, axis=1 if horizontal else 0)
    return out / n


def make_photo(rng, obj, pool=None, opaque=False, empty=False):
    """Return a 160x160 uint8 RGB array that imitates a phone capture of obj (a 160 px RGB array)."""
    S = FRAME
    frame = _background(rng, pool)
    if not empty:
        frame = _place(rng, frame, obj, opaque)
    # Perspective: jitter the four corners of the output frame.
    j = rng.uniform(0.0, 0.07) * S
    src = [(rng.uniform(-j, j), rng.uniform(-j, j)), (S + rng.uniform(-j, j), rng.uniform(-j, j)),
           (S + rng.uniform(-j, j), S + rng.uniform(-j, j)), (rng.uniform(-j, j), S + rng.uniform(-j, j))]
    frame = frame.transform((S, S), Image.PERSPECTIVE, _perspective_coeffs(src, [(0, 0), (S, 0), (S, S), (0, S)]), BILINEAR)
    arr = _lighting(rng, np.asarray(frame, np.float32))
    if rng.random() < .55:  # focus blur
        arr = np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(rng.uniform(0.4, 2.2))), np.float32)
    if rng.random() < .15:  # hand shake
        arr = _motion_blur(arr, int(rng.integers(3, 8)), bool(rng.random() < .5))
    if rng.random() < .22:  # TV or monitor moire
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        p1, p2 = rng.uniform(2.2, 4.6, 2)
        amp = rng.uniform(0.03, 0.12)
        arr = arr * (1 + amp * np.sin(2 * np.pi * xx / p1) * np.sin(2 * np.pi * yy / p2))[..., None]
        arr = arr + rng.uniform(-6, 6, 3) * np.sin(2 * np.pi * yy / rng.uniform(6, 14))[..., None]  # colour bands
    sigma = rng.uniform(0, 20) * (1.6 if rng.random() < .4 else 1.0)
    arr = arr + rng.normal(0, sigma, arr.shape)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    # Low-resolution sensor, JPEG compression, then back to frame size.
    r = int(rng.integers(90, 225))
    small = Image.fromarray(arr).resize((r, r), BILINEAR)
    buf = io.BytesIO(); small.save(buf, format='JPEG', quality=int(rng.integers(16, 78))); buf.seek(0)
    img = Image.open(buf).convert('RGB').resize((S, S), BILINEAR)
    # Framing: the app keeps the centre 82% square, sometimes tighter (partial object) or off-centre.
    if rng.random() < .3:
        side = int(S * rng.uniform(0.6, 0.9))
    else:
        side = int(S * CROP * rng.uniform(0.94, 1.06))
    cx = S / 2 + rng.uniform(-0.05, 0.05) * S
    cy = S / 2 + rng.uniform(-0.05, 0.05) * S
    x0 = int(np.clip(cx - side / 2, 0, S - side)); y0 = int(np.clip(cy - side / 2, 0, S - side))
    return np.asarray(img.crop((x0, y0, x0 + side, y0 + side)).resize((OUT, OUT), BILINEAR), np.uint8)
