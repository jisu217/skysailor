from cfd.assess import assess


def result(cd=1.4, moment=0, converged=True):
    return {'mean_cd_last_100':cd,'aero_loads':{'pitch_moment_com_Nm':moment},'status':'single_mesh_converged_not_validated' if converged else 'preliminary_not_converged'}


def test_close_drag_without_convergence_is_not_verified():
    report=assess({'layered-v6':result(),'layered-refined':result(1.401,converged=False)})
    assert report['meridian_comparison']['within_tolerance']
    assert not report['meridian_comparison']['both_converged']
    assert not report['free_flight_calibration_ready']


def test_static_mirror_restoring_is_distinct_from_dynamic_stability():
    report=assess({'tilt-minus10':result(moment=.001),'tilt-plus10':result(moment=-.001)})
    assert report['tilt_comparison']['both_static_restoring']
    assert report['tilt_comparison']['mirror_moment_error']==0
    assert not report['free_flight_calibration_ready']
