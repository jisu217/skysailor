import numpy as np
from cfd.cap_sweep import shift_to_com, history


def test_offset_com_torque_sign():
    np.testing.assert_allclose(shift_to_com([0,0,.1],[0,0,0],[.01,0,0]),[0,.001,0])


def test_shift_preserves_total_torque_about_original_origin():
    force=np.array([.2,-.1,.3]);torque=np.array([.01,.02,-.03]);com=np.array([.03,.02,-.1])
    np.testing.assert_allclose(shift_to_com(force,torque,com)+np.cross(com,force),torque)


def test_direct_force_parser_uses_total_not_pressure(tmp_path):
    p=tmp_path/'postProcessing/loads/0';p.mkdir(parents=True)
    (p/'force.dat').write_text('# Time total pressure viscous\n1 (1 2 3) (4 5 6) (-3 -3 -3)\n')
    np.testing.assert_allclose(history(tmp_path,'force'),[[1,1,2,3]])


def test_azimuth_rotation_precedes_arbitrary_com_shift():
    from cfd.rebase_cap_loads import rebase
    f,m=rebase([1,0,0],[0,0,0],[0,0,2],90)
    np.testing.assert_allclose(f,[0,1,0],atol=1e-15)
    np.testing.assert_allclose(m,[2,0,0],atol=1e-15)


def test_report_requires_solver_finish_and_residuals(tmp_path,capsys):
    import json
    from cfd.cap_sweep import report
    case=tmp_path/'a000';p=case/'postProcessing/loads/0';p.mkdir(parents=True)
    meta=dict(angle_deg=0,speed_m_s=1.6,air_density=1.225,reference_area_m2=.0452389342,incoming_air_unit_body=[0,0,1],iterations_requested=300)
    (case/'metadata.json').write_text(json.dumps(meta))
    for name,vector in [('force','0 0 .1'),('moment','0 0 0')]:
        (p/f'{name}.dat').write_text(''.join(f'{i} ({vector}) (0 0 0) (0 0 0)\n' for i in range(1,301)))
    (case/'log.checkMesh').write_text('Mesh OK.')
    residuals=''.join(f'Solving for {v}, Initial residual = 1e-7\n' for v in ['p','Ux','Uy','Uz','k','omega'])
    (case/'log.solver').write_text('\nTime = 300\n'+residuals+'End\n')
    report(tmp_path)
    r=json.loads((tmp_path/'loads.json').read_text())['results'][0]
    assert r['status']=='single_mesh_converged_not_validated'
    assert not r['usable_for_dynamics']
    (case/'log.solver').write_text('\nTime = 300\n'+residuals)
    report(tmp_path)
    assert json.loads((tmp_path/'loads.json').read_text())['results'][0]['status']=='preliminary_not_converged'
