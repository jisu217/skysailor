"""D4 synthetic evaluation of the sky detector: recall by target size × contrast, false alarms, speed.

python -m ops.perception.synth_eval [--frames 6] [--width 3840 --height 2160] [--noise 2]

Each frame: sky gradient + sensor noise + a soft cloud + a textured building strip, with one row of
dark and one row of bright square targets of every size at one contrast (frames cycle through the
contrasts). Targets are kept apart: closer than about twice max_size they disturb each other's
background estimate — a known limit for dense groups such as balloon clusters. Ground truth is exact,
so this measures the detector, not labelling. Real footage (D2/D5) is still needed: haze, compression
and moving clouds are not modelled.
"""
import argparse
import json
import time

import numpy as np

from ops.perception.detector import SkyBlobDetector

SIZES = (2, 3, 4, 6, 8, 12, 20, 40)
CONTRASTS = (10, 20, 40, 80)                   # grey levels between target and local sky


def make_frame(rng, W, H, noise, contrast, sizes=SIZES):
    y = np.linspace(0, 1, H)[:, None]
    sky = (190-35*y)+np.zeros((H, W))                                  # brighter towards the horizon
    yy, xx = np.indices((H, W))
    sky += 35*np.exp(-(((xx-0.65*W)/(0.13*W))**2+((yy-0.23*H)/(0.08*H))**2))      # soft cloud
    sky += rng.normal(0, noise, (H, W))
    truth, cols = [], len(sizes)
    for r, sign in enumerate((-1, 1)):
        c = contrast
        for k, s in enumerate(sizes):
            x = int((k+0.5)*W/cols)+int(rng.integers(-10, 10))
            yv = int((0.18 if r == 0 else 0.48)*H)+int(rng.integers(-10, 10))
            local = float(sky[yv:yv+s, x:x+s].mean())
            sky[yv:yv+s, x:x+s] = np.clip(local+sign*c, 0, 255)
            truth.append((x, yv, s, c))
    bh = int(0.25*H)
    sky[H-bh:] = 80+70*rng.random((bh, W))+(np.indices((bh, W))[1] % 40 < 20)*30          # buildings
    g = np.clip(sky, 0, 255).astype(np.uint8)
    return np.repeat(g[:, :, None], 3, axis=2), truth


def run(frames=8, W=3840, H=2160, noise=2.0, seed=0, detector=None):
    det = detector or SkyBlobDetector()
    rng = np.random.default_rng(seed)
    hit, n, fp, ts = {}, {}, 0, []
    for i in range(frames):
        img, truth = make_frame(rng, W, H, noise, CONTRASTS[i % len(CONTRASTS)])
        t0 = time.perf_counter()
        boxes = det.detect_boxes(img)
        ts.append(time.perf_counter()-t0)
        inside = lambda b, x, y, s: b.x1-1 <= x+s/2 <= b.x2+1 and b.y1-1 <= y+s/2 <= b.y2+1
        for x, y, s, c in truth:
            n[(s, c)] = n.get((s, c), 0)+1
            hit[(s, c)] = hit.get((s, c), 0)+any(inside(b, x, y, s) for b in boxes)
        fp += sum(not any(inside(b, x, y, s) for x, y, s, _ in truth) for b in boxes)
    table = {f'{c}': {f'{s}px': round(hit[(s, c)]/n[(s, c)], 2) for s in SIZES} for c in CONTRASTS}
    return dict(frames=frames, size=f'{W}x{H}', noise=noise, recall_by_contrast_then_size=table,
                false_alarms_per_frame=round(fp/frames, 2), ms_per_frame_median=round(1000*sorted(ts)[len(ts)//2]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--frames', type=int, default=8)
    ap.add_argument('--width', type=int, default=3840)
    ap.add_argument('--height', type=int, default=2160)
    ap.add_argument('--noise', type=float, default=2.0)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    print(json.dumps(run(a.frames, a.width, a.height, a.noise, a.seed), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
