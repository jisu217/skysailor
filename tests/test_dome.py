import numpy as np
import mujoco
import pytest
from dome import DomeSim, RADIUS, DOME_MASS, PAYLOAD_MASS
from clover import Config
from dashboard import Experiment, experiment, app
from fastapi.testclient import TestClient


def test_winch_rates_and_internal_forces_preserve_ballistics():
    sim=DomeSim(Config(air_density=0),target_xy=(.025,.01));sim.reset(0)
    before=sim.system_com();previous=sim.spool.copy()
    for _ in range(300):
        sim.step(sim.pd_action())
        assert np.all(np.abs(sim.spool-previous)<=.04*sim.c.dt+1e-12)
        assert np.all(np.abs(sim.winch_rates)<=.04+1e-12)
        assert np.all(sim.tensions>=0)
        previous=sim.spool.copy()
    delta=sim.system_com()-before
    assert np.linalg.norm(delta[:2])<1e-7
    assert delta[2] == pytest.approx(-.5*9.81*sim.data.time**2,abs=.002)
    assert sim.model.nv==12 and sim.model.nu==0  # Two independent free rigid bodies, no planar servo.
    assert np.all(np.isfinite(sim.data.qvel))
    assert all(w.number==0 for w in sim.data.warning)


def test_slack_lines_cannot_push_or_constrain_payload_height():
    sim=DomeSim(Config(air_density=0));sim.reset(0)
    sim.spool[:]+=.04
    assert np.all(sim.cable_state()['slack'])
    assert sim.cable_state()['tension'] == pytest.approx([0,0,0])
    # With paid-out line, payload can move vertically; the old plane would prevent this.
    p=sim.payload_qpos
    sim.data.qpos[p+2]+=.01
    mujoco.mj_forward(sim.model,sim.data)
    local=sim.data.xmat[sim.hub].reshape(3,3).T@(sim.data.xpos[sim.payload]-sim.data.xpos[sim.hub])
    assert local[2] == pytest.approx(-sim.hang+.01)
    assert sim.cable_state()['tension'] == pytest.approx([0,0,0])


def test_motor_load_limits_retraction_without_clipping_external_tension():
    sim=DomeSim(Config(air_density=0));sim.reset(0)
    sim.spool[0]-=.01  # Large load on reel 1.
    assert sim.cable_state()['tension'][0] > sim.winch_pull_limit
    before=sim.spool.copy()
    sim.step([1,0])
    assert sim.winch_stalled[0]
    assert sim.spool[0] == pytest.approx(before[0])
    assert sim.winch_rates[0] == 0
    assert sim.tensions[0] > sim.winch_pull_limit


def test_initial_line_length_and_inverse_kinematics():
    sim=DomeSim(line_length=.25,target_xy=(.03,.01));sim.reset(0)
    assert sim.cable_state()['lengths'] == pytest.approx([.25]*3)
    expected=np.sqrt(np.sum((sim.attachments[:,:2]-[.03,.01])**2,axis=1)+sim.hang**2)
    assert sim.lengths_for_target([.03,.01]) == pytest.approx(expected)
    target=sim.target_com_world()-sim.data.xpos[sim.hub]
    assert target[:2] == pytest.approx(np.array([.03,.01])*PAYLOAD_MASS/(DOME_MASS+PAYLOAD_MASS))
    with pytest.raises(ValueError):DomeSim(target_xy=(-.09,0))
    with pytest.raises(ValueError):sim.step([np.nan,0])


