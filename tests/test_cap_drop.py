import numpy as np
from cap_drop import loads,mass_properties,simulate
from cap_app import Settings,app
from fastapi.testclient import TestClient


def test_aerodynamics_axial_symmetry_and_speed_squared():
    f,m,_=loads(np.array([0,0,1.6]),np.zeros(3))
    assert f[2]>0
    np.testing.assert_allclose(f[:2],0)
    np.testing.assert_allclose(m,0)
    f2,m2,_=loads(np.array([0,0,3.2]),np.zeros(3))
    np.testing.assert_allclose(f2,4*f)


def test_azimuth_covariance_and_offset_torque():
    u=np.array([-.8,0,1.3]);c=np.array([.01,.02,-.04]);R=np.array([[0,-1,0],[1,0,0],[0,0,1]])
    f,m,_=loads(u,c);f2,m2,_=loads(R@u,R@c)
    np.testing.assert_allclose(f2,R@f,atol=1e-14);np.testing.assert_allclose(m2,R@m,atol=1e-14)
    f0,m0,_=loads(u,np.zeros(3));np.testing.assert_allclose(m,m0-np.cross(c,f0))


def test_mass_distribution_has_requested_com_and_positive_inertia():
    c=np.array([.01,-.02,-.04]);mass,b,I=mass_properties(4,6,c)
    np.testing.assert_allclose((.004*np.array([0,0,.03])+.006*b)/mass,c)
    assert np.min(np.linalg.eigvalsh(I))>0


def test_vacuum_freefall_and_no_gravity_torque():
    p=Settings(height=5,tilt=35,com_x_mm=10,seconds=.3).model_dump();p['rho']=0
    r=simulate(p);a,b=r['frames'][0],r['frames'][-1]
    np.testing.assert_allclose(np.array(b['com'])-a['com'],[0,0,-.5*9.81*.3**2],atol=1e-9)
    np.testing.assert_allclose(a['quaternion'],b['quaternion'],atol=1e-12)


def test_upright_remains_upright():
    r=simulate(Settings(tilt=0).model_dump())
    assert max(f['tilt'] for f in r['frames'])<1e-7
    assert r['summary']['horizontal_distance']<1e-10


def test_timestep_refinement():
    p=Settings(seconds=.8).model_dump()
    a=simulate(p,dt=.001)['frames'][-1];b=simulate(p,dt=.0005)['frames'][-1]
    assert np.linalg.norm(np.array(a['com'])-b['com'])<.005
    assert abs(a['tilt']-b['tilt'])<1


def test_http_input_validation_and_result():
    c=TestClient(app)
    assert c.post('/api/simulate',json={'ballast_g':0}).status_code==422
    r=c.post('/api/simulate',json={'seconds':.1})
    assert r.status_code==200 and len(r.json()['frames'])>2


def test_damping_dissipates_tilt_rotation_and_leaves_axial_spin():
    from cap_drop import damping_torque
    w=np.array([2.,-3.,4.]);torque=damping_torque(w)
    assert np.dot(w,torque)<0 and torque[2]==0
    np.testing.assert_allclose(damping_torque(w,rho=0),0)


def test_default_damping_reduces_rotation_without_locking_attitude():
    on=simulate(Settings().model_dump())['summary']
    off=simulate(Settings(rotation_damping=False).model_dump())['summary']
    assert 0<on['peak_spin_deg_s']<off['peak_spin_deg_s']
    assert 10<on['max_tilt']<90


def test_exported_torque_components_and_world_angular_velocity():
    for enabled in [True,False]:
        r=simulate(Settings(seconds=.4,com_x_mm=10,com_y_mm=5,rotation_damping=enabled).model_dump())
        for f in r['frames']:
            np.testing.assert_allclose(np.array(f['torque_aero'])+f['torque_damping'],f['torque'],atol=1e-15)
            np.testing.assert_allclose(np.linalg.norm(f['angular_velocity']),f['spin'])
            assert np.dot(f['torque_damping'],f['angular_velocity'])<=1e-15
            if not enabled:np.testing.assert_allclose(f['torque_damping'],0)


def test_pose_loads_scaling_zero_speed_and_com_shift():
    c=TestClient(app)
    def pose(**kw):
        r=c.post('/api/pose',json=kw)
        assert r.status_code==200
        return r.json()
    a=pose(tilt=30,airspeed=1.6,com_z_mm=0)
    b=pose(tilt=30,airspeed=3.2,com_z_mm=0)
    np.testing.assert_allclose(b['force'],np.array(a['force'])*4)
    np.testing.assert_allclose(b['torque'],np.array(a['torque'])*4)
    shifted=pose(tilt=30,airspeed=1.6,com_z_mm=-40)
    np.testing.assert_allclose(shifted['torque'],np.array(a['torque'])-np.cross(shifted['com'],a['force']))
    still=pose(airspeed=0)
    np.testing.assert_allclose(still['force'],0)
    np.testing.assert_allclose(still['torque'],0)
    np.testing.assert_allclose(still['net'],still['gravity'])
    assert c.post('/api/pose',json={'airspeed':-1}).status_code==422
