from pathlib import Path
import math,json,re,shutil
import trimesh
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-floor-brace-v22'
def cylinder(r,z0,z1):
 m=trimesh.creation.cylinder(radius=r,height=z1-z0,sections=512);m.apply_translation([0,0,(z0+z1)/2]);return m
def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True)
# Support the arch underside with a cross-slot cradle, without cutting the half-lap joint.
inner_center=math.sqrt(16900-94**2)
seat=2+math.sqrt(16900-4**2)-inner_center-.04
cup_bottom=seat-2;cup_top=45.2
cup=cylinder(4,cup_bottom,cup_top)
cuts=[box([12,2.2,10],[0,0,seat+5]),box([2.2,12,10],[0,0,seat+5])]
cup=trimesh.boolean.difference([cup]+cuts,engine='manifold')
post=cylinder(2,1.9,cup_bottom+.1)
central_disk=cylinder(4,0,2)
ring=trimesh.boolean.union([base,central_disk,post,cup],engine='manifold')
assert ring.is_volume and ring.is_watertight and len(ring.split())==1
parts=[ring]
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','mid-ring-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
 hit=trimesh.boolean.intersection([ring,m],engine='manifold');assert not len(hit.faces) or abs(hit.volume)<.001,(name,hit.volume)
# Check lowering both arches into the open cradle.
for m in parts[1:3]:
 for dz in (.1,1,3,6):
  raised=m.copy();raised.apply_translation([0,0,dz]);hit=trimesh.boolean.intersection([ring,raised],engine='manifold');assert not len(hit.faces) or abs(hit.volume)<.001
ring.export(out/'ring-print.stl')
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:shutil.copy2(src/name,out/name)
assembly=trimesh.util.concatenate(parts);total=sum(m.volume for m in parts)/1000
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>중앙 원판 + 기둥 + 십자 끼움 받침</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>바닥 원판 Ø8 × 2mm · 기둥 Ø4mm · 상단 십자 홈 폭 2.2mm · {total:.2f}cm³</small>',html)
html=re.sub(r'<details>.*?</details>',f'<details><summary>ⓘ</summary><p>바닥 + 중앙에 Ø8mm 원판, 두께 2mm.<br>Ø4mm 기둥과 Ø8mm 십자 홈 받침이 아래 링과 일체형입니다.<br>홈 바닥 z={seat:.3f}mm, 받침 윗면 z={cup_top}mm.<br>아치 교차부를 위에서 내려 폭 2.2mm 홈에 끼웁니다. 기존 중앙 반턱 홈은 유지했습니다.<br>전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html);(out/'preview.html').write_text(html)
spec={'base_disk_diameter_mm':8,'base_disk_thickness_mm':2,'post_diameter_mm':4,'post_top_z_mm':cup_bottom,'cradle_diameter_mm':8,'cradle_top_z_mm':cup_top,'slot_floor_z_mm':seat,'slot_width_mm':2.2,'total_cm3':total,'collision_free':True,'insertion_checked':True,'connected_base':True,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
