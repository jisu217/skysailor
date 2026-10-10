"""Physical-time averages; adaptive-step samples must not have equal weight."""
import json
from pathlib import Path
import re
import numpy as np
try:
    from .moments import coefficient_frame
except ImportError:
    from moments import coefficient_frame


def time_mean(t, y, start, end):
    t,y=np.asarray(t),np.asarray(y)
    if len(t)<2 or not t[0]<=start<end<=t[-1]:
        raise ValueError('Averaging interval must be covered by samples')
    use=(t>start)&(t<end)
    x=np.r_[start,t[use],end];v=np.r_[np.interp(start,t,y),y[use],np.interp(end,t,y)]
    return float(np.sum(np.diff(x)*(v[1:]+v[:-1])/2)/(end-start))


def read_history(case):
    records={};header=None;axes={}
    for file in sorted(case.glob('postProcessing/drag/**/coefficient.dat'),key=lambda p:p.stat().st_mtime):
        lines=file.read_text().splitlines();axes=coefficient_frame('\n'.join(lines[:15]))
        for line in lines:
            if line.lstrip('# ').startswith('Time'):header=line.lstrip('# ').split()
            elif line and not line.startswith('#') and header:
                try:row=list(map(float,line.split()))
                except ValueError:continue
                if len(row)==len(header) and np.all(np.isfinite(row)):records[row[0]]=row
    return header,np.array([records[t] for t in sorted(records)]),axes


def snapshot(case):
    case=Path(case);meta=json.loads((case/'metadata.json').read_text())
    header,v,axes=read_history(case)
    with (case/'log.solver').open('rb') as f:
        f.seek(max(0,f.seek(0,2)-200000));log=f.read().decode(errors='replace')
    co=re.findall(r'Courant Number mean: [\deE.+-]+ max: ([\deE.+-]+)',log)
    delta=re.findall(r'deltaT = ([\deE.+-]+)',log)
    elapsed=re.findall(r'ClockTime = ([\deE.+-]+)',log)
    result=dict(case=case.name,metadata=meta,solver_finished=log.rstrip().endswith('End'),status='insufficient_physical_time',physical_time_s=0,steps=len(v),courant_max_latest=float(co[-1]) if co else None,delta_t_s=float(delta[-1]) if delta else None,solver_wall_s=float(elapsed[-1]) if elapsed else None,statistics=None,trace=[],calibration_ready=False)
    if len(v)<2:return result
    t=v[:,0];cd=v[:,header.index('Cd')];scale=.5*meta['air_density']*meta['speed_m_s']**2*np.pi*(meta['diameter_m']/2)**2
    my=v[:,header.index('CmPitch')]*axes.get('pitchAxis',[0,-1,0])[1]*scale*meta['diameter_m']
    result['physical_time_s']=float(t[-1]);result['mean_cd_observed']=time_mean(t,cd,t[0],t[-1])
    result['trace']=[[float(t[i]),float(cd[i]),float(my[i]*1000)] for i in np.unique(np.linspace(0,len(t)-1,min(len(t),600),dtype=int))]
    convective=meta['diameter_m']/meta['speed_m_s'];discard=5*convective;required=10*convective
    result.update(convective_time_s=convective,discard_before_s=discard,required_statistics_window_s=required)
    if t[-1]>discard and t[0]<=discard:
        end=float(t[-1]);mean=time_mean(t,cd,discard,end);mid=(discard+end)/2
        drift=abs(time_mean(t,cd,discard,mid)-time_mean(t,cd,mid,end))/max(abs(mean),1e-12)
        result['statistics']=dict(start_s=discard,end_s=end,mean_cd=mean,mean_drag_N=mean*scale,half_window_drift=drift,sufficient_duration=end-discard>=required-1e-8)
        if end-discard>=required-1e-8:result['status']='statistics_available_not_validated'
    return result
