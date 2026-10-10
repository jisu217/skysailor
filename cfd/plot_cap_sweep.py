"""Render pilot loads with explicit convergence status; never smooth failed points."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cap_sweep import history

p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
data=json.loads((a.root/'loads.json').read_text());results=data['results']
if not results:raise SystemExit('No results yet')
angles=np.array([r['angle_deg'] for r in results])
fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
for component,label in enumerate(['Fx','Fy','Fz']):
    axes[0,0].plot(angles,[r['force_body_N'][component]*1000 for r in results], 'o--',label=label)
    axes[0,1].plot(angles,[r['torque_origin_body_Nm'][component]*1000 for r in results], 'o--',label=['Mx','My','Mz'][component])
axes[0,0].set(ylabel='Force (mN)',xlabel='Incoming-air angle (deg)',title='Last 100 SIMPLE iterations')
axes[0,1].set(ylabel='Torque at rim centre (mN m)',xlabel='Incoming-air angle (deg)',title='Body coordinates; no COM assumed')
for result in results:
    case=a.root/f"a{result['angle_deg']:03g}"
    f=history(case,'force');m=history(case,'moment');angle=np.deg2rad(result['angle_deg'])
    drag=f[:,1:]@np.array([-np.sin(angle),0,np.cos(angle)])
    axes[1,0].plot(f[:,0],drag*1000,label=f"{result['angle_deg']:g} deg")
    axes[1,1].plot(m[:,0],m[:,2]*1000,label=f"{result['angle_deg']:g} deg")
axes[1,0].set(xlabel='SIMPLE iteration (not seconds)',ylabel='Drag (mN)',title='Iteration history (initial 30 omitted)',xlim=(30,None))
axes[1,1].set(xlabel='SIMPLE iteration (not seconds)',ylabel='My at rim centre (mN m)',title='Iteration history (initial 30 omitted)',xlim=(30,None))
# Exclude startup spikes from vertical scaling while retaining the raw data.
for ax,index in [(axes[1,0],0),(axes[1,1],1)]:
    vals=[]
    for line in ax.lines:
        x,y=line.get_data();vals.extend(np.asarray(y)[np.asarray(x)>=30])
    low,high=min(vals),max(vals);pad=max((high-low)*.08,.01);ax.set_ylim(low-pad,high+pad)
for ax in axes.flat:ax.grid(alpha=.25);ax.legend(fontsize=8);ax.axhline(0,color='gray',lw=.5)
passed=sum(r['status']=='single_mesh_converged_not_validated' for r in results)
fig.suptitle(f'240 mm diameter / 60 mm rise / assumed 1 mm wall / U = 1.6 m/s\nPRELIMINARY: {passed}/{len(results)} pass single-mesh convergence; no grid or experimental validation',fontsize=12)
fig.savefig(a.root/'loads.png',dpi=160)
