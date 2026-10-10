import numpy as np
import pytest
import manual_arena as m
from benchmark import CodeSubmission

def test_unbounded_hardware_and_replay():
    hw=dict(payload_mass_g=250,connector_drop_mm=250,actuator_speed_mm_s=250)
    r=m.Run(**hw,flight=m.Flight(seed=0,actions=[(0,0,0)]*5))
    CodeSubmission(metric_id='direct-wind-380-v1',participant='test',name='test',**hw)
    result=m.simulate(m.hardware(r),r.flight,True)
    assert result['steps']==5
    assert np.isfinite(result['score'])
    assert np.isfinite(result['summary']['mean_descent_m_s'])
    assert result['summary']['wall_seconds']>0
    assert result['replay']['hardware']==hw

@pytest.mark.parametrize('name,value',[('payload_mass_g',0),('connector_drop_mm',0),('actuator_speed_mm_s',float('inf'))])
def test_invalid_settings(name,value):
    with pytest.raises(ValueError):m.Run(flight=m.Flight(seed=0),**{name:value})
