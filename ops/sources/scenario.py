"""Seeded demo scenarios with ground truth.

Emits what real hardware would send — NodeStatus (IMU attitude with noise and a sync offset),
CameraDetection (pixel boxes from the true attitude), Remote ID for cooperative drones — plus
truth for checking. Detection probability follows apparent size in pixels, so detection range
comes out of the camera spec and target size rather than a fixed radius.
"""
from dataclasses import dataclass, field

import numpy as np

from ops.core.geo import ENU
from ops.core.reference import Population, Reference, Zone
from ops.core.schemas import CameraDetection, NodeStatus, RemoteID
from ops.nodes.wind import estimate as wind_estimate
from ops.perception.bearing import Camera, project

REF = (37.55, 126.99, 0.0)           # virtual reference point (Seoul area)
SIZE = dict(drone=0.4, balloon=2.0, bird=0.3)
MIN_PX, FULL_PX = 4.0, 12.0          # apparent size where detection starts / is reliable
EXPOSURE_S = 1/500                   # shutter time; blur (px) = angular rate × exposure × fx
IMU_SIGMA = np.radians(0.5)
SYNC_S = 0.01


def ring_cameras(n: int = 4, pitches=(5.0, 38.0), **kw):
    """n cameras around the horizon per tier. With the default 60° × 34° lens, two tiers at
    5° and 38° cover elevations of about −12° to +55° all around (2n cameras per dome)."""
    return [Camera(mount_yaw_deg=360*i/n+45*k, mount_pitch_deg=p, **kw)
            for k, p in enumerate(pitches) for i in range(n)]


@dataclass
class Node:
    id: str
    pos: np.ndarray
    quality: float                   # 1 = steady, 0 = violent shake (stands in for controller performance)
    phase: float = 0.0

    def attitude(self, t):
        a = np.radians(1+24*(1-self.quality))
        roll = a*np.sin(1.3*t+self.phase)
        pitch = a*np.sin(0.9*t+2*self.phase)
        yaw = 0.2*np.sin(0.05*t+self.phase)+np.radians(20)*(1-self.quality)*np.sin(0.4*t)
        return np.array([roll, pitch, yaw])

    def rate(self, t, h=1e-3):
        return (self.attitude(t+h)-self.attitude(t-h))/(2*h)


@dataclass
class Target:
    id: str
    cls: str
    pos: np.ndarray
    t0: float = 0.0
    speed: float = 0.0
    goal: np.ndarray | None = None
    loiter: tuple | None = None      # (centre xyz, radius, angular speed)
    descent: float = 0.0
    uas_id: str | None = None
    size: float | None = None        # m; defaults to SIZE[cls]
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    hd: float = 0.0

    def step(self, t, dt, wind, rng):
        if self.cls == 'balloon':
            self.vel = np.array([wind[0], wind[1], -self.descent])
        elif self.loiter is not None:
            c, r, w = self.loiter
            nxt = np.array([c[0]+r*np.cos(w*(t+dt)), c[1]+r*np.sin(w*(t+dt)), c[2]])
            self.vel = (nxt-self.pos)/dt
        elif self.goal is not None:
            d = self.goal-self.pos
            n = np.linalg.norm(d)
            self.vel = d/n*self.speed if n > 1 else np.zeros(3)
        else:
            self.hd += rng.normal(0, .5)
            self.vel = np.array([self.speed*np.cos(self.hd)+.3*wind[0], self.speed*np.sin(self.hd)+.3*wind[1], rng.normal(0, .5)])
        self.pos = self.pos+self.vel*dt


@dataclass
class Scenario:
    name: str
    seed: int
    duration_s: float
    nodes: list
    targets: list
    cameras: list
    wind: np.ndarray
    reference: Reference = field(default_factory=Reference)
    enu: ENU = field(default_factory=lambda: ENU(*REF))


@dataclass
class Frame:
    t: float
    node_statuses: list
    camera_detections: list
    rid_reports: list                # (node_id, RemoteID)
    wind: object
    truth: list


