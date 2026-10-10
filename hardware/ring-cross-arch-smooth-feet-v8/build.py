from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-arch-flat-base-v6'
ring=trimesh.load(out.parent/'ring-cross-arch-v5/ring-print.stl',force='mesh');ring.process(validate=True)
base=trimesh.creation.revolve([[94,0],[100,0],[100,2],[94,2],[94,0]],sections=1024)
ring=trimesh.boolean.union([ring,base],engine='manifold')
# Continue the wall foot with a tangent-continuous blend to the original inner arch.
# Equal-radius shifted arcs do not intersect, so a smooth blend is required.
co=math.sqrt(130**2-100**2);ci=math.sqrt(130**2-94**2)
join_h=12.
z=np.linspace(0,join_h,257)
wall_inner=np.sqrt(130**2-(co+z)**2)-2
arch_inner=np.sqrt(130**2-(ci+z)**2)
t=np.clip((z-4)/8,0,1);blend=t*t*(3-2*t)
cut_r=wall_inner*(1-blend)+arch_inner*blend
profile=np.vstack(([[0,2]],np.column_stack((cut_r,2+z)),[[0,2+join_h],[0,2]]))
inner_cut=trimesh.creation.revolve(profile,sections=1024)
arches=[]
for label in ('A-top-slot','B-bottom-slot'):
 m=trimesh.load(src/('arch-'+label+'-assembled.stl'),force='mesh');m.process(validate=True)
 shaped=trimesh.boolean.difference([m,inner_cut],engine='manifold')
 assert shaped.is_watertight and shaped.is_volume and len(shaped.split())==1
 shaped.export(out/('arch-'+label+'-assembled.stl'))
 flat=shaped.copy()
 if label.startswith('B'):flat.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/2,[0,0,1]))
 flat.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]])
 flat.export(out/('arch-'+label+'-print.stl'))
 arches.append(shaped)
for x,y in [(ring,arches[0]),(ring,arches[1]),tuple(arches)]:
 collision=trimesh.boolean.intersection([x,y],engine='manifold')
 assert not len(collision.faces) or abs(collision.volume)<.001
ring.export(out/'ring-print.stl')
assembly=trimesh.util.concatenate([ring]+arches)
html=(src/'preview.html').read_text()
p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 · 턱 없이 이어지는 경사 발</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>경사면을 아치 안쪽 윤곽까지 연장 · {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>발의 안쪽 경사 곡면을 아치 안쪽 윤곽까지 이어 수평 턱을 제거했습니다.<br>발의 바깥 윤곽은 원래 아치 곡선을 유지합니다. 홈 양옆에는 기존 조립 여유가 남습니다.<br>바닥판과 중앙 반턱 홈은 유지했습니다.<br>분해 버튼으로 발 모양을 확인하세요. 전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]', 'const counts='+json.dumps([len(m.faces)*3 for m in [ring]+arches]),html)
(out/'preview.html').write_text(html)
(out/'specs.json').write_text(json.dumps({'foot_region_z_mm':[2,2+join_h],'foot_shape':'tangent-continuous blend from wall inner curve to arch inner edge, h=4..12mm','ring_unchanged':True,'center_joint_unchanged':True,'triangles':len(assembly.faces),'smooth_shading':False,'decimated':False,'collision_free':True},indent=2))
print('Join height above base:',join_h)
print('Validated two connected arches; no overlaps. Triangles:',len(assembly.faces))
