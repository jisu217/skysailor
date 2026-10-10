from pathlib import Path
import numpy as np,trimesh,json
from generate import grid,clearance,SCALE
O=Path(__file__).resolve().parent
report={}
# Double generating resolution at identical output nodes.
r,z=grid(48,41,2881,0);old=np.load(O/'nominal.npz')['radii'];report['generation_convergence']=dict(pose_count_coarse=1441,pose_count_fine=2881,max_radial_change_mm=float(np.abs(r-old).max()),p95_radial_change_mm=float(np.percentile(np.abs(r-old),95)))
worm=trimesh.load(O/'worm-with-journal.stl');spool=trimesh.load(O/'print-clearance-assembly.stl');T=np.array([[0,0,1,-3*SCALE],[1,0,0,-9],[0,1,0,3],[0,0,0,1]])
volumes=[]
for phi in (np.arange(24)+.31)*2*np.pi/24:
 w=worm.copy();w.apply_transform(trimesh.transformations.rotation_matrix(phi,[0,0,1]));w.apply_transform(T)
 s=spool.copy();s.apply_transform(trimesh.transformations.rotation_matrix(-phi/24,[0,0,1]));inter=trimesh.boolean.intersection([w,s],engine='manifold');volumes.append(float(inter.volume) if len(inter.faces) else 0)
report['independent_mesh_collision']=dict(pose_count=24,max_volume_mm3=max(volumes),volumes_mm3=volumes)
# Close print clearance in either torque direction. Independent surface vertices, analytic worm.
bands=[trimesh.load(O/('print-clearance-'+b+'.stl')).vertices for b in ['lower','upper']]
def gap(v,phi,delta):
 angle=-phi/24+delta;c,s=np.cos(angle),np.sin(angle);x=c*v[:,0]-s*v[:,1];y=s*v[:,0]+c*v[:,1];z=v[:,2];mask=(abs(x)<2.98*SCALE)&(y<-4)&(np.hypot(x,y)>4);return float(clearance(x[mask],y[mask],z[mask],phi).min())
rows=[]
for phi in (np.arange(24)+.29)*2*np.pi/24:
 for sign in [-1,1]:
  lo=0;hi=np.deg2rad(2)
  for _ in range(22):
   mid=(lo+hi)/2
   if min(gap(v,phi,sign*mid) for v in bands)<0:hi=mid
   else:lo=mid
  rows.append(dict(worm_deg=float(np.rad2deg(phi)),direction=sign,closing_wheel_angle_deg=float(np.rad2deg(lo)),lower_gap_mm=gap(bands[0],phi,sign*lo),upper_gap_mm=gap(bands[1],phi,sign*lo)))
report['geometric_flank_closure']=dict(rows=rows,max_other_band_gap_mm=max(max(r['lower_gap_mm'],r['upper_gap_mm']) for r in rows),total_free_angle_deg_range=[2*min(r['closing_wheel_angle_deg'] for r in rows),2*max(r['closing_wheel_angle_deg'] for r in rows)],note='Rigid geometric contact surrogate, not load-bearing contact analysis; no compliance or friction.')
(O/'audit.json').write_text(json.dumps(report,indent=2));print({k:{a:b for a,b in v.items() if a not in ['rows','volumes_mm3']} for k,v in report.items()},flush=True)
