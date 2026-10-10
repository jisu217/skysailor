"""Numerical generating envelope of the measured CAD worm profile.
Units mm/rad. No hand-set helix or lower-ring phase. 24:1 negative rotation.
Radial-solid assumption is tested separately; results are geometric, not FEA.
"""
from pathlib import Path
import numpy as np,trimesh,json,time
O=Path(__file__).resolve().parent
N=24;C=9.0;SCALE=1.0631953679858266;LEAD=1.875*SCALE;TIP=8.4119722843;RINNER=7.0

def clearance(x,y,z,phi,relief=0):
 theta=np.arctan2(z-3,y+C)-phi
 phase=(x+3*SCALE-LEAD*theta/(2*np.pi)+LEAD/2)%LEAD-LEAD/2
 radius=2.25+np.clip(.8625-np.abs(phase)/SCALE,0,.75)+relief
 return np.maximum(np.hypot(y+C,z-3)-radius,np.abs(x)-3*SCALE)

def field(r,a,z,phis,relief):
 result=np.full(r.shape,np.inf)
 for batch in np.array_split(phis,24):
  angle=a[:,None]-batch[None,:]/N
  x=r[:,None]*np.cos(angle);y=r[:,None]*np.sin(angle)
  val=clearance(x,y,z[:,None],batch[None,:],relief)
  result=np.minimum(result,val.min(axis=1))
 return result

def grid(ns,nz,phases,relief):
 a=-np.pi/2+np.arange(ns)*2*np.pi/N/ns
 zz=np.r_[np.linspace(0,2,nz),np.linspace(4,6,nz)]
 aa,z=np.meshgrid(a,zz,indexing='ij');a=aa.ravel();z=z.ravel()
 limit=TIP-(TIP-RINNER)*np.where(z<=2,z/2,(6-z)/2)
 lo=np.full_like(z,3.0);hi=limit.copy();phis=np.linspace(-6*np.pi,6*np.pi,phases)
 assert field(lo,a,z,phis,relief).min()>0
 affected=field(hi,a,z,phis,relief)<0
 for _ in range(19):
  mid=(lo+hi)/2;cut=field(mid,a,z,phis,relief)<0
  hi=np.where(cut,mid,hi);lo=np.where(cut,lo,mid)
 radii=np.where(affected,lo,limit).reshape(ns,2*nz)
 return radii,zz

def bandmesh(radii,zz):
 ns,nz=radii.shape;nt=ns*N;vertices=[]
 for k,z in enumerate(zz):
  a=-np.pi/2+np.arange(nt)*2*np.pi/nt;r=np.tile(radii[:,k],N)
  vertices.extend(np.column_stack([r*np.cos(a),r*np.sin(a),np.full(nt,z)]))
 faces=[]
 for k in range(nz-1):
  for i in range(nt):
   j=(i+1)%nt;a=k*nt+i;b=k*nt+j;c=(k+1)*nt+j;d=(k+1)*nt+i;faces.extend([[a,b,c],[a,c,d]])
 b=len(vertices);vertices.extend([[0,0,zz[0]],[0,0,zz[-1]]])
 for i in range(nt):
  j=(i+1)%nt;faces.extend([[b,j,i],[b+1,(nz-1)*nt+i,(nz-1)*nt+j]])
 m=trimesh.Trimesh(vertices,faces,process=True);assert m.is_watertight;return m

def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m

if __name__=='__main__':
 for label,relief in [('nominal',0),('print-clearance',.08)]:
  start=time.time();r,z=grid(48,41,1441,relief)
  np.savez_compressed(O/(label+'.npz'),radii=r,z=z)
  lower=bandmesh(r[:,:41],z[:41]);upper=bandmesh(r[:,41:],z[41:])
  full=trimesh.boolean.union([lower,upper,cyl(3,2.2,3)],engine='manifold')
  full=trimesh.boolean.difference([full,cyl(1.7,12,3)],engine='manifold')
  assert full.is_watertight and full.is_winding_consistent and len(full.split())==1
  lower.export(O/(label+'-lower.stl'));upper.export(O/(label+'-upper.stl'))
  full.export(O/(label+'-assembly.stl'));full.export(O/(label+'-spool.stl'))
  print(label,'min/max radii',r.min(),r.max(),'seconds',time.time()-start,flush=True)
 (O/'parameters.json').write_text(json.dumps(dict(ratio=24,rotation_sign=-1,axis_distance_mm=C,worm_lead_mm=LEAD,worm_root_radius_mm=2.25,worm_tip_radius_mm=3,worm_length_mm=6*SCALE,spool_gap_mm=2,gear_bands_z_mm=[[0,2],[4,6]],lower_phase_override=None,angular_samples_per_tooth=48,z_samples_per_band=41,generating_worm_angle_range_deg=[-1080,1080],generating_pose_count=1441,radial_solver_iterations=19,print_radial_cutter_relief_mm=.08,limitations=['Numerical radial envelope, not exact analytic solution','Finite sampling and STL tessellation','Print relief is an uncalibrated trial value']),indent=2))
