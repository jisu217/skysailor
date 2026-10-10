import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
data=json.loads((a.root/'rotation-summary.json').read_text())
fig,axs=plt.subplots(2,2,figsize=(11,7),layout='constrained')
for r,color in zip(data['results'],['#257d96','#cb7931']):
    d=r['trace'];t=np.array(d['t_s']);label=f"+/-{r['amplitude_deg']:g} deg ({r['peak_rate_deg_s']:.0f} deg/s peak)"
    axs[0,0].plot(t,np.array(d['torque_Nm'])*1000,color=color,label=label)
    axs[0,1].plot(t,np.array(d['delta_Nm'])*1000,color=color,label=label)
    axs[0,1].plot(t,np.array(d['fitted_delta_Nm'])*1000,color=color,ls='--',alpha=.6)
    axs[1,0].plot(d['angle_deg'],np.array(d['delta_Nm'])*1000,color=color,label=label)
    axs[1,1].plot(d['rate_deg_s'],np.array(d['delta_Nm'])*1000,color=color,label=label)
if data['results']:
    d=data['results'][0]['trace'];axs[0,0].plot(d['t_s'],np.array(d['baseline_Nm'])*1000,color='gray',ls=':',label='Fixed-pose control')
axs[0,0].set(title='Measured torque about rim centre',xlabel='Physical time (s)',ylabel='My (mN m)')
axs[0,1].set(title='Rotating minus fixed (dashed: local fit)',xlabel='Physical time (s)',ylabel='Torque difference (mN m)')
axs[1,0].set(title='Dependence on angle and motion history',xlabel='Incoming-air angle (deg)',ylabel='Torque difference (mN m)')
axs[1,1].set(title='Rate dependence is not a single-valued curve',xlabel='Pitch rate (deg/s)',ylabel='Torque difference (mN m)')
for ax in axs.flat:ax.grid(alpha=.25);ax.axhline(0,color='gray',lw=.5);ax.legend(fontsize=8)
fig.suptitle('Forced pitch around 60 deg / U = 1.6 m/s / 4 Hz\nPRELIMINARY: first-order URANS; one measured cycle; no grid/time validation',fontsize=12)
fig.savefig(a.root/'rotation.png',dpi=160)
