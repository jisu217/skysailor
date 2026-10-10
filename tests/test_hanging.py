import json
import numpy as np
import pytest
from hanging import HangingEnv,HangingSim
from benchmark import Submission,CodeSubmission,evaluate,HANGING_ID,hardware_for

def test_hanging_physics_and_geometry():
    from dashboard import snapshot,geometry
    s=HangingSim();s.reset(0);s.c.air_density=0
    start=s.system_com().copy();lengths=s.data.ten_length.copy()
    for _ in range(100):s.step([.5,-.5,0],np.zeros(3))
    assert np.isfinite(s.data.qpos).all()
    assert np.linalg.norm(s.data.ten_length-lengths)>1e-5
    assert np.max(np.abs(s.tensions))<=.5
    # Internal motors cannot accelerate the whole-system COM horizontally.
    assert np.linalg.norm(s.system_com()[:2]-start[:2])<1e-8
    assert abs(s.system_com()[2]-(start[2]-.5*9.81*.1**2))<.001
    assert abs(np.linalg.norm(s.data.xpos[s.payload]-s.data.xpos[s.connector])-s.pendulum_length)<1e-9
    f=snapshot(s);assert f['mechanism']=='H' and len(f['position'])==len(geometry(s))

def test_hanging_evaluation(tmp_path,monkeypatch):
    import benchmark as b
    monkeypatch.setattr(b,'ROOT',tmp_path/'scores');monkeypatch.setattr(b,'REPLAYS',tmp_path/'replays')
    request=Submission(metric_id=HANGING_ID,participant='test',name='neutral',weights=[[0]*28]*3,bias=[0]*3,ring_radius_mm=90,pendulum_length_mm=70,payload_mass_g=22)
    row=dict(id='test',episodes=[]);evaluate(row,request)
    assert row['status']=='complete' and len(row['episodes'])==5
    replay=json.loads((b.REPLAYS/(row['episodes'][0]['replay_id']+'.json')).read_text())
    assert replay['hardware']['ring_radius_mm']==90 and replay['hardware']['pendulum_length_mm']==70
    assert replay['frames'][0]['mechanism']=='H'
    env=HangingEnv(hardware_for(request));obs,_=env.reset();assert obs.shape==(28,)
    assert np.isfinite(obs).all()

@pytest.mark.parametrize('field,value',[('ring_radius_mm',0),('connector_drop_mm',20),('pendulum_length_mm',200),('actuator_speed_mm_s',float('nan'))])
def test_hanging_invalid_hardware(field,value):
    with pytest.raises(ValueError):CodeSubmission(metric_id=HANGING_ID,participant='t',name='t',**{field:value})

def test_direct_no_pendulum_and_momentum():
    from hanging import DirectSim,DirectEnv
    s=DirectSim();s.reset(0);s.c.air_density=0
    assert s.model.nv==9 and s.model.nq==10
    assert np.allclose(np.linalg.norm(s.attachments[:,:2],axis=1),.19)
    start=s.system_com().copy()
    for _ in range(100):s.step([.5,-.5,0],np.zeros(3))
    assert np.allclose(s.data.xpos[s.payload],s.data.xpos[s.connector])
    assert np.linalg.norm(s.system_com()[:2]-start[:2])<1e-8
    assert np.isfinite(s.data.qpos).all()
    env=DirectEnv(dict(payload_mass_g=22,connector_drop_mm=100,actuator_speed_mm_s=40))
    obs,_=env.reset();assert obs.shape==(22,)

def test_direct_evaluation(tmp_path,monkeypatch):
    import benchmark as b
    monkeypatch.setattr(b,'ROOT',tmp_path/'scores');monkeypatch.setattr(b,'REPLAYS',tmp_path/'replays')
    request=Submission(metric_id=b.DIRECT_ID,participant='test',name='neutral',weights=[[0]*22]*3,bias=[0]*3,connector_drop_mm=100)
    row=dict(id='test',episodes=[]);evaluate(row,request)
    assert row['status']=='complete' and len(row['episodes'])==5
    replay=json.loads((b.REPLAYS/(row['episodes'][0]['replay_id']+'.json')).read_text())
    assert replay['frames'][0]['mechanism']=='P' and replay['hardware']['connector_drop_mm']==100
    assert 'pendulum_length_mm' not in replay['hardware']
