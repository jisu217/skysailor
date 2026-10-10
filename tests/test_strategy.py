import time
import numpy as np
import mujoco
from fastapi.testclient import TestClient
import dashboard
from rail_strategy import rollout,choose


def test_background_strategy_persistence_and_replay(tmp_path,monkeypatch):
    monkeypatch.setattr(dashboard,'STRATEGY_DIR',tmp_path)
    client=TestClient(dashboard.app)
    assert client.post('/api/game/strategies',json={'parameters':{'mechanism':'A'}}).status_code==422
    for mode in ['center','mpc']:
        r=client.post('/api/game/strategies',json={'strategy':mode,'quality':'fast','parameters':{'variant':'B','mechanism':'C','seconds':.12,'tilt':5,'payload_mass_g':18}})
        assert r.status_code==200
        job=r.json()['id']
        for _ in range(200):
            status=client.get('/api/game/strategies/'+job).json()
            if status['status'] in ['complete','failed']:break
            time.sleep(.02)
        assert status['status']=='complete',status
        data=client.get('/api/game/strategies/'+job+'/result').json()
        assert data['frames'][0]['t']==0 and data['frames'][-1]['t']==.12
        assert len(data['geometry'])==len(data['frames'][0]['position'])
        assert data['settings']['payload_mass_g']==18
        assert np.isfinite(data['summary']['mean_descent_m_s'])
        # Completed files remain accessible after transient job metadata disappears.
        dashboard.strategy_jobs.pop(job)
        assert client.get('/api/game/strategies/'+job).json()['status']=='complete'
    assert len(client.get('/api/game/strategies').json())==2
    assert client.get('/api/game/strategies/invalid/result').status_code==404


def test_prediction_preserves_live_state():
    params=dashboard.Experiment(variant='B',mechanism='C')
    sim=dashboard.make_sim(params);prediction=dashboard.make_sim(params)
    prediction.c.dt=.005;prediction.model.opt.timestep=.005
    q=sim.data.qpos.copy();v=sim.data.qvel.copy();t=sim.data.time
    target=choose(sim,np.zeros(2),prediction)
    assert np.array_equal(sim.data.qpos,q) and np.array_equal(sim.data.qvel,v) and sim.data.time==t
    assert np.linalg.norm(target)<=.05+1e-10
