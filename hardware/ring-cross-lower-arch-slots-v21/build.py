from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-adjusted-arch-slots-v20'
co=math.sqrt(16900-10000);ci=math.sqrt(16900-94**2)
# Lower slots start beyond the upper-ring ledge and stop before the feet.
# x=77..89; retain 2mm vertical material along both curved edges.
cutters=[]
for sign in (-1,1):
 x=np.linspace(77,89,513);lo=2+np.sqrt(16900-x*x)-ci+2;hi=2+np.sqrt(16900-x*x)-co-2
 poly=Polygon(np.vstack((np.column_stack((x,lo)),np.column_stack((x[::-1],hi[::-1]))))).buffer(-.65,quad_segs=32).buffer(.65,quad_segs=32)
 c=trimesh.creation.extrude_polygon(poly,height=4,engine='earcut');c.apply_transform(np.array([[sign,0,0,0],[0,0,-1,2],[0,1,0,0],[0,0,0,1]]));cutters.append(c)
parts=[];base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True);parts.append(base)
old_arch=0
for label,angle in [('A-top-slot',0),('B-bottom-slot',math.pi/2)]:
 m=trimesh.load(src/f'arch-{label}-assembled.stl',force='mesh');m.process(validate=True);old_arch+=m.volume
 cuts=[]
 for original in cutters:
  c=original.copy();c.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));cuts.append(c)
 m=trimesh.boolean.difference([m]+cuts,engine='manifold')
 assert m.is_volume and m.is_watertight and len(m.split())==1
 parts.append(m);m.export(out/f'arch-{label}-assembled.stl')
 flat=m.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(-angle,[0,0,1]));flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/f'arch-{label}-print.stl')
mid=trimesh.load(src/'mid-ring-assembled.stl',force='mesh');mid.process(validate=True);parts.append(mid)
for name in ['ring-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:shutil.copy2(src/name,out/name)
saved=old_arch-sum(m.volume for m in parts[1:3]);total=sum(m.volume for m in parts)/1000
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>아치 경량화 · 중간 링 아래 슬롯 추가</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>아치 아래 슬롯 4개 추가 · 전체 {total:.2f}cm³ · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>중간 링 아래 아치 구간에 슬롯을 하나씩 추가했습니다. 아치당 아래 슬롯 2개, 총 4개 추가.<br>아래 슬롯은 중심에서 수평거리 77~89mm 구간. 안팎 가장자리는 수직 기준 2mm씩 남겼습니다.<br>링 받침과 맨 아래 발 주변을 유지했습니다.<br>기존 위쪽 슬롯과 모든 링은 유지. 전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html);(out/'preview.html').write_text(html)
spec={'lower_slots_added':4,'lower_slot_x_mm':[77,89],'vertical_edge_margin_mm':2,'additional_saved_cm3':saved/1000,'total_cm3':total,'arch_connected_and_watertight':True,'smooth_shading':False,'decimated':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
