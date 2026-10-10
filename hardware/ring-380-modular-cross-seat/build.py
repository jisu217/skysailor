from pathlib import Path
import trimesh,numpy as np,json,re,shutil
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-modular-base'
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
seat=trimesh.load(src/'center-seat-print.stl',force='mesh');seat.apply_translation([0,0,1])
arms=[box([377.6,6,1],[0,0,1.5]),box([6,377.6,1],[0,0,1.5])]
web=trimesh.boolean.union([box([369.6,1.6,2],[0,0,3]),box([1.6,369.6,2],[0,0,3])],engine='manifold')
clear=trimesh.creation.cylinder(radius=5.5,height=5,sections=256);clear.apply_translation([0,0,3])
web=trimesh.boolean.difference([web,clear],engine='manifold')
center=trimesh.boolean.union([seat,web]+arms,engine='manifold')
hole=trimesh.creation.cylinder(radius=2.5,height=12,sections=256);hole.apply_translation([0,0,5])
center=trimesh.boolean.difference([center,hole],engine='manifold')
assert center.is_watertight and center.is_volume and len(center.split())==1
center.export(out/'cross-with-center-seat-assembled.stl')
printed=center.copy();printed.apply_translation([0,0,-1]);printed.export(out/'cross-with-center-seat.stl')
quarters=[trimesh.load(src/f'ring-quarter-{i}-assembled.stl',force='mesh') for i in range(1,5)]
for q in quarters:
 hit=trimesh.boolean.intersection([q,center],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-4,hit.volume
meshes=quarters+[center];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
shutil.copy2(src/'ring-quarter-print.stl',out/'ring-quarter-print.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
s=s.replace('4분할 링 + 별도 중앙 받침','4분할 링 + 일체형 십자·원통 받침')
s=re.sub(r'<small>.*?</small>','<small>중앙 흰색: +자와 원통 한 부품 · 팔 6 × 1mm / 보강벽 1.6 × 2mm · 소켓 유격 각 0.2mm · 전체 중앙부 377.6mm</small>',s)
s=s.replace('center-seat-print.stl','cross-with-center-seat.stl').replace('중앙 받침 STL','십자·원통 STL')
(out/'preview.html').write_text(s)
print(json.dumps({'single_center_solid':True,'center_extents_mm':printed.extents.tolist(),'center_PLA_g':printed.volume*.00124,'socket_interference':False}))
