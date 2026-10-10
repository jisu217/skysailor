import numpy as np
import pytest
from pydantic import ValidationError
from benchmark import Submission,evaluate
from rail_env import RailAirtimeEnv

def test_calm_and_validation():
    env=RailAirtimeEnv(wind_mode='constant');env.reset(seed=0)
    assert np.array_equal(env.sim.wind,np.zeros(3))
    env.step([0,0]);assert np.array_equal(env.sim.wind,np.zeros(3))
    env.close()
    with pytest.raises(ValidationError):
        Submission(metric_id='calm-380-v1',participant='a',name='a',weights=[[0]*17]*2,bias=[float('nan'),0])

def test_evaluation_persists_replays(tmp_path,monkeypatch):
    import benchmark as b
    monkeypatch.setattr(b,'ROOT',tmp_path/'scores');monkeypatch.setattr(b,'REPLAYS',tmp_path/'replays')
    request=Submission(metric_id='calm-380-v1',participant='test',name='neutral',payload_mass_g=32,rail_drop_mm=120,weights=[[0]*17]*2,bias=[0,0])
    row=dict(id='test',status='queued',episodes=[])
    evaluate(row,request)
    assert row['status']=='complete' and len(row['episodes'])==5
    assert row['score']>0 and all((b.REPLAYS/(e['replay_id']+'.json')).exists() for e in row['episodes'])

    import json
    replay=json.loads((b.REPLAYS/(row['episodes'][0]['replay_id']+'.json')).read_text())
    assert replay['settings']['payload_mass_g']==32
    assert replay['settings']['rail_drop_mm']==120
    assert row['hardware']==dict(payload_mass_g=32,rail_drop_mm=120)

@pytest.mark.parametrize('field,value',[('payload_mass_g',0),('rail_drop_mm',4),('rail_drop_mm',301),('rail_drop_mm',float('nan'))])
def test_hardware_bounds(field,value):
    from benchmark import CodeSubmission
    with pytest.raises(ValidationError):
        CodeSubmission(metric_id='wind-380-v1',participant='a',name='b',**{field:value})
