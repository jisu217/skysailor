"""⑤ Identification from three cues. See ops/docs/DESIGN.md §5.5.

1. Camera label  — the track's averaged detector output (Track.image_label).
2. Motion        — horizontal airspeed v_air = v_track − w, tested against "moves with the wind":
                   T = v_airᵀ (P_v + P_w)⁻¹ v_air  ~ χ²(2) for a balloon. T is averaged over a
                   window; straight vs. erratic heading separates drones from birds.
3. Remote ID     — a broadcasting aircraft is a drone; the permit list says whether it is allowed.

Cues are combined as independent likelihoods (naive Bayes, uniform prior). 'unknown' keeps the
mass the available cues cannot claim. Disagreeing camera and motion cues raise `check`.
"""
from collections import deque

import numpy as np

from ops.core.schemas import ClassProbs

CLASSES = ('drone', 'balloon', 'bird')
KO = dict(drone='드론', balloon='풍선', bird='조류', unknown='미상')
CHI2_2DOF_95 = 5.991
MOTION_BALLOON = np.array([.10, .80, .10])
MOTION_STRAIGHT = np.array([.70, .05, .25])
MOTION_ERRATIC = np.array([.30, .05, .65])
RID = np.array([.97, .015, .015])
UNKNOWN_BY_CUES = {0: 1.0, 1: .35, 2: .12, 3: .05}


def airspeed_statistic(track, wind):
    """→ (horizontal v_air, T)."""
    v = np.asarray(track.vel[:2])-np.asarray(wind.w[:2])
    S = np.asarray(track.P)[3:5, 3:5]+np.asarray(wind.P)[:2, :2]
    return v, float(v@np.linalg.solve(S, v))


def heading_change(history, min_step: float = 2.0):
    """Mean absolute heading change (rad) between successive history segments, or None if too short."""
    if len(history) < 4:
        return None
    seg = np.diff(np.asarray(history, float)[:, :2], axis=0)
    seg = seg[np.linalg.norm(seg, axis=1) > min_step]
    if len(seg) < 3:
        return None
    h = np.arctan2(seg[:, 1], seg[:, 0])
    return float(np.mean(np.abs(np.angle(np.exp(1j*np.diff(h))))))


class WindowClassifier:
    def __init__(self, window_s: float = 5.0, turn_erratic: float = 0.35):
        self.window_s, self.turn_erratic = window_s, turn_erratic
        self.hist = {}

    def update(self, track, wind, permits=frozenset()):
        """→ Track copy with classes, permitted, class_basis and check filled in."""
        h = self.hist.setdefault(track.track_id, deque())
        v, T = airspeed_statistic(track, wind)
        h.append((track.t, T, float(np.linalg.norm(v))))
        while h and track.t-h[0][0] > self.window_s:
            h.popleft()
        cues, basis = [], []
        image_top = motion_top = None

        if track.image_label is not None:
            img = np.array([track.image_label.drone, track.image_label.balloon, track.image_label.bird])
            if img.sum() > 0:
                img = .1+.8*img/img.sum()                         # keep some doubt in the detector
                cues.append(img)
                image_top = CLASSES[int(np.argmax(img))]
                basis.append(f'영상: {KO[image_top]} {img.max()/img.sum():.0%}')

        if track.t-h[0][0] >= self.window_s*.8:
            T_mean = float(np.mean([x[1] for x in h]))
            air = float(np.mean([x[2] for x in h]))
            if T_mean < CHI2_2DOF_95:
                cues.append(MOTION_BALLOON); motion_top = 'balloon'
                basis.append(f'움직임: 바람을 따라 흐름 (대기 기준 속도 {air:.1f} m/s)')
            else:
                turn = heading_change(track.history)
                erratic = turn is not None and turn > self.turn_erratic
                cues.append(MOTION_ERRATIC if erratic else MOTION_STRAIGHT)
                motion_top = 'bird' if erratic else 'drone'
                basis.append(f'움직임: 스스로 이동 (대기 기준 속도 {air:.1f} m/s, {"방향 불규칙" if erratic else "직진"})')
        else:
            basis.append('움직임: 판정 대기')

        permitted = None
        if track.rid is not None:
            cues.append(RID)
            permitted = track.rid.uas_id in permits
            basis.append(f'Remote ID {track.rid.uas_id} · {"허가 목록 있음" if permitted else "허가 목록 없음"}')
        else:
            basis.append('Remote ID 없음')

        p = np.ones(3)
        for c in cues:
            p = p*c
        p = p/p.sum()
        u = UNKNOWN_BY_CUES[min(len(cues), 3)]
        p = (1-u)*p
        check = image_top is not None and motion_top is not None and image_top != motion_top
        if check:
            basis.append('영상과 움직임 판단이 다름 → 확인 필요')
        classes = ClassProbs(drone=float(p[0]), balloon=float(p[1]), bird=float(p[2]), unknown=float(u))
        return track.model_copy(update=dict(classes=classes, permitted=permitted, class_basis=basis, check=check))

    def forget(self, live_ids):
        self.hist = {k: v for k, v in self.hist.items() if k in live_ids}
