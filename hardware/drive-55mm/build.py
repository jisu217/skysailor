from pathlib import Path
import trimesh,numpy as np,json,base64,zipfile
O=Path(__file__).resolve().parent
def cyl(r,h,x=0,y=0,z=0):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=96);m.apply_translation([x,y,z]);return m
def box(s,p):
 m=trimesh.creation.box(s);m.apply_translation(p);return m
def hor(r,l,x,y,z):
 m=cyl(r,l);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([x,y,z]);return m
def union(ms):return trimesh.boolean.union(ms,engine='manifold')
def diff(m,cs):return trimesh.boolean.difference([m,*cs],engine='manifold')
def rot(m,a):
 m=m.copy();m.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(a),[0,0,1]));return m
def bar(p,q,width,z,h):
 p=np.array(p);q=np.array(q);m=box([np.linalg.norm(q-p),width,h],[0,0,z]);m.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(*(q-p)[::-1]),[0,0,1]));m.apply_translation([*((p+q)/2),0]);return m
gear=trimesh.load(O.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
worm=trimesh.load(O.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
R=18;Y=R-10.05
base=cyl(27.5,2,z=1);bottom_add=[base];bottom_cut=[];top_add=[cyl(5,2,z=6.4)];top_cut=[];meshes={}
for i,a in enumerate([0,120,240]):
 g=gear.copy();g.apply_translation([0,R,1]);meshes[f'gear{i}']=rot(g,a)
 w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,Y],[0,1,0,2],[0,0,0,1]]));meshes[f'worm{i}']=rot(w,a)
 meshes[f'motor{i}']=rot(hor(3,15,-11.5,Y,2),a)
 # Bottom cradle supports the motor below the original plate. Open ends for leads/shaft.
 cradle=box([15,8,4.2],[-11.5,Y,-.1])
 bottom_add.extend([rot(cradle,a),rot(cyl(3.5,5.4,23.5,0,2.7),a)])
 bottom_cut.extend([rot(cyl(8.2,4,0,R,3),a),rot(hor(3.15,17,-11.5,Y,2),a),rot(box([7,6.8,6],[0,Y,1]),a),rot(cyl(1.7,12,23.5,0,3),a)])
 # Upper spider spans each gear axis and the screw pillar, plus a motor clamp arm.
 local=[bar([0,0],[0,R],6,6.4,2),bar([0,R],[23.5,0],6,6.4,2),cyl(3.5,4,0,R,5.4),cyl(3.5,2,23.5,0,6.4),bar([0,0],[-11.5,Y],6,6.4,2),box([10,8,2.6],[-11.5,Y,4.1])]
 top_add.extend(rot(m,a) for m in local)
 top_cut.extend([rot(cyl(1.7,8,0,R,5),a),rot(cyl(1.7,8,23.5,0,5),a),rot(hor(3.15,17,-11.5,Y,2),a),rot(hor(3.4,7,0,Y,2),a)])
base=diff(union(bottom_add),bottom_cut)
# Add gear shafts after cutting the shallow pockets, preserving the 1 mm floor.
base=union([base,*[rot(cyl(1.5,6.6,0,R,3.3),a) for a in [0,120,240]]])
top=diff(union(top_add),top_cut)
meshes.update(base=base,top=top)
checks={}
for name,m in [('base',base),('top',top)]:
 assert m.is_watertight and m.is_winding_consistent and len(m.split())==1,(name,len(m.split()))
 printable=m.copy()
 if name=='top':printable.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 printable.apply_translation([0,0,-printable.bounds[0,2]]);printable.export(O/(name+'-55mm.stl'))
names=list(meshes)
for i,a in enumerate(names):
 for b in names[i+1:]:
  ma,mb=meshes[a],meshes[b]
  if np.any(ma.bounds[1]<mb.bounds[0]) or np.any(mb.bounds[1]<ma.bounds[0]):continue
  inter=trimesh.boolean.intersection([ma,mb],engine='manifold');v=float(inter.volume) if len(inter.faces) else 0
  checks[a+'/'+b]=v
  assert v<.001,(a,b,v)
data={}
for name,m in meshes.items():
 sm=m.simplify_quadric_decimation(face_count=1600) if len(m.faces)>1600 else m
 data[name]={k:base64.b64encode(np.asarray(v,dtype=t).tobytes()).decode() for k,v,t in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/drive-55mm.html')
target.write_text((O/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
spec=dict(diameter_mm=55,gear_radius_mm=18,gear_endplay_mm=.4,shaft_diameter_mm=3,top_shaft_bore_mm=3.4,screw_holes_mm=3.4,screw_count=3,fastener='M3 through bolts + nuts, nominal M3x12; verify actual hardware',motor_cradle_bore_mm=6.3,motor_fit='0.15 mm radial allowance; tape shim may be required',base_plate_thickness_mm=2,top_plate_thickness_mm=2,assembly_z_bounds_mm=[-2.2,7.4],static_intersections_mm3=checks,spool='not yet designed; upper bridges must be revised for spool clearance')
(O/'dimensions.json').write_text(json.dumps(spec,indent=2))
with zipfile.ZipFile(O/'drive-55mm-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in ['base-55mm.stl','top-55mm.stl','dimensions.json']:z.write(O/f,f)
 z.write(O.parent/'gear-75pct/wheel-24t-75pct-2mm.stl','gear-print-3.stl');z.write(O.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl','worm-print-3.stl')
print('PASS',len(checks),'pair checks; viewer',target.stat().st_size,'bytes')
