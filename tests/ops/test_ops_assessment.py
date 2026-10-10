import numpy as np

from ops.assessment import footprint
from ops.assessment.classify import WindowClassifier
from ops.assessment.threat import cpa_tti, evaluate
from ops.core.reference import Population, Reference, Zone
from ops.core.schemas import ClassProbs, RemoteID, Track
from ops.nodes.wind import estimate

WIND = estimate(0, (4.0, 1.0, 0.0), sigma=0.5)
REF = Reference(zones=[Zone('Z1', 'zone', (0.0, 0.0), 150.0, 1.0)],
                population=Population([(0.0, 0.0, 300.0, 1.0)]), permits={'OK-1'})


def _track(t, pos, vel, vel_sigma=0.3, image=None, rid=None, history=None, classes=None):
    P = np.diag([4, 4, 4, vel_sigma**2, vel_sigma**2, vel_sigma**2]).tolist()
    return Track(track_id='T', status='confirmed', t=t, pos=tuple(pos), vel=tuple(vel), P=P, rid=rid,
                 image_label=image, history=history or [], classes=classes or ClassProbs())


def _run(vel, image=None, rid=None, turn=0.0, steps=14, permits=frozenset()):
    clf, out, pos, hd = WindowClassifier(), None, np.array([-800., 0., 300.]), 0.0
    hist = []
    for k in range(steps):
        t = k*0.5
        hd += turn*(1 if k % 2 else -1)
        v = np.array(vel) if not turn else np.array([np.linalg.norm(vel)*np.cos(hd), np.linalg.norm(vel)*np.sin(hd), 0])
        pos = pos+v*0.5
        hist.append(tuple(pos))
        out = clf.update(_track(t, pos, v, image=image, rid=rid, history=list(hist)), WIND, permits)
    return out


def _top(tr):
    return max(('drone', 'balloon', 'bird', 'unknown'), key=lambda k: getattr(tr.classes, k))


def test_balloon_drifting_with_wind_is_balloon():
    tr = _run((4.0, 1.0, -0.5))
    assert _top(tr) == 'balloon' and tr.classes.balloon > .5      # one cue (motion): 35 % stays unknown


def test_drone_against_wind_is_drone():
    tr = _run((-10.0, -2.0, 0.0))
    assert _top(tr) == 'drone'


def test_motion_waits_for_full_window():
    tr = _run((-10.0, -2.0, 0.0), steps=3)
    assert tr.classes.unknown == 1.0 and '움직임: 판정 대기' in tr.class_basis


def test_image_and_motion_disagree_marks_check():
    tr = _run((4.0, 1.0, 0.0), image=ClassProbs(drone=1, balloon=0, bird=0, unknown=0))
    assert tr.check and any('확인 필요' in b for b in tr.class_basis)


def test_cpa_tti_straight_line():
    z = Zone('Z', 'z', (0.0, 0.0), 100.0, 1.0)
    cpa, tti = cpa_tti((-1000.0, 50.0, 0), (10.0, 0.0, 0), z)
    assert np.isclose(cpa, 50.0) and np.isclose(tti, (1000-np.sqrt(100**2-50**2))/10)
    cpa, tti = cpa_tti((-1000.0, 300.0, 0), (10.0, 0.0, 0), z)
    assert np.isclose(cpa, 300.0) and np.isinf(tti)
    assert cpa_tti((10.0, 0.0, 0), (0.0, 0.0, 0), z) == (10.0, 0.0)


def test_score_does_not_drop_when_closer():
    drone = ClassProbs(drone=.9, balloon=.03, bird=.02, unknown=.05)
    scores = [evaluate(_track(0, (-d, 0, 100), (12, 0, 0), classes=drone), WIND, REF).score for d in (2000, 1500, 1000, 600, 300, 160)]
    assert all(b >= a for a, b in zip(scores, scores[1:])) and scores[-1] > scores[0]


def test_new_track_heading_not_trusted():
    drone = ClassProbs(drone=.9, balloon=.03, bird=.02, unknown=.05)
    th = evaluate(_track(0, (-1000, 0, 100), (12, 0, 0), vel_sigma=10, classes=drone), WIND, REF)
    assert th.tti_s is None and '속도 추정 중' in th.factors[2].value


def test_permitted_remote_id_lowers_p_hostile():
    tr = _run((-10.0, 0.0, 0.0), rid=RemoteID(uas_id='OK-1', lat=0, lon=0, alt=100), permits={'OK-1'})
    other = _run((-10.0, 0.0, 0.0), rid=RemoteID(uas_id='XX-9', lat=0, lon=0, alt=100), permits={'OK-1'})
    assert tr.permitted and not other.permitted
    a, b = evaluate(tr, WIND, REF), evaluate(other, WIND, REF)
    assert a.p_hostile < .15 < .3 < b.p_hostile and a.score < b.score


def test_balloon_footprint_follows_wind():
    tr = _track(0, (100, 200, 500), (4, 1, -1.0), vel_sigma=0.1)
    (e, n), r, fall = footprint.predict(tr, WIND)
    assert np.isclose(fall, 500) and np.allclose((e, n), (100+4*500, 200+1*500)) and r > footprint.MIN_RADIUS
