import numpy as np
import pytest
import mujoco
from clover import Config
from rail import RailSim
from dashboard import app, Experiment, make_sim, geometry, snapshot
from fastapi.testclient import TestClient


def test_rail_speed_plane_mass_and_reaction():
    sim=RailSim(Config(air_density=0),payload_mass=.018,torque_limit=.0001)
    sim.reset(0);initial=sim.system_com().copy()
    for _ in range(300):
        sim.step([.35,.4])
        r=sim.rail_state()
        assert abs(r['linear_velocity'])<=sim.linear_speed+1e-10
        assert abs(r['torque'])<=sim.torque_limit+1e-12
        local=sim.data.xmat[sim.hub].reshape(3,3).T@(sim.data.xpos[sim.payload]-sim.data.xpos[sim.hub])
        assert local[2]==pytest.approx(-sim.hang,abs=1e-12)
        assert np.linalg.norm(local[:2])==pytest.approx(abs(r['radius']),abs=1e-12)
    assert sim.model.body_mass.sum()==pytest.approx(.0042+.005+.003+.018)
    assert np.linalg.norm((sim.system_com()-initial)[:2])<3e-5
    assert r['angle']>0
    assert sim.data.qvel[5]<0  # Counter-rotation of the free hub.


def test_rail_inertia_and_torque_limit_response():
    angles=[]
    for mass in [.001,.05]:
        sim=RailSim(Config(air_density=0),rail_mass=mass,torque_limit=.00001)
        sim.reset(0)
        initial=sim.rail_state()['axial_inertia']
        sim.data.qpos[sim.payload_qpos]=.1;mujoco.mj_forward(sim.model,sim.data)
        assert sim.rail_state()['axial_inertia']-initial==pytest.approx(sim.payload_mass*.1**2)
        for _ in range(50):sim.step([.1,.8])
        angles.append(sim.rail_state()['angle'])
    assert angles[1]<angles[0]


def test_carriage_can_cross_center_and_stop():
    sim=RailSim(Config(air_density=0));sim.reset(0)
    for target in ([.2,0],[-.2,0],[0,0]):
        for _ in range(650):sim.step(target)
        assert sim.rail_state()['radius']==pytest.approx(target[0]*.12,abs=1e-10)
        assert abs(sim.rail_state()['linear_velocity'])<1e-9
        assert abs(sim.rail_state()['angle'])<1e-9


def test_rail_websocket_rewind_and_geometry(tmp_path,monkeypatch):
    import dashboard
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    with TestClient(app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','mechanism':'C','rail_linear_mm_s':50,'rail_mass_g':7})
        result=ws.receive_json()
        assert result['frame']['mechanism']=='C'
        assert result['frame']['tips']==[]
        assert len(result['geometry'])==len(result['frame']['position'])==60
        assert sum('triangles' in g for g in result['geometry'])==24
        assert np.allclose(result['frame']['position'][1:25],result['frame']['center'])
        frames=[]
        for _ in range(10):
            ws.send_json({'kind':'step','x':.6,'y':.7});frames.append(ws.receive_json()['frame'])
        assert frames[-1]['rail']['linear_velocity']==pytest.approx(.05)
        ws.send_json({'kind':'rewind'});assert ws.receive_json()['frame']==frames[4]
        ws.send_json({'kind':'step','x':.6,'y':.7});assert ws.receive_json()['frame']==frames[5]


def test_guide_ground_contact():
    sim=RailSim();sim.reset(0)
    sim.data.qpos[2]=sim.hang+.001
    mujoco.mj_forward(sim.model,sim.data)
    assert sim.landed()


def test_velocity_drive_decomposes_radial_and_angular_motion():
    sim=RailSim(Config(air_density=0));sim.reset(0)
    sim.data.qpos[sim.payload_qpos]=.06;mujoco.mj_forward(sim.model,sim.data)
    for _ in range(100):sim.step([.5,0],velocity=np.array([0.,.04]))
    assert sim.rail_state()['angle']>.03
    assert abs(sim.rail_state()['linear_velocity'])<=sim.linear_speed+1e-10
    before=sim.rail_state()['radius']
    for _ in range(100):sim.step([.5,0],velocity=np.zeros(2))
    assert sim.rail_state()['radius']==pytest.approx(before,abs=1e-10)