def test_api_reports_real_line_state_and_preserves_a():
    client=TestClient(app)
    a=client.get('/api/initial?variant=A').json();b=client.get('/api/initial?variant=B').json()
    assert len(a['frame']['tips'])==4 and len(b['frame']['tips'])==3
    assert 'polygon' in a['geometry'][1] and 'triangles' in b['geometry'][1]
    assert b['frame']['tension']==[0,0,0]
    assert b['frame']['line_rest']==pytest.approx([np.hypot(.12,.12)]*3)
    for speed in [10,100]:
        result=experiment(Experiment(variant='B',line_length_mm=250,drive_speed_mm_s=speed,target_x_mm=30,seconds=.1))
        for mode,run in result['runs'].items():
            frames=run['frames'];rest=np.array([f['line_rest'] for f in frames]);t=np.array([f['t'] for f in frames])
            assert np.all(np.abs(np.diff(rest,axis=0))<=speed/1000*np.diff(t)[:,None]+1e-10)
            if mode=='off':assert rest==pytest.approx(np.full_like(rest,.25))
            else:assert rest[-1,0]<rest[0,0] and rest[-1,1]>rest[0,1]
            for f in frames:
                assert len(f['winch_speed'])==len(f['line_actual'])==len(f['line_target'])==3
                assert np.all(np.array(f['tension'])>=0)
    for invalid in [{'line_length_mm':119},{'drive_speed_mm_s':0},{'target_x_mm':-100}]:
        assert client.post('/api/simulate',json={'variant':'B',**invalid}).status_code==422


def test_prediction_copies_reel_state_without_advancing_live_system():
    from b_control import BController
    sim=DomeSim(Config(spool_speed=.1),line_length=.25);sim.reset(15)
    for _ in range(30):sim.step([.2,0])
    qpos=sim.data.qpos.copy();qvel=sim.data.qvel.copy();rest=sim.spool.copy();rates=sim.winch_rates.copy();time=sim.data.time
    ctrl=BController('predictive');target=ctrl.action(sim)*RADIUS
    assert sim.data.time==time and sim.c.dt==.001
    assert sim.data.qpos==pytest.approx(qpos) and sim.data.qvel==pytest.approx(qvel)
    assert sim.spool==pytest.approx(rest) and sim.winch_rates==pytest.approx(rates)
    sim.validate_target(target)
    assert ctrl.predictor.model.nv==12
    assert ctrl.predictor.c.spool_speed==.1


def test_feedback_remains_finite_with_wind_and_no_planar_constraint():
    result=experiment(Experiment(variant='B',b_controller='aero_pd',tilt=15,wind_x=.5,seconds=.6))
    for run in result['runs'].values():
        local=np.array([f['payload_local'] for f in run['frames']])
        assert np.all(np.isfinite(local))
        assert np.ptp(local[:,2])>1e-5
        assert np.all(np.isfinite([f['tilt'] for f in run['frames']]))


def test_cable_integration_converges_when_timestep_is_halved():
    endings=[]
    for dt in [.001,.0005]:
        sim=DomeSim(Config(dt=dt,spool_speed=.15));sim.reset(15,3)
        for _ in range(round(.3/dt)):sim.step([.3,.1],wind=(.3,0,0))
        endings.append((sim.system_com(),sim.data.xpos[sim.payload].copy(),sim.record()[2]))
    assert np.linalg.norm(endings[0][0]-endings[1][0])<.003
    assert np.linalg.norm(endings[0][1]-endings[1][1])<.005
    assert abs(endings[0][2]-endings[1][2])<1


def test_slack_reel_has_no_fictitious_velocity_load():
    sim=DomeSim(Config(air_density=0));sim.reset(0);sim.spool[:]+=.03
    direction=sim.cable_state()['directions'][0]
    sim.data.qvel[6:9]=direction*10
    mujoco.mj_forward(sim.model,sim.data)
    before=sim.spool[0]
    sim.step([1,0])
    assert sim.spool[0] == pytest.approx(before-sim.c.dt*sim.c.spool_speed)
    assert not sim.winch_stalled[0]


