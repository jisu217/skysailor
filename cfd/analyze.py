"""Inspect OpenFOAM coefficients and residuals; never auto-calibrate the live model."""
import argparse,json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.colors import TwoSlopeNorm
from moments import summarize_loads, coefficient_frame

p=argparse.ArgumentParser();p.add_argument('case');args=p.parse_args();case=Path(args.case)
metadata=json.loads((case/'metadata.json').read_text())
files=list(case.glob('postProcessing/drag/**/*coeff*.dat'))+list(case.glob('postProcessing/drag/**/*Coeff*.dat'))
if not files:raise RuntimeError('No force coefficients produced')
source=max(files,key=lambda p:p.stat().st_mtime)
metadata['coefficient_axes']=coefficient_frame(source.read_text())
header=None
for line in source.read_text().splitlines():
 if line.lstrip('# ').startswith('Time'):
  header=line.lstrip('# ').split()
history={}
for segment in sorted(set(files),key=lambda p:p.stat().st_mtime):
 for row in np.loadtxt(segment,comments='#',ndmin=2):history[float(row[0])]=row
values=np.array([history[t] for t in sorted(history)])
if header is None or 'Cd' not in header:raise RuntimeError('Cannot identify Cd column')
cd=values[:,header.index('Cd')];tail=cd[-min(100,len(cd)):]
mean=float(np.mean(tail));relative_std=float(np.std(tail)/max(abs(mean),1e-12))
half=len(tail)//2;drift=float(abs(np.mean(tail[:half])-np.mean(tail[half:]))/max(abs(mean),1e-12)) if half else None
log=(case/'log.solver').read_text();residuals={}
last_block=re.split(r'\nTime = ',log)[-1]
for name,initial,final in re.findall(r'Solving for (\w+), Initial residual = ([\deE.+-]+), Final residual = ([\deE.+-]+)',last_block):
 if name not in residuals:residuals[name]=float(initial)
force=.5*metadata['air_density']*metadata['speed_m_s']**2*np.pi*(metadata['diameter_m']/2)**2*mean
force_stable=len(cd)>=200 and relative_std<.02 and drift is not None and drift<.02
residual_pass=all(residuals.get(v,1)<limit for v,limit in [('p',1e-3),('Ux',1e-4),('Uy',1e-4),('Uz',1e-4),('k',1e-3),('omega',1e-3)])
mesh=(case/'log.checkMesh').read_text()
mesh_pass='Mesh OK' in mesh
finished=bool(re.search(r'\nEnd\s*$',log))
yplus=None
yfiles=list(case.glob('postProcessing/yPlus/**/*.dat'))
if yfiles:
 rows=[line.split() for line in max(yfiles,key=lambda p:p.stat().st_mtime).read_text().splitlines() if line.strip() and not line.startswith('#')]
 if rows:
  row=rows[-1];yplus=dict(iteration=float(row[0]),patch=row[1],minimum=float(row[2]),maximum=float(row[3]),average=float(row[4]))
cell_match=re.search(r'cells:\s+(\d+)',mesh)
if cell_match is None:raise RuntimeError('Invalid checkMesh log: rerun checkMesh -allGeometry -allTopology before analysis')
result=dict(metadata=metadata,solver_finished=finished,y_plus=yplus,cells=int(cell_match[1]),iterations=len(cd),last_iteration=float(values[-1,0]),mean_cd_last_100=mean,cd_relative_std=relative_std,cd_relative_drift=drift,drag_N=force,weight_N=.0082*9.81,
 approximate_terminal_speed_if_cd_constant=float(np.sqrt(2*.0082*9.81/(metadata['air_density']*np.pi*.12**2*mean))) if mean>0 else None,
 force_stable=force_stable,residual_pass=residual_pass,last_initial_residuals=residuals,mesh_check_pass=mesh_pass,
 status='single_mesh_converged_not_validated' if finished and mesh_pass and force_stable and residual_pass else 'preliminary_not_converged',
 warning='A single-speed fixed-body steady RANS result is not a validated terminal velocity. Grid/domain/time dependence, unsteady wake, shell thickness, and real-world calibration remain unresolved.')
loads=summarize_loads(values,header,metadata)
result['aero_loads']=loads
if loads and not loads['all_loads_stable']:result['status']='preliminary_not_converged'
samples=list(case.glob('postProcessing/planes/**/*.raw'))
result['field_iteration']=float(max(samples,key=lambda p:p.stat().st_mtime).parent.name) if samples else None
(case/'result.json').write_text(json.dumps(result,indent=2)+'\n')
plt.style.use('dark_background')
has_moment=loads is not None
fig,axes=plt.subplots(3 if has_moment else 2,1,figsize=(7,8),layout='constrained')
axes[0].plot(values[:,0],cd,color='#71e5bd',lw=1)
axes[0].set(xlabel='SIMPLE iteration (not physical time)',ylabel='Cd',title=f'Fixed dome / {metadata["speed_m_s"]} m/s\n{result["status"]}')
axes[1].plot(values[-len(tail):,0],tail,color='#71e5bd',lw=1.5)
axes[1].axhline(mean,color='#ffd77c',ls='--',label=f'Mean Cd = {mean:.3f}')
axes[1].set(xlabel='SIMPLE iteration (not physical time)',ylabel='Cd',title=f'Last {len(tail)} iterations / mean drift {(drift or 0):.1%}')
axes[1].legend()
if has_moment:
 my=values[:,header.index('CmPitch')]*metadata['coefficient_axes'].get('pitchAxis',[0,-1,0])[1]
 qA=.5*metadata['air_density']*metadata['speed_m_s']**2*np.pi*(metadata['diameter_m']/2)**2
 axes[2].plot(values[:,0],my*qA*metadata['diameter_m']*1000,color='#e9bbff',lw=1)
 axes[2].axhline(0,color='#95a7b3',lw=.5)
 axes[2].set(xlabel='SIMPLE iteration (not physical time)',ylabel='My (mN m)',title='Pitch moment about dome origin / body +y')
fig.savefig(case/'convergence.png',dpi=150);plt.close(fig)
from field_plots import render_fields
render_fields(case,metadata,result)
print(json.dumps(result,indent=2))
