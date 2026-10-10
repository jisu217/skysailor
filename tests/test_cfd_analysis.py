"""Prevent false convergence claims and lost history after solver restarts."""
import json
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.mark.parametrize('first_pressure,mesh_ok,expected',[(1e-5,True,True),(.01,True,False),(1e-5,False,False)])
def test_convergence_uses_first_pressure_corrector_and_mesh(tmp_path,first_pressure,mesh_ok,expected):
    metadata=dict(speed_m_s=1.6,air_density=1.225,diameter_m=.24)
    (tmp_path/'metadata.json').write_text(json.dumps(metadata))
    (tmp_path/'log.checkMesh').write_text('cells: 12\n'+('Mesh OK.\n' if mesh_ok else 'Failed 1 mesh checks.\n'))
    residual=lambda name,value:f'Solving for {name}, Initial residual = {value}, Final residual = 1e-9\n'
    log='Time = 400\n'+''.join(residual(name,1e-5) for name in ['Ux','Uy','Uz','k','omega'])
    log+=residual('p',first_pressure)+residual('p',1e-8)+'End\n'
    (tmp_path/'log.solver').write_text(log)
    for start in [0,200]:
        folder=tmp_path/'postProcessing/drag'/str(start);folder.mkdir(parents=True)
        (folder/'coefficient.dat').write_text('# Time Cd\n'+''.join(f'{i} 1.3\n' for i in range(start+1,start+201)))
    subprocess.run([sys.executable,str(Path(__file__).parents[1]/'cfd/analyze.py'),str(tmp_path)],check=True,capture_output=True)
    result=json.loads((tmp_path/'result.json').read_text())
    assert result['iterations']==400
    assert result['last_initial_residuals']['p']==first_pressure
    assert (result['status']=='single_mesh_converged_not_validated') is expected
