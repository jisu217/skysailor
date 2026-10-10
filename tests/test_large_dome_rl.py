import numpy as np
from dashboard import Experiment,make_sim,snapshot
from rail_env import RailAirtimeEnv
from gymnasium.utils.env_checker import check_env

def test_large_geometry_mass_and_aero_scaling():
 a=make_sim(Experiment(variant='B',mechanism='C'));b=make_sim(Experiment(variant='B',mechanism='C',dome_diameter_mm=380,dome_mass_g=25))
 assert b.radius==.19 and b.depth==.08
 assert np.isclose(b.model.body_mass[b.hub],.025)
 a.reset(0,0);b.reset(0,0);a.wind=np.array([0.,0.,1.]);b.wind=a.wind.copy()
 assert np.allclose(b.aerodynamics()['force'],a.aerodynamics()['force']*(.19/.12)**2)
 assert 'provisional' in snapshot(b)['aero_model']
 vertices=np.concatenate([p['vertices'] for p in b.panels]);assert np.isclose(vertices[:,2].max(),.08)
 assert np.isclose(np.linalg.norm(vertices[:,:2],axis=1).max(),.19)

def test_gym_contract_reward_limits_and_determinism():
 env=RailAirtimeEnv(seconds=.12,reward_mode="airtime");check_env(env,skip_render_check=True)
 o,info=env.reset(seed=5);total=0
 for _ in range(6):
  o,r,done,truncated,info=env.step(np.array([1,1],dtype=np.float32));total+=r
  assert np.isfinite(o).all() and abs(info['linear_force_n'])<=.5+1e-9
 assert np.isclose(total,.12) and truncated


def test_altitude_reward_weights_height_and_partial_steps():
 # Constant measured height isolates the reward from dynamics, including the
 # final partial control interval (10 ms rather than 20 ms).
 for height in [1.,3.]:
  env=RailAirtimeEnv(seconds=.1)
  env.reset(seed=3)
  env.params=env.params.model_copy(update={'seconds':.03})
  env.sim.system_com=lambda:np.array([0.,0.,height])
  _,a,_,_,info=env.step(np.zeros(2));_,b,_,truncated,last=env.step(np.zeros(2))
  assert np.isclose(a,height*.02) and np.isclose(b,height*.01)
  assert np.isclose(a+b,height*.03) and truncated
  assert last['reward_mode']=='altitude'
