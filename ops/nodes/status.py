"""Node observation quality from telemetry.

stability ← recent tilt and angular rate (camera shake); coverage_m ← reference detection
range × stability. The dome attitude itself is controlled on board (hanging.py / Arena agents);
ops only reads it.
"""
from collections import deque

import numpy as np

TILT_SCALE = np.radians(15)      # tilt at which stability falls to e^-1
RATE_SCALE = np.radians(30)      # angular rate at which stability falls to e^-1


class NodeMonitor:
    def __init__(self, ref_range_m: float, window: int = 20):
        self.ref_range_m = ref_range_m
        self.hist = {}
        self.window = window

    def evaluate(self, status):
        """→ NodeStatus copy with stability (0–1) and coverage_m filled in."""
        h = self.hist.setdefault(status.node_id, deque(maxlen=self.window))
        roll, pitch, _ = status.attitude
        h.append((np.hypot(roll, pitch), float(np.linalg.norm(status.angular_rate))))
        tilt_rms = float(np.sqrt(np.mean([a*a for a, _ in h])))
        rate_rms = float(np.sqrt(np.mean([r*r for _, r in h])))
        stability = float(np.exp(-(tilt_rms/TILT_SCALE)**2-(rate_rms/RATE_SCALE)**2))
        if not status.camera_ok:
            stability = 0.0
        return status.model_copy(update=dict(stability=stability, coverage_m=self.ref_range_m*stability))
