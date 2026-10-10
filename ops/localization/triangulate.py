"""Bearing rays from two or more domes → target positions (weighted least squares).

Rays from the same time window are paired greedily: same label, different domes, wide enough
crossing angle, and a closest-approach gap within the combined angular uncertainty. Other rays
that pass close to a fix join it. Rays left unpaired stay bearing-only (direction known,
range unknown) and are returned separately for display.
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ops.core.schemas import Detection, Measurement
from ops.perception.bearing import bearing_to_ray

MIN_ANGLE = np.radians(5)
MAX_RANGE = 5000.0
GATE_K = 3.0
GATE_FLOOR = 5.0


@dataclass
class Ray:
    det: Detection
    p: np.ndarray
    d: np.ndarray
    sigma: float

    @classmethod
    def of(cls, det):
        az, el = det.measurement.z
        return cls(det, np.asarray(det.node_pos, float), bearing_to_ray(az, el), float(np.sqrt(det.measurement.R[1][1])))


@dataclass
class Fix:
    t: float
    pos: np.ndarray
    cov: np.ndarray
    rays: list
    residual: float

    def detection(self) -> Detection:
        nodes = sorted({r.det.node_id for r in self.rays})
        labels = [r.det.label for r in self.rays if r.det.label]
        conf = [r.det.confidence for r in self.rays if r.det.confidence is not None]
        return Detection(t=self.t, node_id='+'.join(nodes), node_pos=tuple(self.rays[0].p), source='camera',
                         measurement=Measurement(kind='position', z=self.pos.tolist(), R=self.cov.tolist()),
                         label=max(set(labels), key=labels.count) if labels else None,
                         confidence=float(np.mean(conf)) if conf else None)


def group(bearings, window_s: float = 0.5):
    """Bucket bearing detections by time window → {window_start: [Detection]}."""
    out = defaultdict(list)
    for b in bearings:
        out[np.floor(b.t/window_s)*window_s].append(b)
    return dict(out)


def _closest(a: Ray, b: Ray):
    w = a.p-b.p
    dd = a.d@b.d
    den = 1-dd*dd
    if den < 1e-9:
        return None
    s = (dd*(b.d@w)-(a.d@w))/den
    t = ((b.d@w)-dd*(a.d@w))/den
    if s <= 0 or t <= 0 or s > MAX_RANGE or t > MAX_RANGE:
        return None
    gap = np.linalg.norm((a.p+s*a.d)-(b.p+t*b.d))
    return gap, s, t


def intersect(rays, iters: int = 3):
    """Weighted least-squares point closest to all rays → (pos, cov, residual) or None if ill-conditioned."""
    x = None
    for _ in range(iters):
        A, b = np.zeros((3, 3)), np.zeros(3)
        for r in rays:
            rng = max(1.0, (x-r.p)@r.d) if x is not None else 1000.0
            w = 1/(r.sigma*rng)**2
            M = np.eye(3)-np.outer(r.d, r.d)
            A += w*M
            b += w*M@r.p
        if np.linalg.cond(A) > 1e8:
            return None
        x = np.linalg.solve(A, b)
    cov = np.linalg.inv(A)
    res = np.sqrt(np.mean([(np.linalg.norm((np.eye(3)-np.outer(r.d, r.d))@(x-r.p))/(r.sigma*max(1.0, (x-r.p)@r.d)))**2 for r in rays]))
    return x, cov, float(res)


def _crossing_ok(a: Ray, b: Ray):
    return np.arccos(np.clip(abs(a.d@b.d), -1, 1)) >= MIN_ANGLE


def triangulate(bearings):
    """Bearing detections from one time window → (fixes, bearing_only_detections)."""
    rays = [Ray.of(b) for b in bearings]
    pairs = []
    for i in range(len(rays)):
        for j in range(i+1, len(rays)):
            a, b = rays[i], rays[j]
            if a.det.node_id == b.det.node_id or (a.det.label and b.det.label and a.det.label != b.det.label):
                continue
            if not _crossing_ok(a, b):
                continue
            c = _closest(a, b)
            if c is None:
                continue
            gap, s, t = c
            gate = GATE_K*np.hypot(a.sigma*s, b.sigma*t)+GATE_FLOOR
            if gap <= gate:
                pairs.append((gap/gate, i, j))
    used, fixes = set(), []
    t0 = min((b.t for b in bearings), default=0.0)
    for _, i, j in sorted(pairs):
        if i in used or j in used:
            continue
        group_ = [rays[i], rays[j]]
        r = intersect(group_)
        if r is None:
            continue
        x = r[0]
        nodes = {rays[i].det.node_id, rays[j].det.node_id}
        extra = []
        for k, rk in enumerate(rays):
            if k in used or k in (i, j) or rk.det.node_id in nodes:
                continue
            if rays[i].det.label and rk.det.label and rk.det.label != rays[i].det.label:
                continue
            rng = (x-rk.p)@rk.d
            if rng <= 0:
                continue
            dist = np.linalg.norm((np.eye(3)-np.outer(rk.d, rk.d))@(x-rk.p))
            if dist <= GATE_K*rk.sigma*rng+GATE_FLOOR:
                group_.append(rk); nodes.add(rk.det.node_id); extra.append(k)
        r = intersect(group_)
        if r is None:
            continue
        used.update((i, j, *extra))
        fixes.append(Fix(t0, r[0], r[1], group_, r[2]))
    bearing_only = [rays[k].det for k in range(len(rays)) if k not in used]
    return fixes, bearing_only
