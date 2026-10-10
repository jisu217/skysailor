from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-cross-light-top-v18'
co=math.sqrt(16900-10000);ci=math.sqrt(16900-94**2)
h=2+math.sqrt(16900-71**2)-co-.40413635830093

def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m

def difference(m,c):return trimesh.boolean.difference([m]+c,engine='manifold')
z=np.unique(np.r_[np.linspace(h,h+2,257),h+.40413635830093]);ro=np.minimum(71,np.sqrt(16900-(co+z-2)**2))
mid=trimesh.creation.revolve(np.vstack(([[67,h]],np.column_stack((ro,z)),[[67,h+2],[67,h]])),sections=2048)
cuts=[]
for angle in np.arange(4)*math.pi/2:
 c=box([6.1,2.2,4],[66.05,0,h+1]);c.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));cuts.append(c)
mid=difference(mid,cuts)
z=np.linspace(h-.001,h+1.2,129);ro=np.minimum(71,np.sqrt(16900-(co+z-2)**2))-.9
cavity=trimesh.creation.revolve(np.vstack(([[67.9,z[0]]],np.column_stack((ro,z)),[[67.9,z[-1]],[67.9,z[0]]])),sections=2048)
pockets=[]
for k in range(8):
 t=np.linspace(math.radians(k*45+10),math.radians(k*45+35),257)
 xy=np.vstack((np.column_stack((75*np.cos(t),75*np.sin(t))),np.column_stack((65*np.cos(t[::-1]),65*np.sin(t[::-1])))))
 c=trimesh.creation.extrude_polygon(Polygon(xy),height=4,engine='earcut');c.apply_translation([0,0,h-1]);pockets.append(trimesh.boolean.intersection([cavity,c],engine='manifold'))
mid=difference(mid,pockets)
# Rebuild shafts from pre-seat source, so old lower ledges disappear.
slot_cuts=[]
for sign in (-1,1):
 x=np.linspace(12,66,1025);low=2+np.sqrt(16900-x*x)-ci+2;up=2+np.sqrt(16900-x*x)-co-2
 poly=Polygon(np.vstack((np.column_stack((x,low)),np.column_stack((x[::-1],up[::-1]))))).buffer(-.65,quad_segs=32).buffer(.65,quad_segs=32)
 c=trimesh.creation.extrude_polygon(poly,height=4,engine='earcut');c.apply_transform(np.array([[sign,0,0,0],[0,0,-1,2],[0,1,0,0],[0,0,0,1]]));slot_cuts.append(c)
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True);parts=[base]
shutil.copy2(src/'ring-print.stl',out/'ring-print.stl')
for label,angle in [('A-top-slot',0),('B-bottom-slot',math.pi/2)]:
 m=trimesh.load(root/'ring-cross-arch-eight-feet-v10'/f'arch-{label}-assembled.stl',force='mesh');m.process(validate=True)
 rot=trimesh.transformations.rotation_matrix(angle,[0,0,1]);cuts=[]
 for original in slot_cuts:
  c=original.copy();c.apply_transform(rot);cuts.append(c)
 for sign in (-1,1):
  c=box([40,6,50],[sign*88.9,0,h+25]);c.apply_transform(rot);cuts.append(c)
 m=difference(m,cuts);assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/f'arch-{label}-assembled.stl');parts.append(m)
 flat=m.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(-angle,[0,0,1]));flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/f'arch-{label}-print.stl')
assert mid.is_volume and mid.is_watertight and len(mid.split())==1
mid.export(out/'mid-ring-assembled.stl');flat=mid.copy();flat.apply_translation([0,0,-h]);flat.export(out/'mid-ring-print.stl');parts.append(mid)
for dz in (0,.1,.5,1,2,4,8,16,30):
 raised=mid.copy();raised.apply_translation([0,0,dz])
 for arch in parts[1:3]:
  hit=trimesh.boolean.intersection([raised,arch],engine='manifold');assert not len(hit.faces) or abs(hit.volume)<.001
assembly=trimesh.util.concatenate(parts);total=sum(m.volume for m in parts)/1000
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>위 링 축소 · Ø142 / Ø134</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>위 링 바닥 높이 {h:.3f}mm · 두께 2mm · 전체 {total:.2f}cm³</small>',html)
html=re.sub(r'<details>.*?</details>',f'<details><summary>ⓘ</summary><p>위 링 외경/내경을 각각 10mm 줄였습니다.<br>바닥 높이 {h:.3f}mm. 아치에 맞춘 바깥 곡면, ㄴ자 받침, 끼움 홈 4개를 다시 계산했습니다.<br>밑면 슬롯 8개, 깊이 1.2mm, 윗면 0.8mm 유지.<br>아래 링과 아치 경량화 슬롯 유지. 기존 낮은 받침턱은 복원했습니다.<br>전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html);(out/'preview.html').write_text(html)
spec={'od_mm':142,'id_mm':134,'height_mm':2,'bottom_z_mm':h,'raised_mm':h-24,'upper_od_mm':2*math.sqrt(16900-(co+h)**2),'top_ring_cm3':mid.volume/1000,'total_cm3':total,'insertion_checked':True,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
