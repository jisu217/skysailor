"""② Object detection on ground-received frames → CameraDetection. See ops/docs/DESIGN.md §5.2.

Runs on the ground station, not on the dome. Detection only has to say "something is in the sky
here"; what it is, is decided by ⑤ identification (wind-relative motion + Remote ID). So the default
backend is a light, class-agnostic image-processing detector; a learned model is optional.

Backends
- SkyBlobDetector (default): small dark/bright blobs against smooth sky, OpenCV only, CPU, no model.
  Labels 'unknown'.
- TorchvisionDetector (optional): COCO-pretrained model (BSD); labels mapped provisionally
  (bird→bird, kite→balloon, airplane→drone). Needs torch/torchvision.
- TiledDetector: wraps a model for small targets by also running it on overlapping tiles.
"""
from dataclasses import dataclass

import numpy as np

from ops.core.schemas import CameraDetection

LABELS = ('drone', 'balloon', 'bird', 'unknown')


@dataclass
class Box:
    x1: float
    y1: float
    x2: float
    y2: float
    label: str
    score: float

    def xywh(self):
        return (self.x1, self.y1, self.x2-self.x1, self.y2-self.y1)


def iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a.x2, b.x2)-max(a.x1, b.x1))
    iy = max(0.0, min(a.y2, b.y2)-max(a.y1, b.y1))
    inter = ix*iy
    union = (a.x2-a.x1)*(a.y2-a.y1)+(b.x2-b.x1)*(b.y2-b.y1)-inter
    return inter/union if union > 0 else 0.0


def nms(boxes: list[Box], thr: float = 0.5) -> list[Box]:
    """Class-wise non-maximum suppression, highest score first."""
    keep = []
    for b in sorted(boxes, key=lambda x: -x.score):
        if all(k.label != b.label or iou(k, b) < thr for k in keep):
            keep.append(b)
    return keep


def _contains(a: Box, b: Box, pad: float = 2.0) -> bool:
    """b lies inside a (with a small margin): fragments next to a stronger blob."""
    return a.x1-pad <= b.x1 and a.y1-pad <= b.y1 and b.x2 <= a.x2+pad and b.y2 <= a.y2+pad


def _gap(a: Box, b: Box) -> float:
    """Edge-to-edge distance between two boxes (0 when they overlap)."""
    return max(0.0, max(a.x1, b.x1)-min(a.x2, b.x2), max(a.y1, b.y1)-min(a.y2, b.y2))


class Detector:
    """Base: subclasses implement detect_boxes(frame) → list[Box] in frame pixels."""
    min_confidence = 0.4

    def detect_boxes(self, frame: np.ndarray) -> list[Box]:
        raise NotImplementedError

    def detect(self, frame: np.ndarray, t: float, node_id: str, camera_id: int = 0) -> list[CameraDetection]:
        h, w = frame.shape[:2]
        return [CameraDetection(t=t, node_id=node_id, camera_id=camera_id, bbox=b.xywh(), image_size=(w, h),
                                label=b.label, confidence=float(b.score))
                for b in self.detect_boxes(frame) if b.label in LABELS and b.score >= self.min_confidence]


class TiledDetector(Detector):
    """Run `inner` on the full frame and on overlapping tiles, then merge (small-object recall)."""

    def __init__(self, inner: Detector, tile: int = 640, overlap: float = 0.2, full_frame: bool = True):
        self.inner, self.tile, self.overlap, self.full_frame = inner, tile, overlap, full_frame
        self.min_confidence = inner.min_confidence

    def tiles(self, h: int, w: int):
        step = max(1, int(self.tile*(1-self.overlap)))
        ys = list(range(0, max(h-self.tile, 0)+1, step)) or [0]
        xs = list(range(0, max(w-self.tile, 0)+1, step)) or [0]
        if ys[-1]+self.tile < h:
            ys.append(h-self.tile)
        if xs[-1]+self.tile < w:
            xs.append(w-self.tile)
        return [(y, x) for y in ys for x in xs]

    def detect_boxes(self, frame):
        h, w = frame.shape[:2]
        out = list(self.inner.detect_boxes(frame)) if self.full_frame else []
        for y, x in self.tiles(h, w):
            for b in self.inner.detect_boxes(frame[y:y+self.tile, x:x+self.tile]):
                out.append(Box(b.x1+x, b.y1+y, b.x2+x, b.y2+y, b.label, b.score))
        return nms(out)


