from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-light-base-v14'
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True)
# Wall spans z=2..6. Windows span 3..5, preserving 1mm upper/lower height bands.
# 25-degree openings centered halfway between eight supports.
cutters=[]
for k in range(8):
 theta=np.linspace(math.radians(k*45+10),math.radians(k*45+35),257)
 xy=np.vstack((np.column_stack((102*np.cos(theta),102*np.sin(theta))),np.column_stack((92*np.cos(theta[::-1]),92*np.sin(theta[::-1])))))
 from shapely.geometry import Polygon
 cut=trimesh.creation.extrude_polygon(Polygon(xy),height=2,engine='earcut');cut.apply_translation([0,0,3]);cutters.append(cut)
ring=trimesh.boolean.difference([base]+cutters,engine='manifold')
assert ring.is_volume and ring.is_watertight and len(ring.split())==1
ring.export(out/'ring-print.stl')
parts=[ring]
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','mid-ring-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:
 shutil.copy2(src/name,out/name)
old_total=base.volume+sum(m.volume for m in parts[1:]);total=sum(m.volume for m in parts);initial=20.416692135655705
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>경량화 · 바닥 슬롯 + 경사 벽 창</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>경사 벽 슬롯 8개 추가 · 전체 {total/1000:.2f}cm³ · 최초 대비 {(1-total/1000/initial)*100:.1f}% 감소</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>기존 바닥판 슬롯 8개를 유지하고 경사 벽에 창 8개를 추가했습니다.<br>창 높이 2mm(z=3~5). 위아래 벽 띠는 높이 1mm씩 남겼습니다.<br>각 받침 사이 중앙 25° 구간만 비워 받침 연결부를 유지했습니다.<br>전체 삼각형 표시, 스무딩 없음. 실제 강성과 출력 상태는 확인이 필요합니다.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html)
(out/'preview.html').write_text(html)
spec={'wall_window_count':8,'window_z_mm':[3,5],'upper_lower_wall_band_height_mm':1,'window_arc_deg':25,'total_cm3':total/1000,'additional_saved_cm3':(old_total-total)/1000,'total_saved_percent':(1-total/1000/initial)*100,'connected_ring_solids':1,'watertight':True,'smooth_shading':False,'decimated':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
