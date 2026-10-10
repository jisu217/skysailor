"""Fast forced-pitch URANS experiment, not a universal rotational correction."""
import argparse,json,math,re
from pathlib import Path
import numpy as np
try:
    from .setup_unsteady import create
    from .cap_sweep import history
except ImportError:
    from setup_unsteady import create
    from cap_sweep import history


def setup(source,target,amplitude=5,frequency=4,cycles=2):
    if not np.isfinite(amplitude) or amplitude<0 or not np.isfinite(frequency) or frequency<=0 or cycles<2:
        raise ValueError("Require nonnegative amplitude, positive frequency, and at least two cycles")
    source,target=Path(source),Path(target)
    create(source,target,duration=cycles/frequency,max_co=3,max_dt=.002)
    p=target/'system/fvSchemes';s=p.read_text().replace('default backward','default Euler').replace('Gauss linearUpwind grad(U)','Gauss upwind')
    s+='\nfluxRequired { default no; p; pcorr; }\n';p.write_text(s)
    p=target/'system/fvSolution';s=p.read_text().replace('nOuterCorrectors 2','nOuterCorrectors 1').replace('nNonOrthogonalCorrectors 1','nNonOrthogonalCorrectors 0')
    s=s.replace('solvers {','solvers { "pcorr.*" { solver GAMG; tolerance 1e-6; relTol 0; smoother GaussSeidel; }')
    s=s.replace('PIMPLE {','PIMPLE { correctPhi yes; checkMeshCourantNo yes; pRefCell 0; pRefValue 0;')
    p.write_text(s)
    p=target/'0/U';s=p.read_text();s=re.sub(r'(dome\s*\{\s*type\s+)noSlip',r'\1movingWallVelocity; value uniform (0 0 0)',s);p.write_text(s)
    (target/'constant/dynamicMeshDict').write_text(f'''FoamFile {{version 2.0; format ascii; class dictionary; object dynamicMeshDict;}}
dynamicFvMesh dynamicMotionSolverFvMesh;
motionSolverLibs ("libfvMotionSolvers.so");
solver solidBody;
solidBodyCoeffs {{
 solidBodyMotionFunction oscillatingRotatingMotion;
 oscillatingRotatingMotionCoeffs {{ origin (0 0 0); amplitude (0 {amplitude} 0); omega {2*math.pi*frequency}; }}
}}
''')
    p=target/'system/controlDict';s=p.read_text();s=re.sub(r'writeInterval\s+0.01;',f'writeInterval {1/frequency/4};',s,count=1)
    s+='\nlibs ("libdynamicFvMesh.so");\n';p.write_text(s)
    p=target/'metadata.json';m=json.loads(p.read_text());m.update(amplitude_deg=amplitude,frequency_hz=frequency,cycles=cycles,
        peak_rate_deg_s=amplitude*2*math.pi*frequency,reference_angle_deg=60,
        solver='pimpleFoam ALE moving mesh URANS kOmegaSST',time_scheme='Euler; first-order upwind',
        note='Mesh passing checkMesh reused; whole-domain pitch around rim centre; discard first cycle; 1 measured cycle is preliminary only; baseline not converged; inferred rate term also includes wake phase lag; no validation at other angles, speeds or axes.')
    p.write_text(json.dumps(m,indent=2)+'\n')


def inspect(root):
    root=Path(root);results=[]
    base=history(root/'fixed','moment')
    for case in [root/'small',root/'large']:
        meta=json.loads((case/'metadata.json').read_text());m=history(case,'moment');f=history(case,'force')
        if not len(m) or not len(base):continue
        period=1/meta['frequency_hz'];end=min(m[-1,0],base[-1,0]);start=period
        if end<2*period-1e-7:continue
        # Uniform time grid avoids bias from adaptive solver sampling.
        t=np.linspace(start,2*period,1001);omega=2*np.pi*meta['frequency_hz'];A=np.deg2rad(meta['amplitude_deg'])
        theta=A*np.sin(omega*t);rate=A*omega*np.cos(omega*t)
        my=np.interp(t,m[:,0],m[:,2]);fixed=np.interp(t,base[:,0],base[:,2]);delta=my-fixed
        design=np.column_stack([np.ones_like(t),theta,rate])
        fit=np.linalg.lstsq(design,delta,rcond=None)[0];prediction=design@fit
        integral=lambda y:float(np.sum(np.diff(t)*(y[1:]+y[:-1])/2))
        C=integral(delta*rate)/integral(rate**2)
        energy=integral(delta*rate)
        force=np.column_stack([np.interp(t,f[:,0],f[:,j]) for j in [1,2,3]])
        body=force.copy();body[:,0]=np.cos(theta)*force[:,0]-np.sin(theta)*force[:,2];body[:,2]=np.sin(theta)*force[:,0]+np.cos(theta)*force[:,2]
        log=(case/'log.solver').read_text();courant=re.findall(r'Courant Number mean: [\deE.+-]+ max: ([\deE.+-]+)',log)
        result=dict(case=case.name,amplitude_deg=meta['amplitude_deg'],frequency_hz=meta['frequency_hz'],
            peak_rate_deg_s=meta['peak_rate_deg_s'],time_window_s=[start,2*period],
            torque_rate_coefficient_Nm_per_rad_s=C,cycle_work_difference_J=energy,
            interpretation='damping_like' if C<0 else 'driving_like',
            force_body_range_N=np.ptp(body,axis=0).tolist(),torque_peak_to_peak_Nm=float(np.ptp(my)),
            fit_offset_Nm=float(fit[0]),fit_displacement_Nm_per_rad=float(fit[1]),
            fit_rms_Nm=float(np.sqrt(np.mean((delta-prediction)**2))),
            final_courant_max=float(courant[-1]) if courant else None,
            solver_finished=log.rstrip().endswith('End'),usable_as_global_correction=False,
            trace=dict(t_s=t[::10].tolist(),angle_deg=(60+np.degrees(theta[::10])).tolist(),rate_deg_s=np.degrees(rate[::10]).tolist(),
                       torque_Nm=my[::10].tolist(),baseline_Nm=fixed[::10].tolist(),delta_Nm=delta[::10].tolist(),
                       fitted_delta_Nm=prediction[::10].tolist(),force_body_N=body[::10].tolist()))
        results.append(result)
    (root/'rotation-summary.json').write_text(json.dumps(dict(reference_angle_deg=60,speed_m_s=1.6,
       limitations='Single analysed cycle after one discarded cycle; first-order ALE URANS; comparison is exploratory, not an identified universal angular damping coefficient.',results=results),indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='trace'} for r in results],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','report']);p.add_argument('source');p.add_argument('target',nargs='?');p.add_argument('--amplitude',type=float,default=5);p.add_argument('--frequency',type=float,default=4);p.add_argument('--cycles',type=int,default=2);a=p.parse_args()
    if a.action=='setup':setup(a.source,a.target,a.amplitude,a.frequency,a.cycles)
    else:inspect(a.source)
