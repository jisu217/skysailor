from pathlib import Path
import numpy as np,trimesh,json,base64
out=Path(__file__).resolve().parent
def cyl(r,h,x=0,y=0,z=0):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=80);m.apply_translation([x,y,z+h/2]);return m
def union(ms):return trimesh.boolean.union(ms,engine='manifold')
def diff(a,bs):return trimesh.boolean.difference([a,*bs],engine='manifold')
centres=[(23*np.cos(np.deg2rad(a)),23*np.sin(np.deg2rad(a))) for a in [90,210,330]]
plate=trimesh.convex.convex_hull(np.vstack([cyl(10,2,x,y).vertices for x,y in centres]))
top=plate.copy();top.apply_translation([0,0,11.6])
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
# Gear is the lower flange; added upper flange and winding core.
spool=union([gear,cyl(4,5.2,z=1.9),cyl(6,1,z=7)])
spool=diff(spool,[cyl(1.8,12,z=-1)])
spool.export(out/'gear-spool.stl')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
meshes={};cuts=[];supports=[];holes=[]
for i,a in enumerate([0,120,240]):
 rot=trimesh.transformations.rotation_matrix(np.deg2rad(a),[0,0,1])
 x,y=centres[i]
 supports.extend([cyl(2.6,1.2,x,y,2),cyl(1.5,10.6,x,y,2)])
 holes.append(cyl(1.7,4,x,y,11))
 g=spool.copy();g.apply_translation([0,23,3.2]);g.apply_transform(rot);meshes[f'gear{i}']=g
 w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,12.95],[0,1,0,4.2],[0,0,0,1]]));w.apply_transform(rot);meshes[f'worm{i}']=w
 motor=cyl(3,15);motor.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));motor.apply_translation([-19,12.95,4.2]);motor.apply_transform(rot);meshes[f'motor{i}']=motor
 cut=trimesh.creation.box([23,6.8,4]);cut.apply_translation([-7.5,12.95,3.05]);cut.apply_transform(rot);cuts.append(cut)
 # Central spacers keep cover above the rotating upper flanges.
 t=np.deg2rad(a+90);supports.append(cyl(2,9.6,5*np.cos(t),5*np.sin(t),2))
base=union([diff(plate,cuts),*supports]);top=diff(top,holes)
meshes['base']=base;meshes['top']=top
for name,m in [('base',base),('top',top)]:
 assert m.is_watertight and len(m.split())==1
 m.export(out/(name+'.stl'))
checks={}
for a in ['base','top']:
 for b,m in meshes.items():
  if b in ['base','top']:continue
  inter=trimesh.boolean.intersection([meshes[a],m],engine='manifold');v=float(inter.volume) if len(inter.faces) else 0
  checks[a+'/'+b]=v
  assert v<.001,(a,b,v)
data={}
for name,m in meshes.items():
 sm=m.simplify_quadric_decimation(face_count=1800) if len(m.faces)>1800 else m
 data[name]={k:base64.b64encode(np.asarray(v,dtype=t).tobytes()).decode() for k,v,t in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/triangle-winch.html')
target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
(out/'dimensions.json').write_text(json.dumps(dict(plate_bounds_mm=plate.extents.tolist(),plate_thickness_mm=2,overall_height_mm=13.6,spool_core_diameter_mm=8,spool_winding_width_mm=5,upper_flange_diameter_mm=12,axial_clearance_mm=.4,shaft_diameter_mm=3,motor_mounts_and_cover_fasteners_pending=True,checks=checks),indent=2))
print('Validated plate clearances;',target.stat().st_size,'bytes',plate.extents)
