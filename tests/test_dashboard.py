import numpy as np
from fastapi.testclient import TestClient
from dashboard import app, Experiment, experiment, slots
from clover import run

client = TestClient(app)


def test_health_and_initial_geometry():
    assert client.get('/api/health').json()['status'] == 'ok'
    data = client.get('/api/initial').json()
    assert len(data['geometry']) == len(data['frame']['position']) == 26
    assert len(data['frame']['tips']) == 4
    assert data['frame']['height'] == 3


def test_dashboard_trajectory_matches_original_engine():
    result = experiment(Experiment())
    for mode in ('pd','off'):
        trajectory = run(mode=mode)
        actual = result['runs'][mode]
        assert abs(actual['summary']['duration']-trajectory[-1,0]) < 1e-9
        assert abs(actual['summary']['rms_tilt']-np.sqrt(np.mean(trajectory[:,2]**2))) < 1e-9
        assert abs(actual['frames'][-1]['height']-trajectory[-1,1]) < 1e-9
        assert actual['frames'][0]['t'] == 0
        assert actual['summary']['termination'] == 'ground'


def test_invalid_and_busy_requests():
    assert client.post('/api/simulate',json={'height':-1}).status_code == 422
    assert client.post('/api/simulate',json={'kp':2}).status_code == 422
    assert client.post('/api/simulate',json={'unknown':1}).status_code == 422
    slots.acquire()
    slots.acquire()
    try:
        assert client.post('/api/simulate',json={}).status_code == 503
    finally:
        slots.release()
        slots.release()


def test_short_run_has_final_frame_and_timeout():
    response=client.post('/api/simulate',json={'seconds':.105,'mode':'pd'})
    assert response.status_code == 200
    data=response.json()['runs']['pd']
    assert data['frames'][-1]['t'] == .105
    assert data['summary']['termination'] == 'timeout'


def test_aero_visualization_uses_physics_and_vacuum():
    data = client.post('/api/simulate',json={'seconds':.1,'mode':'pd','air_density':0}).json()
    assert len(data['geometry']) == 26
    assert len([g for g in data['geometry'] if 'polygon' in g]) == 24
    frame = data['runs']['pd']['frames'][-1]
    assert len(frame['aero_force']) == 24
    assert np.allclose(frame['aero_total'],0)
    assert np.allclose(frame['loading'],0)
    assert np.allclose(frame['airflow'],0)
    assert frame['air_present'] is False
    assert np.allclose(frame['gravity'],[0,0,-.0082*9.81])
    assert frame['height'] < 3


def test_seeded_gusts_are_bounded_smooth_and_reproducible():
    import numpy as np
    from dashboard import WindProfile, Experiment
    p=Experiment(wind_mode='gust',wind_x=.2,wind_y=-.1,wind_seed=7)
    a,b=WindProfile(p),WindProfile(p)
    samples=np.array([a.at(t) for t in np.linspace(0,5,501)])
    assert np.max(np.linalg.norm(samples-[.2,-.1,0],axis=1)) <= p.gust_speed+1e-12
    np.testing.assert_array_equal(samples,[b.at(t) for t in np.linspace(0,5,501)])
    assert np.max(np.abs(samples-[WindProfile(p.model_copy(update={'wind_seed':8})).at(t) for t in np.linspace(0,5,501)]))>.01
    np.testing.assert_allclose(a.at(2),WindProfile(p.model_copy(update={'seconds':10})).at(2))
    assert np.linalg.norm(a.at(.8-1e-6)-a.at(.8+1e-6))<1e-8
    constant=WindProfile(p.model_copy(update={'wind_mode':'constant'}))
    np.testing.assert_allclose(constant.at(2),[.2,-.1,0])


def test_both_controllers_see_identical_wind_at_each_time():
    import numpy as np
    from dashboard import Experiment,experiment,WindProfile
    p=Experiment(variant='B',b_controller='optimized',wind_mode='gust',wind_seed=3,seconds=.2)
    r=experiment(p);a=r['runs']['off']['frames'];b=r['runs']['pd']['frames'];wind=WindProfile(p)
    for fa,fb in zip(a,b):
        assert fa['t']==fb['t']
        np.testing.assert_array_equal(fa['wind'],fb['wind'])
        np.testing.assert_allclose(fa['wind'],wind.at(fa['t']),atol=1e-12)


def test_measured_replay_preserves_components_timing_and_ignores_synthetic_settings():
    import numpy as np
    import pytest
    from dashboard import WindProfile,Experiment,measured_wind
    p=Experiment(wind_mode='measured',wind_clip='up',seconds=10,wind_x=3,gust_speed=3,wind_seed=99)
    w=WindProfile(p);clip=measured_wind()['clips']['up']
    np.testing.assert_allclose(w.at(0),clip['velocity_m_s'][0])
    np.testing.assert_allclose(w.at(10),clip['velocity_m_s'][-1])
    t=.5*(clip['time_s'][0]+clip['time_s'][1])
    np.testing.assert_allclose(w.at(t),np.mean(clip['velocity_m_s'][:2],axis=0))
    np.testing.assert_allclose(w.at(1),WindProfile(p.model_copy(update={'seconds':8,'wind_seed':0,'wind_x':0})).at(1))
    assert np.ptp(np.array(clip['velocity_m_s'])[:,2])>0
    with pytest.raises(ValueError):w.at(10.01)
    for c in measured_wind()['clips'].values():
        assert np.max(np.diff(c['time_s']))<=.200001
        assert np.all(np.isfinite(c['velocity_m_s']))


def test_measured_vertical_wind_and_air_relative_descent_are_reported():
    import numpy as np
    import pytest
    from dashboard import Experiment,experiment
    r=experiment(Experiment(variant='B',b_controller='optimized',wind_mode='measured',seconds=.1))
    assert r['wind_source']['height_m']==50
    for run in r['runs'].values():
        for f in run['frames']:
            assert f['air_descent_speed']==pytest.approx(f['speed']+f['wind'][2])
        assert run['summary']['mean_air_descent_speed']>run['summary']['mean_descent_speed']
