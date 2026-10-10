from pathlib import Path
import trimesh,numpy as np,json,re,math,shutil
out=Path(__file__).resolve().parent;root=out.parent
src=root/'ring-380-modular-cross-seat'
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
original=trimesh.load(src/'cross-with-center-seat-assembled.stl',force='mesh')
arm=trimesh.boolean.union([box([181.2,6,1],[98.2,0,1.5]),box([177.2,1.6,2.05],[96.2,0,2.975])],engine='manifold')
assert arm.is_volume and arm.is_watertight and len(arm.split())==1
seat=trimesh.load(root/'ring-380-modular-base/center-seat-print.stl',force='mesh');seat.apply_translation([0,0,1])
core=trimesh.creation.cylinder(radius=7.5,height=2,sections=256);core.apply_translation([0,0,1])
parts=[seat,core];cuts=[]
for i in range(4):
 turn=trimesh.transformations.rotation_matrix(i*math.pi/2,[0,0,1])
 shell=box([11.5,8.4,5.2],[10.25,0,2.6]);shell.apply_transform(turn);parts.append(shell)
 # Slots open at radius16, inner stop radius7.4. 0.2 gap to arm end.
 floor_slot=box([9,6.4,1.4],[11.9,0,1.5])
 wall_slot=box([9,2,2.2],[11.9,0,3.1])
 for c in [floor_slot,wall_slot]:c.apply_transform(turn);cuts.append(c)
hub=trimesh.boolean.union(parts,engine='manifold')
bore=trimesh.creation.cylinder(radius=2.5,height=12,sections=256);bore.apply_translation([0,0,5]);cuts.append(bore)
hub=trimesh.boolean.difference([hub]+cuts,engine='manifold')
assert hub.is_volume and hub.is_watertight and len(hub.split())==1
arms=[]
for i in range(4):
 m=arm.copy();m.apply_transform(trimesh.transformations.rotation_matrix(i*math.pi/2,[0,0,1]));arms.append(m)
 hit=trimesh.boolean.intersection([m,hub],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
p=arm.copy();p.apply_translation(-p.bounds[0]);p.export(out/'arm-print.stl')
hub.export(out/'center-t-slot-hub.stl')
quarters=[trimesh.load(root/'ring-380-modular-base'/f'ring-quarter-{i}-assembled.stl',force='mesh') for i in range(1,5)]
meshes=quarters+arms+[hub]
assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
shutil.copy2(root/'ring-380-modular-base/ring-quarter-print.stl',out/'ring-quarter-print.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
s=s.replace('[0x85c9de,0x9fd8b0,0xf0b66b,0xc7a1dd,0xe7e9ef][i]','[0x85c9de,0x9fd8b0,0xf0b66b,0xc7a1dd,0xe7e9ef,0xe7e9ef,0xe7e9ef,0xe7e9ef,0xf0a650][i]')
s=re.sub(r'<h1>.*?</h1>','<h1>팔 4개 + 중앙 ㅗ자 홈 허브</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>팔 개별 출력 · 중앙 ㅗ자 홈 4개 · 삽입 길이 8.4mm · 각 면 유격 0.2mm · 끼움 시험용 / 잠금 미적용</small>',s)
s=s.replace('cross-with-center-seat.stl','center-t-slot-hub.stl').replace('십자·원통 STL','중앙 허브 STL').replace('</nav>','<a href="arm-print.stl" download>팔 STL (4개)</a></nav>')
(out/'preview.html').write_text(s)
print(json.dumps({'arm_mm':p.extents.tolist(),'hub_mm':hub.extents.tolist(),'insertion_mm':8.4,'verified':'watertight parts and no hub/arm intersection'}))
