import numpy as np
from cfd.moments import shift_moment,summarize_loads


def test_shift_moment_uses_new_origin_not_added_arm():
    force=np.array([0.,0.,1.]);moment=np.zeros(3)
    np.testing.assert_allclose(shift_moment(moment,force,[.01,0,0]),[0,.01,0])


def test_tilt_coordinates_and_restoring_sign():
    header=['Time','Cd','Cl','Cs','CmPitch']
    values=np.c_[np.arange(1,301),np.ones(300),np.zeros((300,3))]
    for tilt in [-10,10]:
        meta=dict(tilt_deg=tilt,diameter_m=.24,air_density=1.225,speed_m_s=1.6,reference_com_m=[0,0,-.05])
        result=summarize_loads(values,header,meta);f=np.array(result['force_body_N']);a=np.deg2rad(tilt)
        rotation=np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
        np.testing.assert_allclose((rotation@f)[:2],[0,0],atol=1e-12)
        assert result['pitch_tendency']=='restoring'
        assert result['pitch_moment_com_Nm']*tilt<0
        assert result['pitch_moment_origin_Nm']==0
        assert result['all_loads_stable']


def test_unstable_moment_cannot_be_hidden_by_stable_drag():
    h=['Time','Cd','Cl','Cs','CmPitch'];v=np.c_[np.arange(1,301),np.ones(300),np.zeros((300,2)),np.linspace(0,.1,300)]
    r=summarize_loads(v,h,dict(diameter_m=.24,air_density=1.225,speed_m_s=1.6))
    assert not r['all_loads_stable']


def test_openfoam_reported_pitch_axis_controls_sign():
    from cfd.moments import coefficient_frame
    metadata = dict(diameter_m=.24, air_density=1.225, speed_m_s=1.6, tilt_deg=10, reference_com_m=[0,0,0])
    metadata['coefficient_axes'] = coefficient_frame('# pitchAxis : (0 -1 0)\n# sideDir : (0 -1 0)')
    values = np.tile([1, 1, 0, 0, .1], (200, 1))
    result = summarize_loads(values, ['Time','Cd','Cl','Cs','CmPitch'], metadata)
    assert result['pitch_moment_origin_Nm'] < 0
    assert result['pitch_tendency'] == 'restoring'
