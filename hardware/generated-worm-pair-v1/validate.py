from pathlib import Path
import numpy as np,trimesh,json
from generate import clearance,grid,field
O=Path(__file__).resolve().parent
PHIS=(np.arange(96)+.37)*2*np.pi/96  # independent, offset from generating samples

def transformed(v,angle):
 c,s=np.cos(angle),np.sin(angle);return np.column_stack([c*v[:,0]-s*v[:,1],s*v[:,0]+c*v[:,1],v[:,2]])
def distances(points,phi):return clearance(points[:,0],points[:,1],points[:,2],phi)
def nearpoints(vertices,phi,delta=0):
 v=transformed(vertices,-phi/24+delta)
 return v[(np.abs(v[:,0])<2.98)&(v[:,1]<-4)&(np.hypot(v[:,0],v[:,1])>4)]
report={}
for label in ['nominal','print-clearance']:
 byband={}
 for band in ['lower','upper']:
  mesh=trimesh.load(O/(label+'-'+band+'.stl'));mins=[];contactcounts=[];residuals=[];levers=[]
  for phi in PHIS:
   p=nearpoints(mesh.vertices,phi);d=distances(p,phi);mins.append(float(d.min()));q=p[(d>=-.01)&(d<.025)]
   theta=np.arctan2(q[:,2]-3.5,q[:,1]+8.5)-phi
   phase=(q[:,0]+3-1.875*theta/(2*np.pi)+.9375)%1.875-.9375
   q=q[(np.abs(phase)>.13)&(np.abs(phase)<.84)]
   contactcounts.append(len(q))
   if len(q):
    eps=1e-5;grad=[]
    for axis in range(3):
     e=np.zeros(3);e[axis]=eps;grad.append((distances(q+e,phi)-distances(q-e,phi))/(2*eps))
    grad=np.array(grad).T;grad/=np.linalg.norm(grad,axis=1)[:,None]
    vw=np.column_stack([np.zeros(len(q)),-(q[:,2]-3.5),q[:,1]+8.5]);vg=np.column_stack([q[:,1]/24,-q[:,0]/24,np.zeros(len(q))]);rel=vg-vw
    residuals.extend((np.abs(np.sum(grad*rel,axis=1))/np.linalg.norm(rel,axis=1)).tolist())
    levers.extend((q[:,0]*grad[:,1]-q[:,1]*grad[:,0]).tolist())
  byband[band]=dict(minimum_radial_clearance_mm=min(mins),maximum_nearest_radial_clearance_mm=max(mins),poses_with_near_flank_samples=sum(n>0 for n in contactcounts),pose_count=96,near_flank_threshold_mm=.025,relative_normal_velocity_residual_p95=float(np.percentile(residuals,95)) if residuals else None,contact_normal_torque_arm_range_mm=[min(levers),max(levers)] if levers else None)
 report[label]=byband
# Angular free travel to a 0.005 mm penetration threshold; geometric proxy only.
mesh=trimesh.load(O/'print-clearance-assembly.stl');travel=[]
for phi in PHIS[::8]:
 pair=[]
 for sign in [-1,1]:
  lo=0.;hi=np.deg2rad(7.5)
  if distances(nearpoints(mesh.vertices,phi,sign*hi),phi).min()>=-.005:pair.append(None);continue
  for _ in range(15):
   mid=(lo+hi)/2
   if distances(nearpoints(mesh.vertices,phi,sign*mid),phi).min()<-.005:hi=mid
   else:lo=mid
  pair.append(float(np.rad2deg(hi)))
 travel.append(pair)
report['print_free_rotation_deg_to_penetration_0_005mm']=travel
# Verify radial representation assumption on a coarse grid: once removed along a ray, it stays removed.
sample=np.load(O/'nominal.npz');aa,zz=np.meshgrid(-np.pi/2+np.arange(12)*2*np.pi/24/12,np.r_[np.linspace(0,2,9),np.linspace(5,7,9)],indexing='ij');aa=aa.ravel();zz=zz.ravel();states=[]
for r in np.linspace(3,7.912,36):states.append(field(np.full_like(aa,r),aa,zz,np.linspace(-6*np.pi,6*np.pi,721),0)<0)
states=np.array(states);report['radial_nonmonotone_transitions']=int(np.count_nonzero(states[:-1]&~states[1:]))
(O/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
