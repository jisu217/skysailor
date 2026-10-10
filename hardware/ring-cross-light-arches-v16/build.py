from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-light-wall-v15'
co=math.sqrt(130**2-100**2);ci=math.sqrt(130**2-94**2)
# Leave 2mm in vertical section along both arch edges, and solid joint zones.
cutters=[]
for sign in (-1,1):
 x=np.linspace(12,66,1025)
 lower=2+np.sqrt(130**2-x*x)-ci+2
 upper=2+np.sqrt(130**2-x*x)-co-2
 poly=Polygon(np.vstack((np.column_stack((x,lower)),np.column_stack((x[::-1],upper[::-1])))))
 poly=poly.buffer(-.65,quad_segs=32).buffer(.65,quad_segs=32)
 m=trimesh.creation.extrude_polygon(poly,height=4,engine='earcut')
 m.apply_transform(np.array([[sign,0,0,0],[0,0,-1,2],[0,1,0,0],[0,0,0,1]]))
 if sign<0:m.invert()
 # trimesh handles reflection winding; ensure positive volume.
 if m.volume<0:m.invert()
 cutters.append(m)
parts=[];old_volume=0
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True);parts.append(base)
shutil.copy2(src/'ring-print.stl',out/'ring-print.stl')
for label,angle in [('A-top-slot',0),('B-bottom-slot',math.pi/2)]:
 m=trimesh.load(src/f'arch-{label}-assembled.stl',force='mesh');m.process(validate=True);old_volume+=m.volume
 cuts=[]
 for cut in cutters:
  c=cut.copy();c.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));cuts.append(c)
 m=trimesh.boolean.difference([m]+cuts,engine='manifold')
 assert m.is_watertight and m.is_volume and len(m.split())==1
 m.export(out/f'arch-{label}-assembled.stl');parts.append(m)
 flat=m.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(-angle,[0,0,1]));flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/f'arch-{label}-print.stl')
mid=trimesh.load(src/'mid-ring-assembled.stl',force='mesh');mid.process(validate=True);parts.append(mid)
for name in ['mid-ring-assembled.stl','mid-ring-print.stl']:shutil.copy2(src/name,out/name)
saved=old_volume-parts[1].volume-parts[2].volume;total=sum(m.volume for m in parts)
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>경량화 · 아치 곡선 슬롯 추가</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>아치당 슬롯 2개 · 전체 {total/1000:.2f}cm³ · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>각 아치에 곡선을 따르는 슬롯 2개를 추가했습니다.<br>안팎 가장자리는 수직 단면 기준 2mm씩 남겼습니다.<br>중앙 교차 홈, 위 링 받침, 양끝 접합부는 유지했습니다.<br>아래 링 바닥/경사 벽 슬롯도 유지했습니다.<br>전체 삼각형 표시, 스무딩 없음. 강성은 실물 시험이 필요합니다.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html)
(out/'preview.html').write_text(html)
spec={'arch_slots_each':2,'arch_edge_vertical_margin_mm':2,'slot_x_extent_mm':[12,66],'total_cm3':total/1000,'additional_saved_cm3':saved/1000,'original_reduction_percent':(1-total/20416.692135655705)*100,'connected_arches':True,'smooth_shading':False,'decimated':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
