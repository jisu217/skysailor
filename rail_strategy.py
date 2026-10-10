"""Offline rail strategy rollout, isolated from live game state."""
import copy,time
import numpy as np
import mujoco
def metrics(sim):
 R=sim.data.xmat[sim.hub].reshape(3,3);n=R[:,2];tilt=np.arccos(np.clip(n[2],-1,1))
 vel=np.zeros(6);mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,sim.hub,vel,0)
 spin=vel[:3]-n*np.dot(vel[:3],n)
 return tilt,np.linalg.norm(spin),-vel[5]
def choose(sim,prev,predict):
 pred_dt=predict.c.dt
 spec=mujoco.mjtState.mjSTATE_INTEGRATION
 state=np.zeros(mujoco.mj_stateSize(sim.model,spec))
 angles=np.arange(8)*np.pi/4
 candidates=np.vstack([np.zeros(2),*[r*np.column_stack([np.cos(angles),np.sin(angles)]) for r in [.02,.05]]])
 mujoco.mj_getState(sim.model,sim.data,state,spec)
 best=None
 for target in np.vstack([candidates,prev]):
  mujoco.mj_setState(predict.model,predict.data,state,spec);mujoco.mj_forward(predict.model,predict.data)
  predict.wind=sim.wind.copy();cost=0
  for j in range(round(.3/pred_dt)):
   predict.step(target/predict.radius,sim.wind)
   if (j+1)%round(.025/pred_dt)==0:
    tilt,w,descent=metrics(predict)
    # Dominant overturning penalty, then descent and residual rotation.
    loss=1.5*tilt**2+.12*w*w+1.0*max(descent,0)**2+60*max(tilt-np.deg2rad(65),0)**2
    cost+=loss*.025
  tilt,w,descent=metrics(predict)
  cost+=2*tilt**2+.3*w*w+1*max(descent,0)**2+.03*np.sum(((target-prev)/.05)**2)
  if best is None or cost<best[0]:best=(cost,target.copy())
 return best[1]

def rollout(params,strategy,quality,progress):
 # Deferred import avoids a module cycle with the HTTP adapter.
 from dashboard import make_sim,WindProfile,snapshot,geometry
 sim=make_sim(params);sim.reset(params.tilt,params.seed);wind=WindProfile(params);sim.wind=wind.at(0)
 predict=make_sim(params);predict.c=copy.copy(predict.c)
 predict.c.dt=.001 if quality=='fine' else .005;predict.model.opt.timestep=predict.c.dt
 frames=[snapshot(sim)];gs=geometry(sim);target=np.zeros(2);next_update=0;start=time.perf_counter();decisions=0;peak=frames[0]['tilt']
 while sim.data.time<params.seconds-1e-9 and not sim.landed():
  sim.wind=wind.at(sim.data.time)
  if sim.data.time>=next_update-1e-9:
   progress(float(sim.data.time))
   if strategy=='mpc':target=choose(sim,target,predict);decisions+=1
   next_update+=.1
  sim.step(target/sim.radius,sim.wind)
  peak=max(peak,float(metrics(sim)[0]*180/np.pi))
  if round(sim.data.time/sim.c.dt)%20==0:frames.append(snapshot(sim))
 if frames[-1]['t']!=round(sim.data.time,6):frames.append(snapshot(sim))
 t=np.array([f['t'] for f in frames]);speed=np.array([f['speed'] for f in frames])
 return dict(settings=params.model_dump(),strategy=strategy,quality=quality,geometry=gs,frames=frames,
  summary=dict(duration_s=float(sim.data.time),max_tilt_deg=peak,termination='ground' if sim.landed() else 'timeout',
  mean_descent_m_s=float(np.trapezoid(speed,t)/t[-1]),wall_seconds=time.perf_counter()-start),
  prediction=dict(horizon_s=.3,update_s=.1,dt_s=predict.c.dt,future_wind='현재 바람 고정 예측'),wind_source=wind.metadata)
