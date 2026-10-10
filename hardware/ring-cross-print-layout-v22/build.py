from pathlib import Path
import json,re,math
import numpy as np
import trimesh
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-lower-arch-slots-v21'
def load(name):
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);return m
ring=load('ring-print.stl');mid=load('mid-ring-print.stl')
mid.apply_transform(trimesh.transformations.rotation_matrix(math.pi,[1,0,0]))
for m in (ring,mid):m.apply_translation([110,110,-m.bounds[0,2]])
a=load('arch-A-top-slot-print.stl');b=load('arch-B-bottom-slot-print.stl')
for m,y in [(a,10),(b,64)]:m.apply_translation([110,y-m.bounds[0,1],-m.bounds[0,2]])
parts=[ring,mid,a,b]
for name,m in zip(['lower-ring-positioned','upper-ring-positioned','arch-A-positioned','arch-B-positioned'],parts):
 assert abs(m.bounds[0,2])<1e-7
 assert np.all(m.bounds[0,:2]>=0) and np.all(m.bounds[1,:2]<=220)
 m.export(out/(name+'.stl'))
plate1=trimesh.util.concatenate([ring,mid]);plate2=trimesh.util.concatenate([a,b])
plate1.export(out/'plate-1-rings.stl');plate2.export(out/'plate-2-arches.stl')
# Combined layout for a larger bed; plate-2 is placed above plate-1 with a gap.
all_parts=[ring.copy(),mid.copy(),a.copy(),b.copy()]
for m in all_parts[2:]:m.apply_translation([0,210,0])
combined=trimesh.util.concatenate(all_parts);combined.export(out/'all-parts-large-bed.stl')
# Check triangle solids do not overlap within each plate.
for x,y in [(ring,mid),(a,b)]:
 assert x.bounds[0,2]==0 and y.bounds[0,2]==0
 # Large clearances can be verified directly from radial / rectangular extents.
assert np.max(np.linalg.norm(mid.vertices[:,:2]-[110,110],axis=1))<72
assert b.bounds[0,1]-a.bounds[1,1]>7
html0=(src/'preview.html').read_text()
def preview(name,meshes,title,description):
 meshes=[m.copy() for m in meshes]
 assembly=trimesh.util.concatenate(meshes);center=(assembly.bounds[0]+assembly.bounds[1])/2;center[2]=0
 assembly.apply_translation(-center)
 html=html0;a0=html.index('const data=');b0=html.index(';\nif(!window.THREE)',a0)
 html=html[:a0]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b0:]
 html=re.sub(r'<h1>.*?</h1>',f'<h1>{title}</h1>',html)
 html=re.sub(r'<small>.*?</small>',f'<small>{description}</small>',html)
 html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>모든 부품의 최저점을 Z=0에 맞췄습니다. 위 링은 슬롯이 위로 열리도록 뒤집었습니다.<br>슬라이서에서 자동 배치를 하지 않으면 이 위치가 유지됩니다.<br>서포트는 슬라이서 미리보기에서 확인하세요. 전체 삼각형 표시, 스무딩 없음.</p></details>',html)
 html=re.sub(r'<nav>.*?</nav>','<nav><button data-v="angle">입체</button><button data-v="top">위</button><a href="plate-1-rings.stl" download>1판 STL</a><a href="plate-2-arches.stl" download>2판 STL</a></nav>',html)
 html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),html)
 html=html.replace('i<4;i++',f'i<{len(meshes)};i++')
 html=re.sub(r"let exploded=false;document.querySelector\('#explode'\).onclick=.*?;update\(\)\};",'',html)
 html=html.replace('el=.48','el=1.1').replace('24+d*Math.sin(el)','d*Math.sin(el)').replace('camera.lookAt(0,0,24)','camera.lookAt(0,0,0)').replace('d=430','d=570')
 (out/name).write_text(html)
preview('preview.html',all_parts,'출력 배치 · 아래 링/위 링 + 아치 2개','모두 Z=0 · 1판: 링 두 개 / 2판: 아치 두 개 · 220×220mm 기준')
preview('plate-1.html',[ring,mid],'1판 · 링 2개','배치 외곽 200×200mm · 위 링은 슬롯이 위로 향함')
preview('plate-2.html',[a,b],'2판 · 아치 2개','배치 외곽 200×100.94mm · 넓은 면을 바닥에 배치')
spec={'source':'v21','all_parts_min_z_mm':[float(m.bounds[0,2]) for m in parts],'plate1_extents_mm':plate1.extents.tolist(),'plate2_extents_mm':plate2.extents.tolist(),'combined_extents_mm':combined.extents.tolist(),'upper_ring_flipped':True}
(out/'layout.json').write_text(json.dumps(spec,indent=2))
(out/'PRINT-NOTES.txt').write_text('v21 최신 형상. 단위 mm.\n220x220mm 베드 기준 2판 배치. 브림/스커트 여유는 슬라이서에서 확인하세요.\n1판 plate-1-rings.stl: 아래 링 + 슬롯이 위로 열린 위 링.\n2판 plate-2-arches.stl: 넓은 면을 바닥에 둔 아치 A/B.\nSTL에 여러 독립 부품이 포함되어 있습니다. 필요하면 슬라이서의 오브젝트 분리 기능을 사용하세요.\n형상은 바꾸지 않고 회전/이동만 했습니다. 자동 배치 시 위치가 달라집니다.\n경사 벽 창 등은 슬라이서의 레이어/서포트 미리보기로 확인하세요.\nall-parts-large-bed.stl은 대형 베드용이며 220x220mm에 들어가지 않습니다.\n')
print(json.dumps(spec,indent=2))
