"""WGS84 <-> local ENU (east, north, up) about a fixed reference point."""
import numpy as np

A = 6378137.0
E2 = 6.69437999014e-3


def _ecef(lat, lon, h):
    lat, lon = np.radians(lat), np.radians(lon)
    n = A/np.sqrt(1-E2*np.sin(lat)**2)
    return np.array([(n+h)*np.cos(lat)*np.cos(lon), (n+h)*np.cos(lat)*np.sin(lon), (n*(1-E2)+h)*np.sin(lat)])


class ENU:
    def __init__(self, lat0: float, lon0: float, h0: float = 0.0):
        self.ref = (lat0, lon0, h0)
        self.origin = _ecef(lat0, lon0, h0)
        la, lo = np.radians(lat0), np.radians(lon0)
        self.R = np.array([[-np.sin(lo), np.cos(lo), 0],
                           [-np.sin(la)*np.cos(lo), -np.sin(la)*np.sin(lo), np.cos(la)],
                           [np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)]])

    def to_enu(self, lat: float, lon: float, h: float) -> np.ndarray:
        return self.R@(_ecef(lat, lon, h)-self.origin)

    def to_geo(self, enu) -> tuple[float, float, float]:
        x, y, z = self.origin+self.R.T@np.asarray(enu, float)
        lon = np.arctan2(y, x)
        p = np.hypot(x, y)
        lat = np.arctan2(z, p*(1-E2))
        for _ in range(6):
            n = A/np.sqrt(1-E2*np.sin(lat)**2)
            h = p/np.cos(lat)-n
            lat = np.arctan2(z, p*(1-E2*n/(n+h)))
        return float(np.degrees(lat)), float(np.degrees(lon)), float(h)
