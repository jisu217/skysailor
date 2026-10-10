"""Balloon landing-area estimate for collateral damage.

fall_time = altitude / descent rate (measured from the track once its vertical speed is reliable);
impact ≈ position + wind · fall_time; radius grows with wind uncertainty × fall_time plus
the current position uncertainty. Population inside feeds Consequence.
"""
import numpy as np

DEFAULT_DESCENT = 1.0     # m/s when the track is not visibly descending
MIN_RADIUS = 30.0
VZ_SIGMA_MAX = 0.5        # m/s; trust the measured descent only below this uncertainty


def predict(track, wind, ground: float = 0.0):
    """→ (impact (e, n), radius_m, fall_time_s)."""
    alt = max(0.0, track.pos[2]-ground)
    vz_known = float(np.sqrt(np.asarray(track.P)[5][5])) <= VZ_SIGMA_MAX
    descent = -track.vel[2] if vz_known and track.vel[2] < -0.2 else DEFAULT_DESCENT
    fall = alt/descent
    w = np.asarray(wind.w[:2])
    impact = np.asarray(track.pos[:2])+w*fall
    sw = float(np.sqrt(np.trace(np.asarray(wind.P)[:2, :2])/2))
    sp = float(np.sqrt(np.trace(np.asarray(track.P)[:2, :2])/2))
    return (float(impact[0]), float(impact[1])), MIN_RADIUS+sw*fall+sp, float(fall)
