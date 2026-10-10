import json
import numpy as np
from cfd.rotation_pilot import inspect


def test_cycle_work_recovers_damping_without_static_stiffness_bias(tmp_path,capsys):
    t=np.linspace(0,.5,2001);omega=8*np.pi
    for name,A in [('fixed',0),('small',5),('large',15)]:
        case=tmp_path/name;p=case/'postProcessing/loads/0';p.mkdir(parents=True)
        theta=np.deg2rad(A)*np.sin(omega*t);rate=np.deg2rad(A)*omega*np.cos(omega*t)
        moment=.001+.0002*t+.002*theta-.0003*rate
        (p/'moment.dat').write_text(''.join(f'{x} (0 {m} 0) (0 0 0) (0 0 0)\n' for x,m in zip(t,moment)))
        (p/'force.dat').write_text(''.join(f'{x} (0 0 .1) (0 0 0) (0 0 0)\n' for x in t))
        (case/'metadata.json').write_text(json.dumps(dict(frequency_hz=4,amplitude_deg=A,peak_rate_deg_s=A*omega)))
        (case/'log.solver').write_text('End')
    inspect(tmp_path)
    r=json.loads((tmp_path/'rotation-summary.json').read_text())['results']
    assert len(r)==2
    for item in r:
        assert abs(item['torque_rate_coefficient_Nm_per_rad_s']+.0003)<1e-10
        assert item['cycle_work_difference_J']<0
        assert item['usable_as_global_correction'] is False