class SkyBlobDetector(Detector):
    """Class-agnostic small-object detector for sky backgrounds.

    1. sky mask  — at 1/4 resolution, erase targets (closing + opening), keep regions whose local
                   standard deviation is low (smooth sky); buildings, ground and cloud texture drop out
    2. residual  — morphological black-hat (darker than surroundings) and top-hat (brighter) with a
                   kernel larger than the biggest target
    3. threshold — residual above max(min_contrast, k × robust noise of the sky residual)
    4. blobs     — connected components between min_size and max_size px → boxes labelled 'unknown',
                   confidence rising with contrast over threshold
    """

    def __init__(self, max_size: int = 64, min_size: int = 2, k: float = 6.0, min_contrast: float = 10.0,
                 sky_std: float = 6.0, min_confidence: float = 0.4):
        self.max_size, self.min_size, self.k = max_size, min_size, k
        self.min_contrast, self.sky_std, self.min_confidence = min_contrast, sky_std, min_confidence

    def sky_mask(self, g):
        import cv2
        h, w = g.shape
        raw = cv2.resize(g, (max(1, w//4), max(1, h//4)), interpolation=cv2.INTER_AREA)
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (self.max_size//4*2+3,)*2)   # erase targets up to max_size
        small = cv2.morphologyEx(cv2.morphologyEx(raw, cv2.MORPH_CLOSE, k), cv2.MORPH_OPEN, k)
        f = small.astype(np.float32)
        mean = cv2.blur(f, (15, 15))
        std = np.sqrt(np.maximum(cv2.blur(f*f, (15, 15))-mean*mean, 0))
        # texture (buildings, foliage) is also erased by the cleaning, but leaves differences everywhere;
        # targets leave them only in a few isolated spots
        diff = (cv2.absdiff(raw, small) > self.min_contrast).astype(np.float32)
        texture = cv2.blur(diff, (31, 31)) > 0.3                  # window ≫ largest target at 1/4 scale
        sky = ((std < self.sky_std) & ~texture).astype(np.uint8)
        sky = cv2.erode(sky, np.ones((3, 3), np.uint8))           # keep away from sky/building edges
        return cv2.resize(sky, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)

    def detect_boxes(self, frame):
        import cv2
        g = cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_RGB2GRAY)
        g = cv2.GaussianBlur(g, (3, 3), 0)
        sky = self.sky_mask(g)
        if not sky.any():
            return []
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (2*self.max_size+1, 2*self.max_size+1))
        out, polarity = [], {}
        # dark and bright targets separately: residue of one polarity around a strong target of the
        # other polarity must not merge with it into one oversized component
        for op in (cv2.MORPH_BLACKHAT, cv2.MORPH_TOPHAT):
            res = cv2.morphologyEx(g, op, kern)
            vals = res[sky][::97].astype(np.float32)             # sample of the sky residual
            med = float(np.median(vals)) if len(vals) else 0.0
            sigma = 1.4826*float(np.median(np.abs(vals-med))) if len(vals) else 0.0
            thr = max(self.min_contrast, med+self.k*sigma)       # residual is not zero-centred
            n, _, stats, _ = cv2.connectedComponentsWithStats(((res > thr) & sky).astype(np.uint8), connectivity=8)
            # hysteresis size check: a blob that belongs to a larger structure at half the threshold
            # (cloud crest, haze band) is a fragment of that structure, not a target
            _, low_lab, low_stats, _ = cv2.connectedComponentsWithStats((res > 0.5*thr).astype(np.uint8), connectivity=8)
            for i in range(1, n):
                x, y, w, h, area = stats[i]
                if not (self.min_size <= max(w, h) <= self.max_size):
                    continue
                lab = low_lab[y+h//2, x+w//2]
                if lab and max(low_stats[lab][2], low_stats[lab][3]) > 2*self.max_size:
                    continue
                peak = float(res[y:y+h, x:x+w].max())
                box = Box(float(x), float(y), float(x+w), float(y+h), 'unknown', min(0.99, 0.4+0.3*(peak/thr-1)))
                out.append(box)
                polarity[id(box)] = op
        # morphology ringing: a weaker opposite-polarity blob right next to a strong target is an artefact
        keep = [b for b in out if not any(polarity[id(o)] != polarity[id(b)] and o.score > b.score
                                          and _gap(o, b) < self.max_size for o in out)]
        return [b for b in nms(keep, 0.1) if not any(o is not b and o.score > b.score and _contains(o, b) for o in keep)]


# COCO category ids (torchvision numbering) → provisional labels
COCO_MAP = {16: 'bird', 38: 'balloon', 5: 'drone'}       # bird, kite, airplane


class TorchvisionDetector(Detector):
    """COCO-pretrained torchvision model (weights download on first use)."""

    def __init__(self, arch: str = 'fasterrcnn_mobilenet_v3_large_fpn', min_confidence: float = 0.4, device: str | None = None):
        import torch
        import torchvision
        self.torch = torch
        self.device = device or ('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
        builder = getattr(torchvision.models.detection, arch)
        self.model = builder(weights='DEFAULT', box_score_thresh=min(0.05, min_confidence)).eval().to(self.device)
        self.min_confidence = min_confidence

    def detect_boxes(self, frame):
        x = self.torch.from_numpy(np.ascontiguousarray(frame)).permute(2, 0, 1).float().div(255).to(self.device)
        with self.torch.no_grad():
            r = self.model([x])[0]
        out = []
        for (x1, y1, x2, y2), lab, s in zip(r['boxes'].cpu().numpy(), r['labels'].cpu().numpy(), r['scores'].cpu().numpy()):
            if int(lab) in COCO_MAP:
                out.append(Box(float(x1), float(y1), float(x2), float(y2), COCO_MAP[int(lab)], float(s)))
        return out


def load_detector(name: str = 'skyblob', tile: int | None = None, **kw) -> Detector:
    if name == 'skyblob':
        det = SkyBlobDetector(**{k: v for k, v in kw.items() if k in ('max_size', 'min_size', 'k', 'min_contrast', 'sky_std', 'min_confidence')})
        return det                                            # works at full resolution already; no tiling
    if name == 'torchvision':
        det = TorchvisionDetector(**kw)
    else:
        raise ValueError(f'unknown detector {name!r}')
    return TiledDetector(det, tile=tile) if tile else det
