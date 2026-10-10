"""Detection accuracy against YOLO-format labels (one .txt per image: `class cx cy w h`, normalised).

python -m ops.perception.evaluate IMAGES LABELS [--classes drone,balloon,bird] [--tile 640]

Reports per class: precision / recall at the confidence threshold, AP50 (all-point, IoU ≥ 0.5),
recall by apparent size (shorter box side: <8, 8–16, 16–32, ≥32 px — the bins that matter for
ops/sources/scenario.py's detection model), false positives per frame, and latency.
"""
import argparse
import json
import time
from pathlib import Path

from ops.perception.detector import LABELS, Box, iou, load_detector
from ops.perception.frames import iter_frames

SIZE_BINS = ((0, 8), (8, 16), (16, 32), (32, 1e9))


def read_yolo(path: Path, w: int, h: int, classes) -> list[Box]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().split('\n'):
        p = line.split()
        if len(p) >= 5 and int(p[0]) < len(classes):
            cx, cy, bw, bh = (float(v) for v in p[1:5])
            out.append(Box((cx-bw/2)*w, (cy-bh/2)*h, (cx+bw/2)*w, (cy+bh/2)*h, classes[int(p[0])], 1.0))
    return out


def size_bin(b: Box) -> str:
    s = min(b.x2-b.x1, b.y2-b.y1)
    lo, hi = next(r for r in SIZE_BINS if r[0] <= s < r[1])
    return f'{lo}-{int(hi)}' if hi < 1e9 else f'{lo}+'


def match(preds: list[Box], gts: list[Box], thr: float = 0.5):
    """Greedy by score: → list of (pred, matched_gt or None), and the set of matched gt indices."""
    used, pairs = set(), []
    for p in sorted(preds, key=lambda b: -b.score):
        best, bi = 0.0, None
        for i, g in enumerate(gts):
            if i in used or g.label != p.label:
                continue
            v = iou(p, g)
            if v >= thr and v > best:
                best, bi = v, i
        if bi is not None:
            used.add(bi)
        pairs.append((p, gts[bi] if bi is not None else None))
    return pairs, used


def ap50(scored: list[tuple[float, bool]], n_gt: int) -> float:
    if n_gt == 0:
        return float('nan')
    tp = fp = 0
    prec, rec = [], []
    for _, hit in sorted(scored, key=lambda x: -x[0]):
        tp += hit; fp += not hit
        prec.append(tp/(tp+fp)); rec.append(tp/n_gt)
    ap, prev_r = 0.0, 0.0
    for i, r in enumerate(rec):
        ap += (r-prev_r)*max(prec[i:])
        prev_r = r
    return ap


def evaluate(frames, conf: float = 0.4, classes=LABELS, agnostic: bool = False):
    """frames: iterable of (preds, gts) per image (preds carry raw scores; conf applies to P/R).
    agnostic=True scores 'is there an object' only (for class-agnostic detectors such as SkyBlobDetector)."""
    if agnostic:
        classes = ('object',)
    scored = {c: [] for c in classes}
    n_gt = {c: 0 for c in classes}
    tp = {c: 0 for c in classes}
    fp = {c: 0 for c in classes}
    by_size = {}
    n_frames = 0
    for preds, gts in frames:
        if agnostic:
            preds = [Box(p.x1, p.y1, p.x2, p.y2, 'object', p.score) for p in preds]
            gts = [Box(g.x1, g.y1, g.x2, g.y2, 'object', g.score) for g in gts]
        preds = [p for p in preds if p.label in classes]
        gts = [g for g in gts if g.label in classes]
        n_frames += 1
        for g in gts:
            n_gt[g.label] += 1
        pairs, _ = match(preds, gts)
        for p, g in pairs:
            scored[p.label].append((p.score, g is not None))
        kept, used = match([p for p in preds if p.score >= conf], gts)
        for p, g in kept:
            tp[p.label] += g is not None
            fp[p.label] += g is None
        for i, g in enumerate(gts):
            k = by_size.setdefault(size_bin(g), [0, 0])
            k[0] += i in used; k[1] += 1
    out = dict(frames=n_frames, classes={})
    for c in classes:
        out['classes'][c] = dict(gt=n_gt[c], precision=tp[c]/(tp[c]+fp[c]) if tp[c]+fp[c] else None,
                                 recall=tp[c]/n_gt[c] if n_gt[c] else None, ap50=ap50(scored[c], n_gt[c]))
    out['recall_by_size_px'] = {k: dict(recall=v[0]/v[1], n=v[1]) for k, v in sorted(by_size.items(), key=lambda x: float(x[0].split('-')[0].rstrip('+')))}
    out['false_positives_per_frame'] = sum(fp.values())/max(n_frames, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('images')
    ap.add_argument('labels')
    ap.add_argument('--classes', default=','.join(LABELS), help='class order of the label files')
    ap.add_argument('--detector', default='skyblob', help='skyblob (light, default) or torchvision')
    ap.add_argument('--arch', default='fasterrcnn_mobilenet_v3_large_fpn')
    ap.add_argument('--tile', type=int, default=None)
    ap.add_argument('--conf', type=float, default=0.4)
    ap.add_argument('--agnostic', action='store_true', help='ignore classes (default for skyblob)')
    a = ap.parse_args()
    classes = tuple(a.classes.split(','))
    kw = dict(arch=a.arch) if a.detector == 'torchvision' else {}
    det = load_detector(a.detector, tile=a.tile, min_confidence=0.05, **kw)
    lat = []

    def frames():
        for _, _, img, name in iter_frames(a.images):
            h, w = img.shape[:2]
            t0 = time.perf_counter()
            preds = det.detect_boxes(img)
            lat.append(time.perf_counter()-t0)
            yield preds, read_yolo(Path(a.labels)/(Path(name).stem+'.txt'), w, h, classes)
    res = evaluate(frames(), a.conf, classes, agnostic=a.agnostic or a.detector == 'skyblob')
    res['latency_ms_median'] = round(sorted(lat)[len(lat)//2]*1000, 1) if lat else None
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
