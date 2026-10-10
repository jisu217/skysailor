"""Merge a camera-only track and a Remote ID track that are the same aircraft.

Two tracks are the same aircraft when their positions agree within the combined uncertainty
(Mahalanobis gate) and their velocities agree, for `need` consecutive steps. The camera track
is then folded into the Remote ID track (which keeps its uas_id); the target is cooperative
and checked against the permit list.
"""
import numpy as np

from ops.tracking.association import CHI2_3DOF


class Fuser:
    def __init__(self, gate_p: float = 0.99, vel_gate: float = 4.0, need: int = 3):
        self.gate, self.vel_gate, self.need = CHI2_3DOF[gate_p], vel_gate, need
        self.streak = {}

    def _same(self, a, b):
        dp = a.kf.x[:3]-b.kf.x[:3]
        S = a.kf.P[:3, :3]+b.kf.P[:3, :3]
        return dp@np.linalg.solve(S, dp) <= self.gate and np.linalg.norm(a.kf.x[3:]-b.kf.x[3:]) <= self.vel_gate

    def match(self, tracks):
        """→ list of (camera_track, rid_track) pairs to merge this step."""
        cams = [t for t in tracks if t.rid is None and t.status != 'lost']
        rids = [t for t in tracks if t.rid is not None and t.status != 'lost']
        seen, out = set(), []
        for c in cams:
            for r in rids:
                if not self._same(c, r):
                    continue
                key = (c.id, r.id)
                seen.add(key)
                self.streak[key] = self.streak.get(key, 0)+1
                if self.streak[key] >= self.need:
                    out.append((c, r))
                    break
        self.streak = {k: v for k, v in self.streak.items() if k in seen}
        return out
