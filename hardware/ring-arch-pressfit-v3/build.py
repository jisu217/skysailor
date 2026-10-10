from pathlib import Path
import json, re
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent
src=out.parent/'ring-200-arch-matched-v2'
base=trimesh.load(src/'ring-curved-wall.stl',force='mesh')
arch=trimesh.load(out.parent/'ring-200-arch-v1/arch.stl',force='mesh')
slot_width=2.2
rib_projection=.15

def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m

def union(ms): return trimesh.boolean.union(ms,engine='manifold')
def diff(a,bs): return trimesh.boolean.difference([a]+bs,engine='manifold')
# Compact socket cheeks at both feet; retain a 1.0 mm floor.
bosses=[box([5.6,7,5.5],[s*96.8,0,3.75]) for s in (-1,1)]
ring=union([base]+bosses)
# Top-open slot has a 0.4 mm lead-in flare, rising from z=5.8.
# Extruded YZ polygon is transformed to span the radial X direction.
section=Polygon([(-1.1,1),(1.1,1),(1.1,5.8),(1.5,6.5),(1.5,10),(-1.5,10),(-1.5,6.5),(-1.1,5.8)])
cutters=[]
for s in (-1,1):
 m=trimesh.creation.extrude_polygon(section,height=8,engine='earcut')
 m.apply_transform(np.array([[0,0,1,s*97-4],[1,0,0,0],[0,1,0,0],[0,0,0,1]]))
 cutters.append(m)
ring=diff(ring,cutters)
# Tongue bottoms at z=1.2: 0.2 mm floor clearance. The original feet seat at z=2.
tabs=[box([3.5,2,1.0],[s*96.75,0,1.7]) for s in (-1,1)]
# Four short tapered crush/friction ribs. Nominal width 2.30 in a 2.20 slot.
ribs=[]
for s in (-1,1):
 for side in (-1,1):
  poly=Polygon([(side*.95,2.3),(side*(1+rib_projection),2.8),(side*(1+rib_projection),3.5),(side*.95,4.1)])
  m=trimesh.creation.extrude_polygon(poly,height=1.2,engine='earcut')
  m.apply_transform(np.array([[0,0,1,s*96.5-.6],[1,0,0,0],[0,1,0,0],[0,0,0,1]]))
  ribs.append(m)
arch=union([arch]+tabs+ribs)
# Seat pads stop the feet at z=2; keep a tongue pocket in their center.
# Existing ring floor is restored outside the tongue envelope.
seat_pads=[]
for s in (-1,1):
 pad=box([6,2.2,1],[s*97,0,1.5])
 pocket=box([3.9,2.2,2],[s*96.75,0,1.5])
 seat_pads.append(diff(pad,[pocket]))
ring=union([ring]+seat_pads)
for name,m in [('ring-print',ring),('arch-assembled',arch)]:
 assert m.is_watertight and m.is_volume and len(m.split())==1,name
 m.export(out/(name+'.stl'))
flat=arch.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]])
# Ribs protrude on both faces; flat print has small raised areas requiring slicer support.
flat.export(out/'arch-print.stl')
# Verify overlap occurs only at intended friction ribs, not main arch or tongues.
plain=diff(arch,ribs)
collision=trimesh.boolean.intersection([ring,plain],engine='manifold')
assert abs(collision.volume)<.001,collision.volume
inter=trimesh.boolean.intersection([ring,arch],engine='manifold')
assert 0<inter.volume<1,inter.volume
# Verify straight insertion path for main shape, excluding intentional rib interference.
for dz in (0.3,1,2,4,7):
 moved=plain.copy();moved.apply_translation([0,0,dz])
 overlap=trimesh.boolean.intersection([ring,moved],engine='manifold')
 assert abs(overlap.volume)<.001,(dz,overlap.volume)
# Crop a real socket and matching foot for fit testing.
clip=box([12,14,12],[97,0,5])
socket_test=trimesh.boolean.intersection([ring,clip],engine='manifold')
foot_test=trimesh.boolean.intersection([arch,box([10,8,8],[97,0,4])],engine='manifold')
for name,m in [('fit-socket',socket_test),('fit-foot',foot_test)]:
 assert m.is_watertight and m.is_volume and len(m.split())==1
 if name=='fit-foot':m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
 m.apply_translation(-m.bounds[0]);m.export(out/(name+'.stl'))
