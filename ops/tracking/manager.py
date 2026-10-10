"""Track lifecycle: tentative → confirmed (M of N hits) → lost (timeout) → dropped.

Per step: predict all tracks → Remote ID reports join the track with the same uas_id →
remaining position detections go through gated association → unassigned detections start
tentative tracks → camera and Remote ID tracks of the same aircraft are fused.
"""
from collections import Counter, deque
from dataclasses import dataclass, field

import numpy as np

from ops.core.schemas import ClassProbs, Track
from ops.tracking.association import associate
from ops.tracking.fusion import Fuser
from ops.tracking.kalman import KalmanCV

VEL_SIGMA0 = 30.0   # m/s, initial velocity uncertainty (covers fast drones)


@dataclass
class _Track:
    id: str
    kf: KalmanCV
    t: float
    first: float
    last: float
    hits: deque
    status: str = 'tentative'
    rid: object = None
    sources: set = field(default_factory=set)
    labels: Counter = field(default_factory=Counter)
    history: list = field(default_factory=list)
    z0: np.ndarray | None = None
    n_upd: int = 0

    def update(self, det):
        """Kalman update; the second measurement re-initialises velocity from two points."""
        z, R = np.asarray(det.measurement.z, float), np.asarray(det.measurement.R, float)
        dt = det.t-self.first
        if self.n_upd == 1 and dt > 0:
            self.kf.x = np.concatenate([z, (z-self.z0)/dt])
            self.kf.P = np.block([[R, R/dt], [R/dt, 2*R/dt**2]])
        else:
            self.kf.update(z, R)
        self.n_upd += 1
        self.absorb(det)

    def absorb(self, det):
        self.last = det.t
        self.sources.add(det.source)
        if det.rid is not None:
            self.rid = det.rid
        if det.label and det.label != 'unknown':          # class-agnostic detections carry no image cue
            self.labels[det.label] += det.confidence or 1.0

    def schema(self) -> Track:
        image = None
        if self.labels:
            tot = sum(self.labels.values())
            image = ClassProbs(drone=self.labels['drone']/tot, balloon=self.labels['balloon']/tot,
                               bird=self.labels['bird']/tot, unknown=0.0)
        return Track(track_id=self.id, status=self.status, t=self.t, pos=tuple(self.kf.x[:3]),
                     vel=tuple(self.kf.x[3:]), P=self.kf.P.tolist(), rid=self.rid,
                     sources=sorted(self.sources), image_label=image, history=self.history[-60:])


class TrackManager:
    def __init__(self, confirm_m: int = 3, confirm_n: int = 5, lost_after_s: float = 5.0,
                 drop_after_s: float = 30.0, q: float = 3.0):
        self.confirm_m, self.confirm_n = confirm_m, confirm_n
        self.lost_after_s, self.drop_after_s, self.q = lost_after_s, drop_after_s, q
        self.tracks: list[_Track] = []
        self.fuser = Fuser()
        self._n = 0

    def _new(self, det):
        self._n += 1
        R = np.asarray(det.measurement.R, float)
        P0 = np.block([[R, np.zeros((3, 3))], [np.zeros((3, 3)), np.eye(3)*VEL_SIGMA0**2]])
        x0 = np.concatenate([det.measurement.z, np.zeros(3)])
        tr = _Track(f'T-{self._n:03d}', KalmanCV(x0, P0, self.q), det.t, det.t, det.t, deque(maxlen=self.confirm_n))
        tr.absorb(det)
        tr.z0, tr.n_upd = np.asarray(det.measurement.z, float), 1
        tr.history.append(tuple(float(v) for v in tr.kf.x[:3]))
        self.tracks.append(tr)
        return tr

    def step(self, t: float, detections) -> list[Track]:
        """Position detections at time t (camera fixes and Remote ID reports) → current tracks."""
        live = [tr for tr in self.tracks if tr.status != 'lost']
        for tr in live:
            tr.kf.predict(t-tr.t)
            tr.t = t
        hit = set()
        rest = []
        by_rid = {tr.rid.uas_id: tr for tr in live if tr.rid is not None}
        for d in detections:
            tr = by_rid.get(d.rid.uas_id) if d.rid is not None else None
            if tr is not None and tr.id not in hit:
                tr.update(d); hit.add(tr.id)
            else:
                rest.append(d)
        pairs, _, new = associate(live, rest)          # a Remote ID track may also take a camera fix
        for tr, d in pairs:
            tr.update(d); hit.add(tr.id)
        for d in new:
            hit.add(self._new(d).id)
        for tr in self.tracks:
            if tr.status == 'lost':
                continue
            tr.hits.append(tr.id in hit)
            if tr.status == 'tentative' and sum(tr.hits) >= self.confirm_m:
                tr.status = 'confirmed'
            elif tr.status == 'tentative' and len(tr.hits) == self.confirm_n:
                tr.status = 'lost'; tr.last = -1e9      # never confirmed: drop now
            if t-tr.last > self.lost_after_s:
                tr.status = 'lost'
            if tr.id in hit:
                tr.history.append(tuple(float(v) for v in tr.kf.x[:3]))
        for cam, rid in self.fuser.match(self.tracks):
            rid.sources |= cam.sources
            rid.labels.update(cam.labels)
            if cam.status == 'confirmed':
                rid.status = 'confirmed'
            self.tracks.remove(cam)
        self.tracks = [tr for tr in self.tracks if not (tr.status == 'lost' and t-tr.last > self.drop_after_s)]
        return [tr.schema() for tr in self.tracks]
