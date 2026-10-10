from pathlib import Path
import json,math,re,shutil
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
src=out.parent/'ring-cross-arch-flat-base-v6'
ring=trimesh.load(out.parent/'ring-cross-arch-v5/ring-print.stl',force='mesh');ring.process(validate=True)
base=trimesh.creation.revolve([[94,0],[100,0],[100,2],[94,2],[94,0]],sections=1024)
ring=trimesh.boolean.union([ring,base],engine='manifold')
def box(size,center):
 m=trimesh.creation.box(size);m.apply_translation(center);return m
# Ring-side supports only: fill beneath the inward leaning wall.
# Each cheek is confined to the vertical projection of the inner wall, and z=2..6.
z=np.linspace(0,4,129);inner=np.sqrt(130**2-(math.sqrt(130**2-100**2)+z)**2)-2
# Small overlap into the wall/base for a robust fused solid.
profile=np.vstack(([[inner[-1],1.98],[inner[0]+.02,1.98]],np.column_stack((inner+.02,2+z)),[[inner[-1],6],[inner[-1],1.98]]))
wedge=trimesh.creation.revolve(profile,sections=1024)
cheeks=[]
for angle in (0,math.pi/2,math.pi,3*math.pi/2):
 rot=trimesh.transformations.rotation_matrix(angle,[0,0,1])
 for side in (-1,1):
  crop=box([12,2.4,6],[97,side*2.3,4]);crop.apply_transform(rot)
  m=trimesh.boolean.intersection([wedge,crop],engine='manifold')
  cheeks.append(m)
ring=trimesh.boolean.union([ring]+cheeks,engine='manifold')
assert ring.is_volume and ring.is_watertight and len(ring.split())==1
ring.export(out/'ring-print.stl')
arches=[]
for label in ('A-top-slot','B-bottom-slot'):
 for pose in ('assembled','print'):
  name=f'arch-{label}-{pose}.stl';shutil.copy2(src/name,out/name)
  assert (src/name).read_bytes()==(out/name).read_bytes()
 m=trimesh.load(src/f'arch-{label}-assembled.stl',force='mesh');m.process(validate=True);arches.append(m)
for arch in arches:
 for dz in (0,1,4,8):
  moved=arch.copy();moved.apply_translation([0,0,dz])
  overlap=trimesh.boolean.intersection([ring,moved],engine='manifold')
  assert not len(overlap.faces) or abs(overlap.volume)<.001
assembly=trimesh.util.concatenate([ring]+arches)
html=(src/'preview.html').read_text();p=html.index('const data=');q=html.index(';\nif(!window.THREE)',p)
html=html[:p]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[q:]
html=re.sub(r'<h1>.*?</h1>','<h1>십자 아치 · 링 경사 아래 받침</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>섀프트 v6 그대로 · 링 받침만 경사 아래에 추가 · {len(assembly.faces):,} 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>아치 A/B는 두 단계 전 v6 파일과 동일합니다.<br>파란 링의 네 접합부에만 경사 아래 공간을 채우는 받침을 추가했습니다.<br>받침은 경사 벽 아래에만 있으며 네모난 블록으로 위로 솟지 않습니다.<br>홈 폭 2.2mm, 중앙 반턱 홈과 평평한 링 바닥 유지.<br>전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]', 'const counts='+json.dumps([len(m.faces)*3 for m in [ring]+arches]),html)
(out/'preview.html').write_text(html)
(out/'specs.json').write_text(json.dumps({'arch_source':'v6 byte-identical STL','support_attached_to':'ring only','support_z_mm':[2,6],'support_inner_radius_mm':float(inner[-1]),'groove_width_mm':2.2,'support_total_tangential_width_mm':7,'triangles':len(assembly.faces),'smooth_shading':False,'decimated':False,'collision_free':True},indent=2))
print('Arches byte-identical to v6; ring supports added; insertion clear. Triangles:',len(assembly.faces))
