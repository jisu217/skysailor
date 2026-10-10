"""Static reference data used by ⑤ identification and ⑥ threat: protected zones, population, permits.

Real data (facility list, census grid, flight permits) replaces the virtual values later; the
interfaces stay the same.
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Zone:
    id: str
    name: str
    center: tuple[float, float]       # ENU east, north (m)
    radius: float                     # m
    weight: float                     # importance 0–1
    kind: str = 'capital'             # capital | military | airport | power | residential (matches case zone_type)


@dataclass
class Population:
    """Relative population density 0–1 as a sum of Gaussian hotspots (stand-in for a census grid)."""
    hotspots: list = field(default_factory=list)   # (east, north, sigma_m, amplitude)

    def density(self, e: float, n: float) -> float:
        v = sum(a*np.exp(-((e-x)**2+(n-y)**2)/(2*s*s)) for x, y, s, a in self.hotspots)
        return float(np.clip(v, 0, 1))


@dataclass
class Reference:
    zones: list = field(default_factory=list)
    population: Population = field(default_factory=Population)
    permits: set = field(default_factory=set)      # permitted Remote ID uas_id values
