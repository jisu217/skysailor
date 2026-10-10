"""Gymnasium preparation for altitude-integral training; provisional 380x80 aerodynamic scaling.
Observations assume noiseless current state/wind.
Action = normalized rail angular-speed command, carriage linear-speed command.
Force/acceleration limits below are provisional engineering assumptions.
"""
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import mujoco
from dashboard import Experiment,make_sim,WindProfile

class RailAirtimeEnv(gym.Env):
    metadata={'render_modes':[]}
    def __init__(self,diameter_mm=380,dome_mass_g=25,wind_clips=('gentle','up','down'),seconds=10,
                 linear_force_n=.5,linear_accel_m_s2=.5,reward_mode="altitude",wind_mode="measured",payload_mass_g=18,rail_drop_mm=5):
        if reward_mode not in ("altitude","airtime"):raise ValueError("Unknown reward mode")
        self.reward_mode=reward_mode
        if wind_mode not in ("constant","measured"):raise ValueError("Invalid wind mode")
        if not 0<seconds<=10 or min(linear_force_n,linear_accel_m_s2)<=0:raise ValueError('Invalid episode/drive limits')
        if not wind_clips or any(c not in ('gentle','up','down') for c in wind_clips):raise ValueError('Unknown wind clip')
        self.params=Experiment(variant='B',mechanism='C',dome_diameter_mm=diameter_mm,dome_mass_g=dome_mass_g,payload_mass_g=payload_mass_g,rail_drop_mm=rail_drop_mm,rail_linear_mm_s=30,rail_torque_mnm=5,rail_angular_deg_s=180,wind_mode=wind_mode,seconds=seconds)
        self.clips=wind_clips;self.force_limit=linear_force_n;self.accel_limit=linear_accel_m_s2
        self.action_space=spaces.Box(-1,1,(2,),dtype=np.float32)
        self.observation_space=spaces.Box(-np.inf,np.inf,(17,),dtype=np.float32)
        self.sim=None;self.last_action=np.zeros(2);self.done=True
    def observation(self):
        s=self.sim;R=s.data.xmat[s.hub].reshape(3,3);vel=np.zeros(6)
        mujoco.mj_objectVelocity(s.model,s.data,mujoco.mjtObj.mjOBJ_BODY,s.hub,vel,0)
        theta=s.data.qpos[s.angle_qpos]
        return np.r_[R.T@np.array([0.,0.,1.]),R.T@vel[:3]/10,R.T@(s.wind-vel[3:])/10,
                     s.data.xpos[s.hub,2]/3,np.sin(theta),np.cos(theta),s.data.qpos[s.payload_qpos]/s.radius,
                     s.data.qvel[6]/s.angular_speed,s.data.qvel[7]/s.linear_speed,self.last_action].astype(np.float32)
    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed)
        p=self.params.model_copy(update={'wind_clip':str(self.np_random.choice(self.clips))})
        self.wind=WindProfile(p);self.sim=make_sim(p)
        self.sim.linear_force_limit=self.force_limit;self.sim.linear_accel_limit=self.accel_limit
        self.sim.reset(float(self.np_random.uniform(3,15)),int(self.np_random.integers(0,100000)))
        self.sim.wind=self.wind.at(0);self.last_action=np.zeros(2);self.done=False
        return self.observation(),{'wind_clip':p.wind_clip,'aero_model':'provisional-scaled-240mm-coefficients' if p.dome_diameter_mm==380 else 'cap60-cfd-v1','reward_mode':self.reward_mode,'altitude_reference':'whole-system COM above ground','force_limit_n':self.force_limit,'accel_limit_m_s2':self.accel_limit}
    def step(self,action):
        if self.done:raise RuntimeError('Call reset before step')
        a=np.asarray(action,dtype=float)
        if a.shape!=(2,) or not np.all(np.isfinite(a)):raise ValueError('Invalid action')
        a=np.clip(a,-1,1);s=self.sim;t0=float(s.data.time);altitude_integral=0.
        for _ in range(20):
            if s.landed() or s.data.time>=self.params.seconds-1e-9:break
            s.wind=self.wind.at(s.data.time)
            h0=max(0.,float(s.system_com()[2]))
            before=float(s.data.time);s.step(np.zeros(2),s.wind,drive=[a[0]*s.angular_speed,a[1]*s.linear_speed])
            if s.data.time<=before:raise FloatingPointError('Physics reset during integration')
            h1=max(0.,float(s.system_com()[2]))
            altitude_integral+=(h0+h1)*.5*(s.data.time-before)
        s.wind=self.wind.at(min(s.data.time,self.params.seconds));self.last_action=a
        terminated=bool(s.landed());truncated=bool(s.data.time>=self.params.seconds-1e-9 and not terminated);self.done=terminated or truncated
        reward=altitude_integral if self.reward_mode=="altitude" else float(s.data.time-t0)
        return self.observation(),float(reward),terminated,truncated,{'reward_mode':self.reward_mode,'altitude_integral_m_s':float(altitude_integral),'altitude_m':float(s.system_com()[2]),'elapsed_s':float(s.data.time-t0),'time_s':float(s.data.time),'tilt_deg':float(s.record()[2]),'linear_force_n':float(s.rail_drive[1])}
