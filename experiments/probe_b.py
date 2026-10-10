import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mujoco
from dome import DomeSim,RADIUS
from clover import Config
sim=DomeSim(Config(height=3))
for kp,kd in [(0,0),(.03,0),(.08,0),(.15,0),(.08,.02),(.15,.04),(.25,.08),(-.08,-.02)]:
 sim.reset(15,0);tilts=[];next_control=0;action=np.zeros(2)
 while sim.data.time<5 and not sim.landed():
  if sim.data.time>=next_control-1e-9:
   R=sim.data.xmat[sim.hub].reshape(3,3);up=R.T@np.array([0,0,1.]);vel=np.zeros(6);mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,sim.hub,vel,1)
   target=kp*up[:2]-kd*np.array([vel[1],-vel[0]])
   target*=min(1,.055/max(np.linalg.norm(target),1e-10));action=target/RADIUS;next_control+=.02
  sim.step(action);tilts.append(sim.record()[2])
 print(kp,kd,round(sim.data.time,3),round(np.sqrt(np.mean(np.square(tilts))),1),round(max(tilts),1),flush=True)
