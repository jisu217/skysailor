import numpy as np
import pytest
from dome import DomeSim
from clover import Config
from fastapi.testclient import TestClient
import dashboard

@pytest.mark.parametrize('n',[3,4])
def test_plane_rate_and_internal_reaction(n):
    sim=DomeSim(Config(air_density=0),planar=True,cable_count=n,payload_mass=.018)
    sim.reset(0)
    initial=sim.system_com().copy()
    for _ in range(200):
        sim.step([.4,.2])
        local=sim.data.xmat[sim.hub].reshape(3,3).T@(sim.data.xpos[sim.payload]-sim.data.xpos[sim.hub])
        assert abs(local[2])<1e-12
        assert np.max(np.abs(sim.winch_rates))<=sim.c.spool_speed+1e-9
        assert np.max(np.abs(sim.winch_rates))>.039
    # Internal actuator forces must not accelerate the system COM horizontally.
    assert np.linalg.norm((sim.system_com()-initial)[:2])<2e-5
    assert np.linalg.norm(sim.data.qpos[-2:])>.005

@pytest.mark.parametrize('model,n',[('B3',3),('B4',4)])
def test_planar_socket_rewind(tmp_path,monkeypatch,model,n):
    monkeypatch.setattr(dashboard,'FLIGHT_LOG_DIR',tmp_path)
    with TestClient(dashboard.app).websocket_connect('/api/game') as ws:
        ws.send_json({'kind':'reset','mechanism':model});r=ws.receive_json()
        assert len(r['frame']['tips'])==n and r['frame']['hang']==0
        frames=[]
        for _ in range(10):
            ws.send_json({'kind':'step','x':-.7,'y':.7});frames.append(ws.receive_json()['frame'])
        ws.send_json({'kind':'rewind'});assert ws.receive_json()['frame']==frames[4]
        ws.send_json({'kind':'step','x':-.7,'y':.7});assert ws.receive_json()['frame']==frames[5]
