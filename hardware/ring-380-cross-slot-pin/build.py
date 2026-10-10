from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;root=out.parent
base=trimesh.load(root/'ring-380-floor-1mm/frame.stl',force='mesh')
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
linked=trimesh.load(root/'ring-380-floor-1mm/linked-slider-print.stl',force='mesh');linked.apply_translation([0,0,-1.2])
shoe=trimesh.boolean.intersection([linked,box([12,12,12],[25,0,2])],engine='manifold');shoe.apply_translation([-25,0,0])
def axis_frame(spacing,z,rotate=False):
 parts=[]
 for x in [-spacing,spacing]:
  m=shoe.copy();m.apply_translation([x,0,0]);parts.append(m)
  for y in [-3.7,3.7]:parts.append(box([12,1,-z],[x,y,(z-1.2)/2]))
  parts.append(box([12,54,1],[x,0,z]))
 for y in [-26,26]:parts.append(box([spacing*2+12,2,1],[0,y,z]))
 parts.append(box([8.4,54,1],[0,0,z]))
 m=trimesh.boolean.union(parts,engine='manifold')
 cuts=[box([3,37,1.4],[0,0,z])]
 for y in [-18.5,18.5]:
  c=trimesh.creation.cylinder(radius=1.5,height=1.4,sections=96);c.apply_translation([0,y,z]);cuts.append(c)
 cutter=trimesh.boolean.union(cuts,engine='manifold');m=trimesh.boolean.difference([m,cutter],engine='manifold')
 if rotate:m.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1]))
 return m
xpart=axis_frame(35,-2.7)
ypart=axis_frame(55,-5.7,True)
pin=trimesh.creation.cylinder(radius=1.3,height=4.7,sections=96);pin.apply_translation([0,0,-4.2])
carrier=trimesh.boolean.union([pin,box([10,10,1],[0,0,-1.5]),box([10,10,1],[0,0,-6.9])],engine='manifold')
for m in [xpart,ypart,carrier]:assert m.is_volume and m.is_watertight and len(m.split())==1
for dx in [-14,0,14]:
 for dy in [-14,0,14]:
  moving=[]
  for m,p in [(xpart,[dx,0,0]),(ypart,[0,dy,0]),(carrier,[dx,dy,0])]:
   q=m.copy();q.apply_translation(p);moving.append(q)
  for i,a in enumerate(moving):
   for b in [base]+moving[:i]:
    hit=trimesh.boolean.intersection([a,b],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-4,(dx,dy,i,hit.volume)
meshes=[base,xpart,ypart,carrier];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
for name,m in zip(['frame','x-stage','y-stage','pin-carrier'],meshes):m.export(out/(name+'.stl'))
s=(root/'ring-380-cross-guided-xy/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>직각 교차 슬롯 · 중앙 핀 XY</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>X/Y 이동에 직각인 슬롯 40 × 3mm · 핀 Ø2.6mm · 위아래 판 10 × 10 × 1mm · 이동 ±14mm</small>',s)
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
s=s.replace('min="-15" max="15"','min="-14" max="14"')
(out/'preview.html').write_text(s)
print('Cross-slot pin mechanism: 9 sampled XY positions collision-free. Carrier rotation remains unconstrained.')
