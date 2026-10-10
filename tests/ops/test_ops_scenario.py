import numpy as np

from ops.service.pipeline import Pipeline
from ops.sources.scenario import generate, replay


def test_scenario_end_to_end_tracks_large_targets():
    sc = generate(quality=0.95, spacing=250, seed=0)
    sc.duration_s = 60
    pl = Pipeline(sc.cameras, sc.enu)
    held = {}
    for f in replay(sc):
        r = pl.step(f.t, f.node_statuses, f.camera_detections, f.rid_reports, f.wind)
        conf = [t for t in r.tracks if t.status == 'confirmed']
        for tr in f.truth:
            ok = any(np.linalg.norm(np.array(c.pos)-tr['pos']) < 50 for c in conf)
            held.setdefault(tr['id'], []).append(ok)
    assert np.mean(held['R-01']) > .9          # Remote ID drone
    assert np.mean(held['B-02']) > .8          # balloon seen by several domes


def test_scenario_identification_and_threat():
    sc = generate(quality=0.95, spacing=250, seed=0)
    pl = Pipeline(sc.cameras, sc.enu, sc.reference)
    tops, levels = {}, {}
    for f in replay(sc):
        r = pl.step(f.t, f.node_statuses, f.camera_detections, f.rid_reports, f.wind)
        th = {x.track_id: x for x in r.threats}
        for tr in f.truth:
            c = min((t for t in r.tracks if t.status == 'confirmed'), key=lambda t: np.linalg.norm(np.array(t.pos)-tr['pos']), default=None)
            if c is None or np.linalg.norm(np.array(c.pos)-tr['pos']) > 50:
                continue
            tops.setdefault(tr['id'], []).append(max(('drone', 'balloon', 'bird', 'unknown'), key=lambda k: getattr(c.classes, k)))
            levels.setdefault(tr['id'], []).append(th[c.track_id].level)
    # class-agnostic detector: each new track is 'unknown' until 5 s of motion → score decided frames only
    share = lambda xs, v: np.mean([x == v for x in xs if x != 'unknown'])
    assert share(tops['B-02'], 'balloon') > .9
    assert share(tops['D-01'], 'drone') > .9
    assert set(levels['R-01']) == {'LOW'}                       # permitted Remote ID drone
    assert {'HIGH', 'CRITICAL'} & set(levels['D-01'])           # hostile drone heading for the zone
