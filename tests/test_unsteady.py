import numpy as np
import pytest
from cfd.unsteady_stats import time_mean


def test_adaptive_time_steps_are_time_weighted():
    t=np.array([0.,.001,.01,.1,1.]);y=2*t+3
    assert time_mean(t,y,0,1)==pytest.approx(4)
    assert time_mean(t,y,.05,.8)==pytest.approx(3.85)
    assert not np.isclose(y.mean(),4)


def test_uncovered_window_is_rejected():
    with pytest.raises(ValueError):time_mean([.1,.2],[1,2],0,.2)


def test_short_finished_run_is_not_statistics_validation(tmp_path):
    import json
    from cfd.unsteady_stats import snapshot
    metadata=dict(diameter_m=.24,speed_m_s=1.6,air_density=1.225)
    (tmp_path/'metadata.json').write_text(json.dumps(metadata))
    (tmp_path/'log.solver').write_text('Courant Number mean: 0.1 max: 0.7\ndeltaT = 0.0001\nEnd\n')
    p=tmp_path/'postProcessing/drag/0';p.mkdir(parents=True)
    (p/'coefficient.dat').write_text('# pitchAxis : (0 -1 0)\n# Time Cd CmPitch\n'+''.join(f'{t} 1.4 0.01\n' for t in np.linspace(.0001,.03,1000)))
    result=snapshot(tmp_path)
    assert result['solver_finished']
    assert result['status']=='insufficient_physical_time'
    assert result['statistics'] is None
    assert not result['calibration_ready']


def test_physical_time_case_keeps_mesh_and_resets_clock(tmp_path):
    import json, shutil
    from pathlib import Path
    from cfd.setup_unsteady import create
    source=tmp_path/'source';source.mkdir()
    shutil.copytree(Path(__file__).parents[1]/'cfd/templates/system',source/'system')
    (source/'constant').mkdir();(source/'constant/marker').write_text('same mesh')
    (source/'2200').mkdir()
    for field in ['U','p','k','omega','nut']:(source/'2200'/field).write_text(field+' initial solution')
    (source/'log.solver').write_text('End\n');(source/'log.checkMesh').write_text('Mesh OK\n')
    (source/'metadata.json').write_text('{}')
    target=tmp_path/'transient';create(source,target,.03,.35,.001)
    assert (target/'0/U').read_text()=='U initial solution'
    assert (target/'constant/marker').read_text()=='same mesh'
    assert 'default backward' in (target/'system/fvSchemes').read_text()
    assert 'PIMPLE' in (target/'system/fvSolution').read_text()
    text=(target/'system/controlDict').read_text()
    assert 'endTime 0.03;' in text and 'maxCo 0.35;' in text
    assert json.loads((target/'metadata.json').read_text())['time_mode']=='physical'
    with pytest.raises(ValueError):create(source,target)
