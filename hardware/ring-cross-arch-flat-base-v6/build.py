from pathlib import Path
import json,re,shutil
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-arch-v5'
ring=trimesh.load(src/'ring-print.stl',force='mesh');ring.process(validate=True)
# Restore the entire original annular base, z=0..2, OD200 / ID188.
base=trimesh.creation.revolve([[94,0],[100,0],[100,2],[94,2],[94,0]],sections=1024)
ring=trimesh.boolean.union([ring,base],engine='manifold')
assert ring.is_volume and ring.is_watertight and len(ring.split())==1
ring.export(out/'ring-print.stl')
a=trimesh.load(src/'arch-A-top-slot-assembled.stl',force='mesh');a.process(validate=True)
b=trimesh.load(src/'arch-B-bottom-slot-assembled.stl',force='mesh');b.process(validate=True)
for m in (a,b):
 overlap=trimesh.boolean.intersection([ring,m],engine='manifold')
 assert not len(overlap.faces) or abs(overlap.volume)<.001
missing=trimesh.boolean.difference([base,ring],engine='manifold')
assert not len(missing.faces) or abs(missing.volume)<.001
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','ASSEMBLY.txt']:
 shutil.copy2(src/name,out/name)
assembly=trimesh.util.concatenate([ring,a,b])
html=(src/'preview.html').read_text()
p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 · 바닥판 홈 제거</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>바닥판 평면 복원 · 위쪽 끼움 홈 4개 유지 · {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=html.replace('별도 발 돌기 없이 링 홈 4개를 유지했습니다.','아래 링 바닥판의 홈을 메웠습니다. 위쪽 곡면 벽의 홈 4개는 유지했습니다.')
html=re.sub(r'const counts=\[[^\]]+\]', 'const counts='+json.dumps([len(m.faces)*3 for m in (ring,a,b)]),html)
assert 'toNonIndexed()' in html and 'flatShading:true' in html
(out/'preview.html').write_text(html)
(out/'specs.json').write_text(json.dumps({'base_od_mm':200,'base_id_mm':188,'base_height_mm':2,'base_grooves':0,'upper_wall_grooves':4,'triangles':len(assembly.faces),'smooth_shading':False,'decimated':False,'arch_collision_mm3':0},indent=2))
print('Base restored; upper slots retained; no arch overlap. Triangles:',len(assembly.faces))
