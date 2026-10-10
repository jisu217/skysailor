import numpy as np

from ops.core.geo import ENU
from ops.core.schemas import Detection, Measurement, RemoteID
from ops.localization.triangulate import triangulate
from ops.perception.bearing import ray_to_bearing
from ops.tracking.manager import TrackManager

SIG = np.radians(0.3)


def _bearing(node, target, t=0.0, label='drone', node_id=None):
    az, el = ray_to_bearing(np.asarray(target, float)-np.asarray(node, float))
    return Detection(t=t, node_id=node_id or str(node), node_pos=tuple(node), source='camera', label=label, confidence=.9,
                     measurement=Measurement(kind='bearing', z=[az, el], R=[[SIG**2, 0], [0, SIG**2]]))


def _pos(t, p, sigma=5.0, rid=None, source='camera'):
    return Detection(t=t, node_id='x', node_pos=(0, 0, 0), source=source, rid=rid,
                     measurement=Measurement(kind='position', z=list(map(float, p)), R=(np.eye(3)*sigma**2).tolist()))


def test_enu_round_trip():
    enu = ENU(37.55, 126.99, 0)
    for p in ([0, 0, 0], [1200.5, -830.2, 410.0], [-5000, 7000, 50]):
        assert np.allclose(enu.to_enu(*enu.to_geo(p)), p, atol=1e-6)


def test_triangulate_two_domes():
    nodes = [(0, 0, 100), (300, 0, 100), (150, 260, 100)]
    target = np.array([180, 120, 150])
    fixes, single = triangulate([_bearing(n, target) for n in nodes])
    assert len(fixes) == 1 and not single
    assert np.linalg.norm(fixes[0].pos-target) < 1e-6
    assert len(fixes[0].rays) == 3


def test_triangulate_rejects_near_parallel_rays():
    fixes, single = triangulate([_bearing((0, 0, 100), (2000, 0, 100)), _bearing((0, 20, 100), (2000, 0, 100))])
    assert not fixes and len(single) == 2


def test_single_dome_stays_bearing_only():
    fixes, single = triangulate([_bearing((0, 0, 100), (300, 200, 150))])
    assert not fixes and len(single) == 1


def test_kalman_converges_on_straight_target():
    rng = np.random.default_rng(0)
    tm = TrackManager()
    for k in range(60):
        t = k*0.5
        tracks = tm.step(t, [_pos(t, np.array([100+10*t, 50-4*t, 120])+rng.normal(0, 5, 3))])
    (tr,) = [x for x in tracks if x.status == 'confirmed']
    P = np.array(tr.P)
    dv = np.array(tr.vel)-[10, -4, 0]
    dp = np.array(tr.pos)-[100+10*29.5, 50-4*29.5, 120]
    assert np.all(np.abs(dv) < 3*np.sqrt(np.diag(P)[3:]))      # within the filter's own 3σ
    assert np.all(np.abs(dp) < 3*np.sqrt(np.diag(P)[:3]))
    assert np.linalg.norm(dv) < 3


def test_two_crossing_targets_keep_ids():
    rng = np.random.default_rng(1)
    tm = TrackManager()
    ids_a, ids_b = set(), set()
    for k in range(80):
        t = k*0.5
        a, b = np.array([10*t, 0, 100]), np.array([400-10*t, 30, 100])
        tracks = tm.step(t, [_pos(t, a+rng.normal(0, 3, 3), 3), _pos(t, b+rng.normal(0, 3, 3), 3)])
        conf = [x for x in tracks if x.status == 'confirmed']
        if k > 5:
            ids_a.add(min(conf, key=lambda x: np.linalg.norm(np.array(x.pos)-a)).track_id)
            ids_b.add(min(conf, key=lambda x: np.linalg.norm(np.array(x.pos)-b)).track_id)
    assert len(ids_a) == 1 and len(ids_b) == 1 and ids_a != ids_b


def test_track_confirm_and_drop():
    tm = TrackManager(lost_after_s=2, drop_after_s=4)
    states = [tm.step(k*0.5, [_pos(k*0.5, [0, 0, 100])])[0].status for k in range(3)]
    assert states[0] == 'tentative' and states[-1] == 'confirmed'
    for k in range(3, 10):
        tracks = tm.step(k*0.5, [])
    assert tracks[0].status == 'lost'
    for k in range(10, 20):
        tracks = tm.step(k*0.5, [])
    assert tracks == []


def test_camera_track_fuses_with_remote_id():
    rid = lambda p: RemoteID(uas_id='KR-1', lat=0, lon=0, alt=float(p[2]))
    tm = TrackManager()
    for k in range(12):
        t = k*0.5
        p = np.array([5*t, 0, 80])
        tracks = tm.step(t, [_pos(t, p+[2, 0, 0]), _pos(t, p, rid=rid(p), source='remote_id')])
    live = [x for x in tracks if x.status != 'lost']
    assert len(live) == 1 and live[0].rid.uas_id == 'KR-1' and live[0].sources == ['camera', 'remote_id']
