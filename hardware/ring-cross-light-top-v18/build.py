from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-longer-slots-v17'
mid=trimesh.load(src/'mid-ring-assembled.stl',force='mesh');mid.process(validate=True)
z=np.linspace(23.999,25.2,129)
ro=np.minimum(76,np.sqrt(130**2-(math.sqrt(130**2-100**2)+z-2)**2))-.9
profile=np.vstack(([[72.9,z[0]]],np.column_stack((ro,z)),[[72.9,z[-1]],[72.9,z[0]]]))
cavity=trimesh.creation.revolve(profile,sections=2048)
cutters=[]
for k in range(8):
 t=np.linspace(math.radians(k*45+10),math.radians(k*45+35),257)
 xy=np.vstack((np.column_stack((80*np.cos(t),80*np.sin(t))),np.column_stack((70*np.cos(t[::-1]),70*np.sin(t[::-1])))))
 sector=trimesh.creation.extrude_polygon(Polygon(xy),height=4,engine='earcut');sector.apply_translation([0,0,23])
 cutters.append(trimesh.boolean.intersection([cavity,sector],engine='manifold'))
light=trimesh.boolean.difference([mid]+cutters,engine='manifold')
assert light.is_watertight and light.is_volume and len(light.split())==1
light.export(out/'mid-ring-assembled.stl');flat=light.copy();flat.apply_translation([0,0,-24]);flat.export(out/'mid-ring-print.stl')
parts=[]
for name in ['ring-print.stl','arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
for name in ['ring-print.stl','arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl']:shutil.copy2(src/name,out/name)
parts.append(light);total=sum(m.volume for m in parts);saved=mid.volume-light.volume
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>경량화 · 위 링 밑면 슬롯 8개</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>위 링 밑면 깊이 1.2mm · 윗면 0.8mm 유지 · 전체 {total/1000:.2f}cm³</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>위 링에 아래로 열린 슬롯 8개를 추가했습니다.<br>깊이 1.2mm, 윗면 두께 0.8mm, 안팎 반지름 방향 테두리 0.9mm 유지.<br>네 끼움 홈과 받침 접촉면 주변은 보존했습니다.<br>아래 보기 또는 분해 버튼으로 밑면을 확인하세요.<br>전체 삼각형 표시, 스무딩 없음. 출력 시 얇은 부분과 슬롯 천장의 브리지를 확인하세요.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html)
(out/'preview.html').write_text(html)
spec={'top_ring_pockets':8,'pocket_depth_mm':1.2,'top_skin_mm':.8,'radial_side_margin_mm':.9,'old_top_cm3':mid.volume/1000,'new_top_cm3':light.volume/1000,'saved_cm3':saved/1000,'total_cm3':total/1000,'connected':True,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
