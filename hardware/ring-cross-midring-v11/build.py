from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-arch-eight-feet-v10'
def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m
h=13.75
mid=trimesh.creation.revolve([[82,h],[86,h],[86,h+2],[82,h+2],[82,h]],sections=2048)
# Inner-edge notches leave outer ligaments of 1.9 mm.
cutters=[]
for ang in np.arange(4)*math.pi/2:
 m=box([6.1,2.2,4],[81.05,0,h+1]);m.apply_transform(trimesh.transformations.rotation_matrix(ang,[0,0,1]));cutters.append(m)
mid=trimesh.boolean.difference([mid]+cutters,engine='manifold')
arches=[]
for label in ['A-top-slot','B-bottom-slot']:
 m=trimesh.load(src/f'arch-{label}-assembled.stl',force='mesh');m.process(validate=True)
 cuts=[]
 ang=0 if label.startswith('A') else math.pi/2
 for sign in (-1,1):
  c=box([2.3,6,2.2],[sign*85.05,0,h+1]);c.apply_transform(trimesh.transformations.rotation_matrix(ang,[0,0,1]));cuts.append(c)
 m=trimesh.boolean.difference([m]+cuts,engine='manifold')
 assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/f'arch-{label}-assembled.stl');arches.append(m)
 flat=m.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(-ang,[0,0,1]));flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/f'arch-{label}-print.stl')
assert mid.is_volume and mid.is_watertight and len(mid.split())==1
mid.export(out/'mid-ring-assembled.stl');flat=mid.copy();flat.apply_translation([0,0,-h]);flat.export(out/'mid-ring-print.stl')
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True)
shutil.copy2(src/'ring-print.stl',out/'ring-print.stl')
def overlap(a,b):
 m=trimesh.boolean.intersection([a,b],engine='manifold');return float(abs(m.volume)) if len(m.faces) else 0
parts=[base]+arches+[mid]
collisions=[]
for i in range(4):
 for j in range(i+1,4):
  v=overlap(parts[i],parts[j]);assert v<.001,(i,j,v);collisions.append(v)
# Explicitly test straight-down installation over the fixed arches.
path=[]
for dz in [.1,.5,1,2,4,8,16,24,36]:
 raised=mid.copy();raised.apply_translation([0,0,dz]);path.append({'offset_mm':dz,'overlap_mm3':sum(overlap(raised,a) for a in arches)})
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 + Ø172 중간 링 · 맞춤 검토</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>중간 링 Ø172 / Ø164 × 2mm · 바닥 높이 13.75mm · {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>보라: 중간 링. 안쪽에서 깊이 2.1mm, 폭 2.2mm 홈 4개.<br>아치에는 바깥쪽 반턱에 맞춰 높이 2.2mm 홈을 냈습니다.<br>완성 위치에서 부품 간 겹침 없음.<br>고정된 십자 아치 위에서 링을 수직으로 내리는 경로는 간섭이 있습니다. 조립 경로가 확보된 출력 확정본은 아닙니다.<br>분해 표시는 부품 구분용이며 실제 조립 경로를 뜻하지 않습니다.</p></details>',html)
html=html.replace('<a href="ring-print.stl" download>링 STL</a>','<a href="ring-print.stl" download>아래 링 STL</a><a href="mid-ring-print.stl" download>중간 링 STL</a>')
html=html.replace('const mats=[0x85c9de,0xf0b66b,0x9fdaa6]','const mats=[0x85c9de,0xf0b66b,0x9fdaa6,0xc59aef]')
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html)
html=html.replace('i<3;i++','i<4;i++').replace('parts[2].position.z=exploded?30:0;','parts[2].position.z=exploded?30:0;parts[3].position.z=exploded?50:0;')
(out/'preview.html').write_text(html)
spec={'mid_ring_od_mm':172,'mid_ring_id_mm':164,'thickness_mm':2,'bottom_z_mm':h,'ring_notch_width_mm':2.2,'ring_notch_depth_mm':2.1,'arch_notch_height_mm':2.2,'assembled_intersections_mm3':collisions,'vertical_insertion_test':path,'assembly_path_verified':False,'render_triangles':len(assembly.faces),'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
print(json.dumps(spec,indent=2))