def test_cap60_cfd_wrench_matches_lookup_and_is_applied_once():
    from cap_drop import loads,damping_torque
    from dome import CAP_HEIGHT
    assert CAP_HEIGHT==.06
    sim=DomeSim();sim.reset(25,2);sim.spool[:]+=.1
    sim.data.qvel[:6]=[.2,-.1,-1.6,.3,-.4,.2]
    mujoco.mj_forward(sim.model,sim.data)
    rot=sim.data.xmat[sim.hub].reshape(3,3);velocity=np.zeros(6)
    mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,sim.hub,velocity,0)
    f,m,alpha=loads(rot.T@(-velocity[3:]),sim.model.body_ipos[sim.hub],sim.c.air_density)
    damping=damping_torque(rot.T@velocity[:3],sim.c.air_density)
    aero=sim.aerodynamics()
    np.testing.assert_allclose(aero['force'][0],rot@f)
    np.testing.assert_allclose(aero['torque_com'],rot@(m+damping))
    np.testing.assert_allclose(aero['torque_origin'],rot@(m+damping+np.cross(sim.model.body_ipos[sim.hub],f)))
    jp=np.zeros((3,sim.model.nv));jr=np.zeros_like(jp)
    mujoco.mj_jacBodyCom(sim.model,sim.data,jp,jr,sim.hub)
    expected=jp.T@aero['force'][0]+jr.T@aero['torque_com']
    sim.step([0,0])
    np.testing.assert_allclose(sim.data.qfrc_applied,expected,atol=1e-12)


def test_cap60_api_exports_one_resultant_and_torque():
    result=experiment(Experiment(variant='B',b_controller='aero_pd',seconds=.1))
    assert result['model']=='B-cap60-cfd-winches-v1'
    for run in result['runs'].values():
        frame=run['frames'][-1]
        assert len(frame['aero_force'])==len(frame['aero_position'])==1
        assert len(frame['aero_torque'])==3
        assert frame['aero_model']=='cap60-cfd-v1'


def test_tuned_controller_finishes_without_flip_and_keeps_winch_limits():
    result=experiment(Experiment(variant='B',b_controller='optimized',mode='pd',seconds=8))
    run=result['runs']['pd'];summary=run['summary']
    assert result['controller']['tuned_active'] is True
    assert summary['termination']=='ground' and not summary['inverted']
    assert 4.8 < summary['duration'] < 5.6
    for frame in run['frames']:
        assert np.all(np.abs(frame['winch_speed'])<=.04+1e-10)
        assert np.all(np.isfinite(frame['payload_local']))


def test_tuned_profile_falls_back_for_large_initial_tilt():
    from b_control import BController
    for tilt,active in [(25,True),(25.1,False),(35,False)]:
        sim=DomeSim();sim.reset(tilt,16)
        ctrl=BController('optimized');ctrl.action(sim)
        assert ctrl.tuned_active is active
        if not active:
            reference=BController('aero_pd')
            np.testing.assert_allclose(ctrl.action(sim),reference.action(sim))


def test_world_origin_guidance_reduces_drift_without_teleporting():
    result=experiment(Experiment(variant='B',b_controller='position',mode='pd',seconds=8))
    run=result['runs']['pd'];summary=run['summary']
    assert summary['termination']=='ground' and not summary['inverted']
    assert summary['horizontal_error'] < .25
    frames=run['frames']
    assert frames[-1]['horizontal_error']==pytest.approx(summary['horizontal_error'])
    assert frames[-1]['world_target']==[0,0]
    assert np.linalg.norm(np.array(frames[-1]['system_com'])[:2])>1e-4
    for frame in frames:
        assert np.all(np.abs(frame['winch_speed']) <= .04+1e-10)


def test_origin_feedback_points_toward_target_and_brakes_motion():
    from b_control import BController
    for offset,speed in [(.5,0),(0,.5),(-.5,0),(0,-.5)]:
        sim=DomeSim();sim.reset(0)
        sim.data.qpos[0]+=offset;sim.data.qpos[sim.payload_qpos]+=offset
        sim.data.qvel[0]=speed;sim.data.qvel[6]=speed
        mujoco.mj_forward(sim.model,sim.data)
        ctrl=BController('position');action=ctrl.action(sim)
        assert action[0]*(offset+speed)<0
        sim.validate_target(action*RADIUS)