def generate(name: str = 'mixed', seed: int = 0, quality: float = 0.95, cameras=None, spacing: float = 250.0) -> Scenario:
    """Presets: 'mixed' (2 balloons, 2 m fixed-wing, 0.4 m quadcopter, permitted drone, bird) around three domes.

    spacing: dome-to-dome distance (m). Small drones are only seen within a few hundred metres,
    so triangulating them needs domes close enough for two to see the same target.
    """
    if name != 'mixed':
        raise ValueError(f'unknown scenario {name!r}')
    h = spacing*np.sqrt(3)/2
    c = np.array([spacing/2, h/3, 0.0])                       # triangle centroid
    nodes = [Node('dome-1', np.array([0., 0., 120.]), quality, 0.0),
             Node('dome-2', np.array([spacing, 0., 120.]), quality, 1.1),
             Node('dome-3', np.array([spacing/2, h, 120.]), quality, 2.3)]
    wind = np.array([3.5, 1.0, 0.0])
    targets = [
        Target('B-01', 'balloon', c+[-400., -60., 420.], descent=0.6),
        Target('B-02', 'balloon', c+[-500., 120., 360.], t0=20, descent=0.5),
        Target('D-01', 'drone', c+[450., 380., 110.], t0=10, speed=12, goal=c+[-450., -330., 90.], size=2.0),  # ~2 m fixed-wing (2022 incursion class)
        Target('D-02', 'drone', c+[-300., 250., 70.], t0=30, speed=6, goal=c+[200., -150., 70.]),                 # 0.4 m quadcopter
        Target('R-01', 'drone', c+[120., 0., 80.], loiter=(c+[0., 0., 80.], 120., 0.06), uas_id='KR-UAS-24817'),
        Target('K-01', 'bird', c+[-40., 30., 100.], speed=6),
    ]
    reference = Reference(
        zones=[Zone('Z1', '정부청사 (가상)', tuple(c[:2]+[-420., -300.]), 150., 1.0, 'capital'),
               Zone('Z2', '변전소 (가상)', tuple(c[:2]+[420., -250.]), 100., .8, 'power')],
        population=Population([(*(c[:2]+[-250., -150.]), 250., 1.0), (*(c[:2]+[600., 300.]), 300., .7)]),
        permits={'KR-UAS-24817'})
    return Scenario(name, seed, 120.0, nodes, targets, cameras or ring_cameras(), wind, reference)


def replay(scenario: Scenario, dt: float = 0.5):
    """Yield Frame(t, node_statuses, camera_detections, rid_reports, wind, truth) in time order."""
    rng = np.random.default_rng(scenario.seed)
    t = 0.0
    while t <= scenario.duration_s+1e-9:
        statuses, dets, rids, truth = [], [], [], []
        for n in scenario.nodes:
            att = n.attitude(t+SYNC_S)+rng.normal(0, IMU_SIGMA, 3)
            statuses.append(NodeStatus(t=t, node_id=n.id, pos=tuple(n.pos), attitude=tuple(att), angular_rate=tuple(n.rate(t))))
        for tg in scenario.targets:
            if t < tg.t0:
                continue
            truth.append(dict(id=tg.id, cls=tg.cls, pos=tg.pos.copy(), vel=tg.vel.copy(), uas_id=tg.uas_id))
            for n in scenario.nodes:
                r = np.linalg.norm(tg.pos-n.pos)
                for ci, cam in enumerate(scenario.cameras):
                    uv = project(tg.pos, n.pos, n.attitude(t), cam)
                    if uv is None:
                        continue
                    px = (tg.size or SIZE[tg.cls])*cam.fx/r
                    blur = np.linalg.norm(n.rate(t))*EXPOSURE_S*cam.fx
                    px_eff = px*px/(px+blur)                    # smear spreads the target's contrast
                    p = np.clip((px_eff-MIN_PX)/(FULL_PX-MIN_PX), 0, 1)
                    if rng.random() > p:
                        continue
                    u, v = uv[0]+rng.normal(0, cam.pixel_sigma), uv[1]+rng.normal(0, cam.pixel_sigma)
                    label = tg.cls if rng.random() < .9 else rng.choice([c for c in SIZE if c != tg.cls])
                    conf = float(np.clip(.35+.6*min(px/30, 1)+rng.normal(0, .05), 0, 1))
                    dets.append(CameraDetection(t=t, node_id=n.id, camera_id=ci, bbox=(u-px/2, v-px/2, px, px),
                                                image_size=(cam.width, cam.height), label=label, confidence=conf))
            if tg.uas_id and abs(t-round(t)) < 1e-9:
                lat, lon, alt = scenario.enu.to_geo(tg.pos+rng.normal(0, 3, 3))
                rids.append((scenario.nodes[0].id, RemoteID(uas_id=tg.uas_id, lat=lat, lon=lon, alt=alt,
                                                            speed=float(np.linalg.norm(tg.vel)))))
            tg.step(t, dt, scenario.wind, rng)
        yield Frame(t, statuses, dets, rids, wind_estimate(t, scenario.wind), truth)
        t = round(t+dt, 9)
