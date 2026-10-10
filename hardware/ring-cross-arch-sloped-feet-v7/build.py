from pathlib import Path
import math,json,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-arch-flat-base-v6'
ring=trimesh.load(out.parent/'ring-cross-arch-v5/ring-print.stl',force='mesh');ring.process(validate=True)
base=trimesh.creation.revolve([[94,0],[100,0],[100,2],[94,2],[94,0]],sections=1024)
ring=trimesh.boolean.union([ring,base],engine='manifold')
# Match the foot to the exact annular sloping wall over z=2..6.
z=np.linspace(0,4,65);r=np.sqrt(130**2-(math.sqrt(130**2-100**2)+z)**2)
profile=np.vstack((np.column_stack((r,2+z)),np.column_stack(((r-2)[::-1],(2+z)[::-1])),[[r[0],2]]))
envelope=trimesh.creation.revolve(profile,sections=1024)
upper=trimesh.creation.box([220,220,100]);upper.apply_translation([0,0,56])
arches=[]
for label in ('A-top-slot','B-bottom-slot'):
 m=trimesh.load(src/('arch-'+label+'-assembled.stl'),force='mesh');m.process(validate=True)
 foot=trimesh.boolean.intersection([m,envelope],engine='manifold')
 top=trimesh.boolean.intersection([m,upper],engine='manifold')
 shaped=trimesh.boolean.union([foot,top],engine='manifold')
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
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 · 경사 벽에 맞춘 발</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>아치 아래 4mm를 경사 벽 단면에 맞춤 · {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>아치 양끝 z=2~6 구간을 링의 경사 벽 단면에 맞췄습니다.<br>발은 벽의 바깥 곡면과 안쪽 곡면 사이만 채웁니다. 홈 양옆에는 기존 조립 여유가 남습니다.<br>바닥판과 중앙 반턱 홈은 유지했습니다.<br>분해 버튼으로 발 모양을 확인하세요. 전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]', 'const counts='+json.dumps([len(m.faces)*3 for m in [ring]+arches]),html)
(out/'preview.html').write_text(html)
(out/'specs.json').write_text(json.dumps({'foot_region_z_mm':[2,6],'foot_shape':'intersection with original curved annular wall','ring_unchanged':True,'center_joint_unchanged':True,'triangles':len(assembly.faces),'smooth_shading':False,'decimated':False,'collision_free':True},indent=2))
print('Validated two connected arches; no overlaps. Triangles:',len(assembly.faces))