assembly=trimesh.util.concatenate([ring,arch])
html=(src/'preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>링 + 아치 · 별도 출력 / 끼움 조립</h1>',html)
html=re.sub(r'<small>.*?</small>','<small>위에서 끼우는 홈 · 폭 2.2mm · 마찰 돌기 포함 폭 2.3mm</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>파랑: 링 / 주황: 아치.<br>홈 입구는 넓게, 아래쪽에는 받침과 돌기 자리를 만들었습니다.<br>아치 양면의 작은 마찰 돌기가 각각 0.05mm 눌리는 설계입니다.<br>시험편을 먼저 출력하고 빡빡하면 마찰 돌기를 조금씩 다듬으세요.<br>분해 버튼으로 수직 조립 방향을 볼 수 있습니다.</p></details>',html)
html=html.replace('<a href="ring-with-arch.stl" download>STL</a>','<button id="explode">분해 / 조립</button><a href="ring-print.stl" download>링 STL</a><a href="arch-print.stl" download>아치 STL</a>')
needle='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,metalness:.12,roughness:.48,flatShading:true,side:T.DoubleSide})));'
replacement='''const meshGroup=new T.Group();scene.add(meshGroup);
const ringG=g.clone();ringG.setDrawRange(0,RINGCOUNT);
const archG=g.clone();archG.setDrawRange(RINGCOUNT,ARCHCOUNT);
meshGroup.add(new T.Mesh(ringG,new T.MeshStandardMaterial({color:0x85c9de,roughness:.5,side:T.DoubleSide})));
const archMesh=new T.Mesh(archG,new T.MeshStandardMaterial({color:0xf0b66b,roughness:.5,side:T.DoubleSide}));meshGroup.add(archMesh);
document.querySelector('#explode').onclick=()=>{archMesh.position.z=archMesh.position.z?0:22;update()};'''.replace('RINGCOUNT',str(len(ring.faces)*3)).replace('ARCHCOUNT',str(len(arch.faces)*3))
assert needle in html
html=html.replace(needle,replacement)
(out/'preview.html').write_text(html)
spec={'slot_width_mm':2.2,'arch_thickness_mm':2,'rib_total_width_mm':2.3,'interference_per_side_mm':.05,'tongue_depth_mm':.8,'pocket_floor_z_mm':1,'tongue_bottom_z_mm':1.2,'socket_top_z_mm':6.5,'designed_interference_volume_mm3':float(inter.volume),'main_shape_collision_mm3':float(collision.volume),'vertical_insertion_checked_mm':[.3,1,2,4,7],'separate_watertight_parts':2}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
(out/'PRINT-NOTES.txt').write_text('''단위 mm. 링과 아치를 별도로 출력합니다.
1. fit-socket.stl과 fit-foot.stl을 먼저 출력해 맞춤을 확인합니다.
2. ring-print.stl은 바닥을 베드에 놓습니다.
3. arch-print.stl은 아치의 넓은 면이 베드 방향입니다. 양면 마찰 돌기 때문에 본체가 베드에서 0.15mm 떠 있습니다. 슬라이서에서 지지/접지 상태를 확인하세요.
4. 아치를 링 위에서 수직으로 내립니다. 양쪽 발을 번갈아 조금씩 누릅니다.
5. 홈 폭 2.2mm, 본체 2mm, 마찰 돌기 포함 2.3mm. 돌기는 면마다 0.05mm 간섭입니다.
6. 너무 빡빡하면 주황 아치 발의 작은 돌기만 조금씩 다듬습니다. 느슨하면 build.py의 rib_projection을 키워 시험편을 다시 생성합니다.
마찰 고정이며 잠금턱 방식은 아닙니다. 실제 유지력은 재료와 출력 설정에 따라 시험해야 합니다.
''')
print(json.dumps(spec,indent=2))
