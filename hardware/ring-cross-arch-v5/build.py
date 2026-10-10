from pathlib import Path
import json,re,math
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-arch-no-feet-v4'
ring=trimesh.load(src/'ring-print.stl',force='mesh')
ring.process(validate=True)
rz=trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1])
rotated=ring.copy();rotated.apply_transform(rz)
ring=trimesh.boolean.intersection([ring,rotated],engine='manifold')
raw=trimesh.load(src/'arch-assembled.stl',force='mesh')
z_top=2+130-math.sqrt(130**2-100**2)
z_inner=2+130-math.sqrt(130**2-94**2)
z_mid=(z_top+z_inner)/2
slot_w=2.2; half_gap=.05

def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m
# A: open from above. B: open from below. Leave 0.10 mm vertical clearance.
a=trimesh.boolean.difference([raw,box([slot_w,6,20],[0,0,z_mid-half_gap+10])],engine='manifold')
b_local=trimesh.boolean.difference([raw,box([slot_w,6,100],[0,0,z_mid+half_gap-50])],engine='manifold')
b=b_local.copy();b.apply_transform(rz)
for name,m in [('ring-print',ring),('arch-A-top-slot-assembled',a),('arch-B-bottom-slot-assembled',b)]:
 assert m.is_watertight and m.is_volume and len(m.split())==1,name
 m.export(out/(name+'.stl'))
for name,m in [('arch-A-top-slot-print',a),('arch-B-bottom-slot-print',b_local)]:
 flat=m.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]])
 flat.export(out/(name+'.stl'))
def volume_overlap(x,y):
 v=trimesh.boolean.intersection([x,y],engine='manifold')
 return float(abs(v.volume)) if len(v.faces) else 0.
for x,y in [(ring,a),(ring,b),(a,b)]:assert volume_overlap(x,y)<.001
# Assembly sequence: seat A, then lower B from above.
for dz in (.1,1,3,6,10):
 raised=b.copy();raised.apply_translation([0,0,dz])
 assert volume_overlap(a,raised)<.001
 assert volume_overlap(ring,raised)<.001
assembly=trimesh.util.concatenate([ring,a,b])
html=(src/'preview.html').read_text()
p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 · 위 / 아래 반턱 홈</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>90° 교차 · 홈 폭 2.2mm · 전체 {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>주황 A: 위로 열린 홈. 초록 B: 아래로 열린 홈.<br>A를 링에 끼운 뒤 B를 위에서 내려 교차부와 링 홈에 동시에 끼웁니다.<br>홈 폭 2.2mm / 아치 두께 2mm / 중앙 높이 여유 0.10mm.<br>별도 발 돌기 없이 링 홈 4개를 유지했습니다.<br>모든 STL 삼각형을 면별 법선으로 표시합니다.</p></details>',html)
html=html.replace('<a href="arch-print.stl" download>아치 STL</a>','<a href="arch-A-top-slot-print.stl" download>A STL</a><a href="arch-B-bottom-slot-print.stl" download>B STL</a>')
p=html.index('const meshGroup=');q=html.index('scene.add(new T.HemisphereLight',p)
counts=[len(m.faces)*3 for m in (ring,a,b)]
html=html[:p]+f'''const mats=[0x85c9de,0xf0b66b,0x9fdaa6];
const counts={json.dumps(counts)};let offset=0;const parts=[];
for(let i=0;i<3;i++){{const partG=g.clone();partG.setDrawRange(offset,counts[i]);offset+=counts[i];const m=new T.Mesh(partG,new T.MeshStandardMaterial({{color:mats[i],roughness:.5,flatShading:true,side:T.DoubleSide}}));scene.add(m);parts.push(m);}}
let exploded=false;document.querySelector('#explode').onclick=()=>{{exploded=!exploded;parts[1].position.z=exploded?12:0;parts[2].position.z=exploded?30:0;update()}};
'''+html[q:]
assert 'toNonIndexed()' in html
(out/'preview.html').write_text(html)
spec={'slot_width_mm':slot_w,'arch_thickness_mm':2,'joint_mid_z_mm':z_mid,'vertical_clearance_mm':2*half_gap,'top_slot_depth_at_center_mm':z_top-z_mid+half_gap,'bottom_slot_depth_at_center_mm':z_mid+half_gap-z_inner,'ring_groove_count':4,'part_count':3,'triangles':[len(m.faces) for m in (ring,a,b)],'rendered_triangles':len(assembly.faces),'smooth_shading':False,'decimated':False,'collision_free':True,'B_insertion_checked_offsets_mm':[.1,1,3,6,10]}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
(out/'ASSEMBLY.txt').write_text('단위 mm. 링, 아치 A, 아치 B를 각 1개 출력합니다.\n1. ring-print.stl을 바닥면으로 출력합니다.\n2. A/B의 print STL은 넓은 면이 베드에 닿도록 배치되어 있습니다.\n3. 위로 열린 홈이 있는 A를 링에 먼저 끼웁니다.\n4. 아래로 열린 홈이 있는 B를 90도 방향에서 위에서 내려 끼웁니다.\n홈 폭 2.2mm, 아치 두께 2mm, 중앙 수직 여유 0.10mm. 실제 맞춤은 출력 오차에 따라 조정이 필요할 수 있습니다.\n')
print(json.dumps(spec,indent=2))
