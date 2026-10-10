from pathlib import Path
import json,re,math
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent
src=out.parent/'ring-arch-pressfit-v3'
ring=trimesh.load(src/'ring-print.stl',force='mesh')
original=trimesh.load(out.parent/'ring-200-arch-matched-v2/ring-curved-wall.stl',force='mesh')
# Trim away added socket blocks, preserving the grooves within the original ring.
ring=trimesh.boolean.intersection([ring,original],engine='manifold')
# Restore the original continuous arch without added tongues or friction ribs.
# Use 4096 segments on each arc; no decimation.
R=130.
def arc(half):
 t=np.linspace(-math.asin(half/R),math.asin(half/R),4097)
 return np.column_stack((R*np.sin(t),R*np.cos(t)-math.sqrt(R*R-half*half)))
arch=trimesh.creation.extrude_polygon(Polygon(np.vstack((arc(100),arc(94)[::-1]))),height=2,engine='earcut')
arch.apply_transform(np.array([[1,0,0,0],[0,0,-1,1],[0,1,0,2],[0,0,0,1]]))
for name,m in [('ring-print',ring),('arch-assembled',arch)]:
 assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/(name+'.stl'))
flat=arch.copy();flat.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));flat.apply_translation([0,0,-flat.bounds[0,2]]);flat.export(out/'arch-print.stl')
overlap=trimesh.boolean.intersection([ring,arch],engine='manifold')
assert abs(overlap.volume)<.001
assembly=trimesh.util.concatenate([ring,arch])
html=(src/'preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>링 + 아치 · 발 돌기 제거</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>홈 유지 · 아치 두께 2mm · 전체 {len(assembly.faces):,}개 삼각형 · 스무딩 없음</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>양쪽 받침 블록을 제거하고 곡면 링의 홈을 유지했습니다.<br>아치의 추가 발 돌기와 마찰 돌기를 제거했습니다.<br>STL의 모든 삼각형을 표시하며, 면별 법선을 사용합니다. 정점 스무딩 없음.<br>홈 폭 2.2mm / 아치 두께 2mm. 돌기 제거로 마찰 고정은 없어집니다.</p></details>',html)
html=html.replace('const g=new T.BufferGeometry()','let g=new T.BufferGeometry()')
html=html.replace('g.computeVertexNormals();','g=g.toNonIndexed();g.computeVertexNormals();')
html=html.replace('roughness:.5,side:T.DoubleSide','roughness:.5,flatShading:true,side:T.DoubleSide')
html=re.sub(r'ringG.setDrawRange\(0,\d+\)',f'ringG.setDrawRange(0,{len(ring.faces)*3})',html)
html=re.sub(r'archG.setDrawRange\(\d+,\d+\)',f'archG.setDrawRange({len(ring.faces)*3},{len(arch.faces)*3})',html)
assert html.count('flatShading:true')==2
assert 'toNonIndexed()' in html
(out/'preview.html').write_text(html)
spec={'ring_triangles':len(ring.faces),'arch_triangles':len(arch.faces),'rendered_triangles':len(assembly.faces),'decimated':False,'smooth_shading':False,'arch_segments_per_arc':4096,'overlap_mm3':float(overlap.volume),'socket_blocks_removed':True}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
print(json.dumps(spec,indent=2))
