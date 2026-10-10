"""Wind estimate with uncertainty (WindEstimate.w, WindEstimate.P).

Phase 1: a known wind (scenario or data/wind/measured.json) with a fixed uncertainty.
Next: dome drift (an unpowered dome is a passive anemometer) fused with station data.
"""
import numpy as np

from ops.core.schemas import WindEstimate


def estimate(t: float, w, sigma: float = 0.8, source: str = 'sim') -> WindEstimate:
    P = (np.eye(3)*sigma**2).tolist()
    return WindEstimate(t=t, w=tuple(float(v) for v in w), P=P, source=source)
