from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-cross-center-post-v23'
def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m
def cyl(r,z0,z1):
 m=trimesh.creation.cylinder(radius=r,height=z1-z0,sections=512);m.apply_translation([0,0,(z0+z1)/2]);return m
def rot(m,a):
 m=m.copy();m.apply_transform(trimesh.transformations.rotation_matrix(a,[0,0,1]));return m
def diff(m,cs):return trimesh.boolean.difference([m]+cs,engine='manifold')
# Restore the original flat base; remove the integral upright post entirely.
base=trimesh.load(root/'ring-cross-floor-brace-v22/ring-print.stl',force='mesh');base.process(validate=True)
# 16mm disk and 3mm tall socket, open upwards; two 8.4 x 2.2 slots at 45/135 deg.
socket=cyl(6,1.9,5)
slots=[rot(box([8.4,2.2,5],[0,0,4.5]),a) for a in (math.pi/4,3*math.pi/4)]
socket=diff(socket,slots)
base=trimesh.boolean.union([base,cyl(8,0,2),socket],engine='manifold')
# Flat plates have opposite half-height joints. Their top edge has the global
# arch-aligned cross clearance carved through it, replacing the old cup.
seat=42.098669683671694;top=45.2;bottom=2.;joint=(bottom+top)/2
posts=[]
for i,a in enumerate((math.pi/4,3*math.pi/4)):
 plate=box([8,2,top-bottom],[0,0,(top+bottom)/2])
 if i==0:cut=box([2.2,4,top-joint+.1],[0,0,(joint-.05+top+.05)/2])
 else:cut=box([2.2,4,joint-bottom+.1],[0,0,(bottom-.05+joint+.05)/2])
 plate=diff(plate,[cut]);plate=rot(plate,a)
 plate=diff(plate,[box([12,2.2,10],[0,0,seat+5]),box([2.2,12,10],[0,0,seat+5])])
 assert plate.is_volume and plate.is_watertight and len(plate.split())==1
 posts.append(plate)
 plate.export(out/f'post-{i+1}-assembled.stl')
 flat=rot(plate,-a);flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/f'post-{i+1}-print.stl')
parts=[base]
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','mid-ring-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
parts+=posts
for i in range(len(parts)):
 for j in range(i+1,len(parts)):
  hit=trimesh.boolean.intersection([parts[i],parts[j]],engine='manifold')
  assert not len(hit.faces) or abs(hit.volume)<.001,(i,j,hit.volume)
assert base.is_volume and base.is_watertight and len(base.split())==1
base.export(out/'ring-print.stl')
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:shutil.copy2(src/name,out/name)
assembly=trimesh.util.concatenate(parts);total=sum(m.volume for m in parts)/1000
html=(src/'preview.html').read_text();p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>중앙 기둥 · 평판 2장 X자 조립</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>바닥 원판 Ø16 × 2mm · 판 폭 8 × 두께 2mm · 전체 {total:.2f}cm³</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>중앙 기둥은 별도 평판 2장을 눕혀 출력합니다.<br>위/아래 반턱 홈으로 판을 결합한 후 45° 방향 X자 바닥 소켓에 내려 끼웁니다.<br>소켓 높이 3mm, 홈 폭 2.2mm. 바닥 원판 Ø16mm.<br>판 윗부분의 홈은 기존 아치 교차부를 받칩니다.<br>조립 순서: 기둥 판끼리 결합 → 바닥에 끼움 → 아치 A/B → 위 링.<br>전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=html.replace('const mats=[0x85c9de,0xf0b66b,0x9fdaa6,0xc59aef]','const mats=[0x85c9de,0xf0b66b,0x9fdaa6,0xc59aef,0xe5a3c1,0xdad58a]')
html=html.replace('i<4;i++','i<6;i++').replace('parts[3].position.z=exploded?50:0;','parts[3].position.z=exploded?50:0;parts[4].position.z=exploded?8:0;parts[5].position.z=exploded?12:0;')
html=html.replace('</nav>','<a href="post-1-print.stl" download>기둥 1</a><a href="post-2-print.stl" download>기둥 2</a></nav>')
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html);(out/'preview.html').write_text(html)
spec={'disk_diameter_mm':16,'disk_thickness_mm':2,'socket_height_mm':3,'plate_width_mm':8,'plate_thickness_mm':2,'plate_height_mm':top-bottom,'joint_slot_width_mm':2.2,'post_angles_deg':[45,135],'parts':6,'assembled_collision_free':True,'total_cm3':total,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
