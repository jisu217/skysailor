from pathlib import Path
import json,re,shutil,math
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-light-arches-v16'
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True)
# Eight curved slots: radial span 95.5..98.5 leaves 1.5 mm rims.
# End caps radius 1.5 mm; centerline sweep 10..35 degrees in each sector.
# Cut only the 2 mm bottom plate, preserving all upper wall and supports.
cutters=[]
for k in range(8):
 angles=np.linspace(math.radians(k*45+7.5),math.radians(k*45+37.5),257)
 # Sweep a disk along a circular arc; planar outline has semicircular ends.
 r=97.; half=1.5
 a0,a1=angles[0],angles[-1]
 pts=[]
 pts.extend(np.column_stack(((r+half)*np.cos(angles),(r+half)*np.sin(angles))))
 end=r*np.array([math.cos(a1),math.sin(a1)])
 t=np.linspace(a1,a1+math.pi,129)[1:]
 pts.extend(end+half*np.column_stack((np.cos(t),np.sin(t))))
 rev=angles[::-1][1:]
 pts.extend(np.column_stack(((r-half)*np.cos(rev),(r-half)*np.sin(rev))))
 start=r*np.array([math.cos(a0),math.sin(a0)])
 t=np.linspace(a0+math.pi,a0+2*math.pi,129)[1:-1]
 pts.extend(start+half*np.column_stack((np.cos(t),np.sin(t))))
 from shapely.geometry import Polygon
 poly=Polygon(pts);assert poly.is_valid
 m=trimesh.creation.extrude_polygon(poly,height=2.001,engine='earcut');m.apply_translation([0,0,-.001]);cutters.append(m)
light=trimesh.boolean.difference([base]+cutters,engine='manifold')
# Extend the existing sloping-wall windows to the same 30-degree sweep.
wall_cutters=[]
for k in range(8):
 theta=np.linspace(math.radians(k*45+7.5),math.radians(k*45+37.5),513)
 xy=np.vstack((np.column_stack((102*np.cos(theta),102*np.sin(theta))),np.column_stack((92*np.cos(theta[::-1]),92*np.sin(theta[::-1])))))
 c=trimesh.creation.extrude_polygon(Polygon(xy),height=2,engine='earcut');c.apply_translation([0,0,3]);wall_cutters.append(c)
light=trimesh.boolean.difference([light]+wall_cutters,engine='manifold')
assert light.is_volume and light.is_watertight and len(light.split())==1
light.export(out/'ring-print.stl')
parts=[light]
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','mid-ring-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:
 shutil.copy2(src/name,out/name)
# Confirm that the base slot cutters remain confined to the lower plate.
removed=trimesh.boolean.intersection([base,trimesh.util.concatenate(cutters)],engine='manifold')
assert removed.bounds[1,2]<=2.00001
saved=base.volume-light.volume
old_total=base.volume+sum(m.volume for m in parts[1:]);new_total=sum(m.volume for m in parts)
assembly=trimesh.util.concatenate(parts)
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>경량화 · 슬롯 길이 30°로 확대</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>슬롯 폭 3mm · 테두리 1.5mm · 부피 {new_total/1000:.2f}cm³ · {saved/old_total*100:.1f}% 감소</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>바닥판과 경사 벽의 슬롯을 25°에서 30°로 늘렸습니다.<br>바닥 슬롯 폭 3mm, 경사 벽 슬롯 높이 2mm 유지.<br>바닥 안팎 테두리 1.5mm, 벽 위아래 높이 1mm 및 받침 아래 유지.<br>아래 보기 버튼으로 슬롯을 확인하세요.<br>전체 삼각형 표시, 스무딩 없음. 강성은 실물 확인이 필요합니다.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html)
(out/'preview.html').write_text(html)
spec={'slot_count':8,'slot_width_mm':3,'inner_outer_rim_mm':1.5,'centerline_radius_mm':97,'centerline_arc_deg':30,'old_total_cm3':old_total/1000,'new_total_cm3':new_total/1000,'saved_cm3':saved/1000,'saved_percent':saved/old_total*100,'new_base_cm3':light.volume/1000,'watertight':True,'connected_base_solids':1,'decimated':False,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
