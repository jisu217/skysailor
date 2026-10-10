"""Compare world-origin guidance with attitude-only control, same actuator bounds."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from dome import DomeSim
from b_control import BController
from clover import Config

def run(algorithm,seed=0,wind=0,dt=.001,kp=1.,kd=1.):
 s=DomeSim(Config(dt=dt),line_length=.1697);s.reset(15,seed);s.wind=np.array([wind,0,0])
 c=BController(algorithm);c.position_kp=kp;c.position_kd=kd
 peak=0
 while s.data.time<8 and not s.landed():
  s.step(c.action(s),s.wind)
  peak=max(peak,np.degrees(np.arccos(np.clip(s.data.xmat[s.hub].reshape(3,3)[2,2],-1,1))))
 return dict(algorithm=algorithm,seed=seed,wind=wind,dt=dt,kp=kp,kd=kd,time=s.data.time,error=float(np.linalg.norm(s.system_com()[:2])),xy=s.system_com()[:2].tolist(),max_tilt=peak,ground=bool(s.landed()))
if __name__=='__main__':
 from concurrent.futures import ProcessPoolExecutor
 jobs=[(a,seed,wind,dt) for seed,wind,dt in [(0,0,.001),(0,0,.0005),(3,0,.001),(4,.2,.001),(5,-.2,.001)] for a in ['optimized','position']]
 with ProcessPoolExecutor(max_workers=4) as pool:
  futures=[pool.submit(run,*j) for j in jobs];results=[f.result() for f in futures]
 print(json.dumps(results,indent=2));Path('outputs/B-position-probe.json').write_text(json.dumps(results,indent=2)+'\n')
