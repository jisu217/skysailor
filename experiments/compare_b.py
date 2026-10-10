"""Reproducible controller experiments; reports measured results, not real-world accuracy."""
import sys,json,time,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mujoco
from dome import DomeSim
from clover import Config
from b_control import BController

def trial(sim,algorithm,tilt=15,seed=0,wind=(0,0,0),seconds=6,**gains):
 sim.reset(tilt,seed);sim.wind=np.array(wind,dtype=float);controller=BController(algorithm,**gains)
 initial_com_height=float(sim.system_com()[2])
 samples=[];inverted=False;move=0;previous=sim.spool.copy();saturated=0
 while sim.data.time<seconds-1e-9 and not sim.landed():
  sim.step(controller.action(sim),wind)
  angle=float(sim.record()[2]);inverted|=angle>90
  vel=np.zeros(6);mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,sim.hub,vel,0)
  samples.append((angle,-vel[5]));move+=np.linalg.norm(sim.spool-previous);previous=sim.spool.copy();saturated+=controller.saturated
 values=np.array(samples)
 return dict(algorithm=algorithm,tilt=tilt,seed=seed,wind=list(wind),height=sim.c.height,seconds=seconds,
  duration=round(sim.data.time,4),rms_tilt=float(np.sqrt(np.mean(values[:,0]**2))),max_tilt=float(values[:,0].max()),
  mean_descent_speed=float((initial_com_height-sim.system_com()[2])/sim.data.time),final_descent_speed=float(values[-1,1]),
  inverted=bool(inverted),target_travel_mm=float(move*1000),saturation_fraction=saturated/len(samples),
  termination='ground' if sim.landed() else 'timeout',gains=gains)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--suite',choices=['probe','validation'],default='probe');parser.add_argument('--output',default='outputs/B-control-experiments.json');args=parser.parse_args()
 start=time.time();results=[]
 if args.suite=='probe':
  sim=DomeSim(Config(height=3))
  candidates=[('center',{}),('p',{'kp':.08}),('pd',{'kp':.08,'kd':.02}),('pd',{'kp':.16,'kd':.06}),('aero_pd',{}),('aero_pd',{'torque_kp':.003,'torque_kd':.001})]
  cases=[(15,0,(0,0,0)),(5,1,(0,0,0)),(15,2,(.5,0,0))]
  for tilt,seed,wind in cases:
   for name,gains in candidates:
    result=trial(sim,name,tilt,seed,wind,**gains);results.append(result)
    print(name,gains,tilt,seed,'time',round(result['duration'],2),'RMS',round(result['rms_tilt'],1),'max',round(result['max_tilt'],1),flush=True)
 else:
  cases=[(3,5,11,(0,0,0),1.3),(3,15,12,(0,0,0),1.3),(3,30,13,(0,0,0),1.3),(3,15,14,(.5,-.3,0),1.3),(5,15,15,(0,0,0),1.3),(3,15,16,(-.5,.3,0),1.04),(3,15,17,(.3,.5,0),1.56),(3,45,18,(1,0,0),1.3)]
  for height,tilt,seed,wind,drag in cases:
   sim=DomeSim(Config(height=height,drag_normal=drag))
   for name in ['center','p','pd','aero_pd']:
    result=trial(sim,name,tilt,seed,wind);result['drag_normal']=drag;results.append(result)
    print(name,'case',seed,'time',round(result['duration'],2),'RMS',round(result['rms_tilt'],1),'max',round(result['max_tilt'],1),flush=True)
 Path(args.output).write_text(json.dumps({'model':'B-winched-cables-v1','suite':args.suite,'elapsed_seconds':time.time()-start,'results':results},indent=2)+'\n')
