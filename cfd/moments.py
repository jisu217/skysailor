"""Aerodynamic loads and origin shifts for body-fixed dome coordinates.
+pitch means dome +z leans towards world +x. The fixed-body flow is R_y(-tilt) z.
Moments applied to the dome must use the dome origin, not the combined COM.
"""
import re
import numpy as np


def coefficient_frame(text):
    """Read actual axes emitted by OpenFOAM, which can override pitchAxis."""
    axes={}
    for name in ["dragDir","sideDir","liftDir","rollAxis","pitchAxis","yawAxis"]:
        match=re.search(r"#\s*"+name+r"\s*:\s*\(([^)]+)\)", text)
        if match:axes[name]=list(map(float,match[1].split()))
    return axes


def shift_moment(moment, force, new_origin):
    return np.asarray(moment)-np.cross(np.asarray(new_origin),np.asarray(force))


def summarize_loads(values, header, metadata, count=100):
    required={'Cd','Cl','Cs','CmPitch'}
    if not required.issubset(header):
        return None
    tail=np.asarray(values[-count:]);angle=np.deg2rad(metadata.get('tilt_deg',0))
    drag=tail[:,header.index('Cd')];lift=tail[:,header.index('Cl')];side=tail[:,header.index('Cs')]
    pitch=tail[:,header.index('CmPitch')]
    area=np.pi*(metadata['diameter_m']/2)**2
    scale=.5*metadata['air_density']*metadata['speed_m_s']**2*area
    axes=metadata.get('coefficient_axes',{})
    drag_axis=np.asarray(axes.get('dragDir',[-np.sin(angle),0,np.cos(angle)]))
    lift_axis=np.asarray(axes.get('liftDir',[np.cos(angle),0,np.sin(angle)]))
    side_axis=np.asarray(axes.get('sideDir',[0,-1,0]))
    pitch_axis=np.asarray(axes.get('pitchAxis',[0,-1,0]))
    force=scale*(drag[:,None]*drag_axis+lift[:,None]*lift_axis+side[:,None]*side_axis)
    moment=pitch[:,None]*pitch_axis*scale*metadata['diameter_m']
    for column,axis in [('CmRoll','rollAxis'),('CmYaw','yawAxis')]:
        if column in header and axis in axes:
            moment+=tail[:,header.index(column),None]*np.asarray(axes[axis])*scale*metadata['diameter_m']
    com=np.asarray(metadata.get('reference_com_m',[0,0,(.0042*.02-.004*.12)/.0082]))
    about_com=shift_moment(moment,force,com)
    checks={}
    for name,column,absolute in [('Cl',lift,.001),('Cs',side,.001),('CmPitch',pitch,.0001)]:
        average=float(np.mean(column));half=len(column)//2
        drift=float(abs(np.mean(column[:half])-np.mean(column[half:]))) if half else float('inf')
        std=float(np.std(column));limit=max(absolute,.02*abs(average))
        checks[name]=dict(mean=average,std=std,drift=drift,limit=limit,stable=bool(len(values)>=200 and std<limit and drift<limit))
    my=float(about_com[:,1].mean());tilt=metadata.get('tilt_deg',0)
    direction='upright_reference' if abs(tilt)<1e-6 else ('restoring' if tilt*my<0 else 'destabilizing')
    return dict(force_body_N=force.mean(axis=0).tolist(),pitch_moment_origin_Nm=float(moment[:,1].mean()),pitch_moment_com_Nm=my,reference_com_m=com.tolist(),positive_pitch='dome axis towards world +x',pitch_tendency=direction,load_stability=checks,all_loads_stable=all(c['stable'] for c in checks.values()),note='Static force/moment only. COM tendency assumes a centred payload at the stated reference; dynamic stability is not proven.')
