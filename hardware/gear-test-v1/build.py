from pathlib import Path
import numpy as np, trimesh, json, base64, shutil
O=Path(__file__).resolve().parent
N=24; P=2.5; C=N*P/(2*np.pi)+3.5; H=9

def box(size,pos):
 m=trimesh.creation.box(size);m.apply_translation(pos);return m

def cyl(r,h,pos):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=96);m.apply_translation(pos);return m

def union(ms):return trimesh.boolean.union(ms,engine='manifold')
def diff(a,b):return trimesh.boolean.difference([a,b],engine='manifold')

# Numerical hobbing envelope of the actual v2 axial profile, with 0.15mm cutter relief.
# One tooth sector is sampled and repeated, using an extended hob to avoid end artifacts.
ns=48;nz=41;nr=160
angles=-np.pi/2+np.arange(ns)*2*np.pi/N/ns
zz=np.linspace(-2,2,nz);rr=np.linspace(8.1,N*P/(2*np.pi)+1,nr)
a,z,r=np.meshgrid(angles,zz,rr,indexing='ij');cut=np.zeros(a.shape,dtype=bool)
for phi in np.linspace(-4*np.pi,4*np.pi,321):
 psi=-phi/N;x=r*np.cos(a+psi);y=r*np.sin(a+psi)+C
 q=np.arctan2(z,y)-phi
 phase=(x+4-P*q/(2*np.pi)+P/2)%P-P/2
 wr=3+np.clip(1.15-np.abs(phase),0,1)+.15
 cut |= np.hypot(y,z)<wr
first=np.argmax(cut,axis=2)
radii=np.where(cut.any(axis=2),rr[np.maximum(first-1,0)],rr[-1])
nt=N*ns;verts=[]
for k,zk in enumerate(zz):
 for i in range(nt):
  t=-np.pi/2+i*2*np.pi/nt; rad=radii[i%ns,k];verts.append([rad*np.cos(t),rad*np.sin(t),zk+2])
outer=len(verts)
for zk in [0,4]:
 for i in range(nt):
  t=-np.pi/2+i*2*np.pi/nt;verts.append([1.8*np.cos(t),1.8*np.sin(t),zk])
f=[]
for k in range(nz-1):
 for i in range(nt):
  j=(i+1)%nt;a=k*nt+i;b=k*nt+j;c=(k+1)*nt+j;d=(k+1)*nt+i;f.extend([[a,b,c],[a,c,d]])
for i in range(nt):
 j=(i+1)%nt;bi=outer+i;bj=outer+j;ti=bi+nt;tj=bj+nt;a=(nz-1)*nt+i;b=(nz-1)*nt+j
 f.extend([[bi,ti,tj],[bi,tj,bj],[i,bi,bj],[i,bj,j],[a,b,tj],[a,tj,ti]])
wheel=trimesh.Trimesh(verts,f,process=True)
# Base top z2, wheel shoulder top z7; wheel rests z7, centre z9.
base=union([box([56,44,2],[-7,-4,1]),cyl(3,5,[0,0,4.5]),cyl(1.5,7,[0,0,9.5]),
 box([2,18,2],[-26,-C,3]),box([2,18,2],[8,-C,3])])
