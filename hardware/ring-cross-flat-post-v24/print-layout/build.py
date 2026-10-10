from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent;src=out.parent
names=['ring-print.stl','mid-ring-print.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','post-1-print.stl','post-2-print.stl']
# Arrange the smaller parts in the spaces between the bottom ring's cross braces.
# Flat arches span ~200mm; keep them on a separate plate for a compact print.
meshes=[]
for n in names:
 m=trimesh.load(src/n,force='mesh');m.process(validate=True);m.apply_translation(-m.bounds[0]);meshes.append(m)
# Two plates: base ring alone; other five parts in independent rows.
base=meshes[0];base.export(out/'plate-1-base.stl')
mid=meshes[1].copy()
p1=meshes[4].copy();p1.apply_translation([148,0,0])
p2=meshes[5].copy();p2.apply_translation([162,0,0])
plate2=trimesh.util.concatenate([mid,p1,p2])
a1=meshes[2].copy();a2=meshes[3].copy();a2.apply_translation([0,a1.extents[1]+6,0])
plate3=trimesh.util.concatenate([a1,a2])
all_parts=[base.copy(),mid,a1,a2,p1,p2]
for i in [1,4,5]:all_parts[i].apply_translation([206,0,0])
for i in [2,3]:all_parts[i].apply_translation([206,148,0])
allmesh=trimesh.util.concatenate(all_parts)
plate2.export(out/'plate-2-ring-and-posts.stl');plate3.export(out/'plate-3-arches.stl');allmesh.export(out/'all-parts-flat.stl')
for i,m in enumerate(all_parts):
 assert abs(m.bounds[0,2])<1e-6
for i in range(len(all_parts)):
 for j in range(i+1,len(all_parts)):
  a,b=all_parts[i].bounds,all_parts[j].bounds
  assert a[1,0]<=b[0,0] or b[1,0]<=a[0,0] or a[1,1]<=b[0,1] or b[1,1]<=a[0,1]
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
# Center all laid-out parts for the existing camera.
show=allmesh.copy();center=(show.bounds[0]+show.bounds[1])/2;show.apply_translation([-center[0],-center[1],0])
html=html[:a]+'const data='+json.dumps({'vertices':show.vertices.tolist(),'faces':show.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>출력 배치 · 부품 6개 바닥 정렬</h1>',html)
html=re.sub(r'<small>.*?</small>','<small>모든 부품 z=0 · 아치와 기둥 판은 눕힘 · 세 출력 묶음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>왼쪽: 아래 링. 오른쪽 위: 위 링과 기둥 판 2개. 오른쪽 아래: 아치 2개.<br>배치 전체는 출력판 크기를 가정하지 않은 비교용입니다. 판별 크기를 확인하고 슬라이서에서 재배치할 수 있습니다.<br>각 부품 최저면 z=0, 부품끼리 겹침 없음.<br>위 링 밑면 포켓과 바닥 소켓 주변은 슬라이서에서 브리지/서포트 확인이 필요합니다.</p></details>',html)
html=re.sub(r'<nav>.*?</nav>','<nav><button data-v="angle">입체</button><button data-v="top">위</button><button data-v="side">옆</button><a href="plate-1-base.stl" download>바닥 링</a><a href="plate-2-ring-and-posts.stl" download>위 링·기둥</a><a href="plate-3-arches.stl" download>아치</a><a href="all-parts-flat.stl" download>전체 배치</a></nav>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in all_parts]),html)
html=re.sub(r"let exploded=false;document.querySelector\('#explode'\).onclick=.*?;\n",'',html)
# Remove handler explicitly if matching one-line closure failed.
start=html.find('let exploded=false;')
if start>=0:
 end=html.index('scene.add(new T.HemisphereLight',start);html=html[:start]+html[end:]
html=html.replace('d=430','d=850').replace('el=.48','el=1.15')
(out/'preview.html').write_text(html)
spec={'plate1_mm':base.extents.tolist(),'plate2_mm':plate2.extents.tolist(),'plate3_mm':plate3.extents.tolist(),'all_parts_mm':allmesh.extents.tolist(),'all_parts_on_z0':True,'no_xy_overlap':True}
(out/'layout.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
