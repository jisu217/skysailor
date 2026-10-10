from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;root=out.parent
base=trimesh.load(root/'ring-380-floor-1mm/frame.stl',force='mesh')
original=trimesh.load(root/'ring-380-floor-1mm/linked-slider-print.stl',force='mesh');original.apply_translation([0,0,-1.2])
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Retain contour shoes, replace the long lower connector with dropped connectors.
shoes=[]
for x in [-25,25]:
 shoe=trimesh.boolean.intersection([original,box([12,12,12],[x,0,2])],engine='manifold');shoes.append(shoe)
def make_link(drop):
 parts=[m.copy() for m in shoes]
 # Original connection plate z=-1.2..-0.2, shifted down by drop.
 parts.append(box([62,8.4,1],[0,0,-.7-drop]))
 for x in [-25,25]:
  for y in [-3.7,3.7]:
   parts.append(box([12,1,drop+.2],[x,y,-1.1-drop/2]))
 m=trimesh.boolean.union(parts,engine='manifold')
 assert m.is_volume and m.is_watertight and len(m.split())==1
 return m
xpart=make_link(2)
ypart=make_link(4);ypart.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1]))
for dx in [-14,0,14]:
 for dy in [-14,0,14]:
  xx=xpart.copy();xx.apply_translation([dx,0,0]);yy=ypart.copy();yy.apply_translation([0,dy,0])
  for a,b in [(base,xx),(base,yy),(xx,yy)]:
   h=trimesh.boolean.intersection([a,b],engine='manifold');assert h.is_empty or abs(h.volume)<1e-4,(dx,dy,h.volume)
meshes=[base,xpart,ypart]
for name,m in zip(['frame','x-slider','y-slider'],meshes):m.export(out/(name+'.stl'))
assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(root/'ring-380-y-frame-only/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>같은 형태의 XY 연결 슬라이더</h1>',s)
s=re.sub(r'<title>.*?</title>','<title>XY 연결판 높이 조정</title>',s)
s=re.sub(r'<small>.*?</small>','<small>두 축 슬라이더 중심 간격 50mm · X 연결판 2mm 하강 · Y 연결판은 X보다 2mm 아래 · 판 두께 1mm</small>',s)
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
s=s.replace('min="-15" max="15"','min="-14" max="14"')
s=s.replace('판 두께 1mm</small>','판 두께 1mm · 이동 각 ±14mm</small>')
(out/'preview.html').write_text(s)
print('Verified matching X/Y link shapes, centers 50mm, plate center Z -2.7/-4.7mm, collision-free at 9 travel positions.')