# Motor saddle travels along y between rails. Tape around exposed motor/saddle secures it.
car=union([box([31,10,1.6],[-9,-C,2.8]),box([15,6.8,5.6],[-12.5,-C,6.2])])
motorcut=cyl(3.2,17,[0,0,0]);motorcut.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));motorcut.apply_translation([-12.5,-C,H])
car=diff(car,motorcut)
# Two top-open transverse tape grooves allow bands around motor and saddle.
for x in [-17,-8]: car=diff(car,box([2,12,0.6],[x,-C,2.25]))
# Integral base rails constrain x; removable tapered side key locks carriage against left rail.
# 0.3 to 1.1mm thickness along travel direction. A shallow 0.1mm nose easing.
wverts=[[-.15,-8,0],[.15,-8,0],[.55,8,0],[-.55,8,0],[-.15,-8,1.6],[.15,-8,1.6],[.55,8,1.6],[-.55,8,1.6]]
wf=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
key=trimesh.Trimesh(wverts,wf,process=True);key=union([key,box([4,2,1.6],[0,9,.8])])
# Optional retention washer; its bore is a separate fit trial, not the motor bore.
cap=diff(cyl(3,1.2,[0,0,.6]),cyl(1.6,3,[0,0,.6]))
worm=trimesh.load(O.parent/'worm-v2-short/worm-v2-short-bore-1.20mm.stl')
parts={'base':base,'motor-saddle':car,'wheel-24t':wheel,'locking-key':key,'retainer':cap,'worm-1.20mm':worm}
checks={}
for name,m in parts.items():
 assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
 assert len(m.split())==1,name
 printing=m.copy();printing.apply_translation(-printing.bounds[0]);printing.export(O/(name+'.stl'))
 checks[name]={'volume_mm3':float(m.volume),'size_mm':m.extents.tolist(),'watertight':True}
# Verify static assembly clearances with exact mesh Boolean intersections (sampling-derived wheel).
wa=wheel.copy();wa.apply_translation([0,0,7]);wo=worm.copy();wo.apply_transform(np.array([[0,0,1,-4],[1,0,0,-C],[0,1,0,H],[0,0,0,1]]))
for name,a,b in [('wheel-base',wa,base),('worm-wheel',wo,wa),('worm-saddle',wo,car),('wheel-saddle',wa,car),('saddle-base',car,base)]:
 inter=trimesh.boolean.intersection([a,b],engine='manifold');volume=0 if inter is None else float(inter.volume);checks[name]={'intersection_mm3':volume};assert volume<.001,(name,volume)
# Rotation sample intersections: kinematic relation wheel=-worm/24.
worst=0
for phi in np.linspace(0,2*np.pi,13)[:-1]:
 w=worm.copy();w.apply_transform(trimesh.transformations.rotation_matrix(phi,[0,0,1]));w.apply_transform(np.array([[0,0,1,-4],[1,0,0,-C],[0,1,0,H],[0,0,0,1]]))
 g=wa.copy();g.apply_transform(trimesh.transformations.rotation_matrix(-phi/N,[0,0,1]));v=float(trimesh.boolean.intersection([w,g],engine='manifold').volume);worst=max(worst,v)
checks['rotation-12-poses']={'maximum_intersection_mm3':worst};assert worst<.01,worst
(O/'validation.json').write_text(json.dumps(checks,indent=2))
(O/'dimensions.json').write_text(json.dumps({'wheel_teeth':N,'ratio':'24:1','centre_distance_mm':C,'worm_axis_height_mm':H,'motor_body_mm':[6,15],'motor_bore_design_mm':1.2,'wheel_bore_design_mm':3.6,'shaft_diameter_mm':3,'wheel_thickness_mm':4,'hob_clearance_mm':.15,'carriage_travel_recommended_mm':[-1.5,1.5],'status':'Numerically generated experimental tooth geometry; hand-fit verification required'},indent=2))
# Compact indexed mesh geometry for the interactive assembly, same parts as STL.
assembled={'base':base,'motor-saddle':car,'wheel-24t':wa,'worm-1.20mm':wo}
ca=cap.copy();ca.apply_translation([0,0,11.4]);assembled['retainer']=ca
ke=key.copy();ke.apply_translation([6.75,-C,2]);assembled['locking-key']=ke
motor=cyl(3,15,[0,0,0]);motor.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));motor.apply_translation([-12.5,-C,H]);assembled['motor-reference']=motor
meshes={}
for name,m in assembled.items():
 sm=m.simplify_quadric_decimation(face_count=5000) if len(m.faces)>5000 else m
 meshes[name]={'v':base64.b64encode(np.asarray(sm.vertices,dtype='<f4').tobytes()).decode(),'f':base64.b64encode(np.asarray(sm.faces,dtype='<u4').tobytes()).decode()}
(O/'viewer-meshes.json').write_text(json.dumps(meshes,separators=(',',':')))
print('Done',checks['rotation-12-poses'], 'viewer bytes', (O/'viewer-meshes.json').stat().st_size)
