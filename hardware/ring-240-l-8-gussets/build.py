from pathlib import Path
import math, json, re, struct
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-240-l-section'
base=trimesh.load(source/'ring-240-l-section.stl',force='mesh')
parts=[base]
# Small overlaps embed each triangular plate in the floor and outer wall.
for i in range(8):
    vertices=[[r,y,z] for y in [-.5,.5] for r,z in [(116.9,.95),(119.1,.95),(119.1,2.)]]
    faces=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
    wedge=trimesh.Trimesh(vertices=vertices,faces=faces)
    wedge.fix_normals()
    wedge.apply_transform(trimesh.transformations.rotation_matrix(i*math.pi/4,[0,0,1]))
    parts.append(wedge)
ring=trimesh.boolean.union(parts,engine='manifold')
ring.export(out/'ring-240-l-8-gussets.stl')
saved=trimesh.load(out/'ring-240-l-8-gussets.stl',force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.extents,[240,240,2])
assert saved.volume>base.volume
s=(source/'preview.html').read_text()
a=s.index('const data=');z=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[z:]
s=s.replace('240mm ㄴ자 보강 링','240mm ㄴ자 링 · 삼각 받침 8개')
s=s.replace('벽 / 바닥 두께 1mm','벽 / 바닥 두께 1mm · 받침 8개 / 두께 1mm')
s=s.replace('ring-240-l-section.stl','ring-240-l-8-gussets.stl')
s=s.replace('단면 · 안쪽 ← → 바깥쪽','받침 단면 · 안쪽 ← → 바깥쪽')
s=s.replace('<path d="M30 80H180V20H130V50H30Z"','<path d="M30 50L130 20V50Z" fill="#f0b66b"/><path d="M30 80H180V20H130V50H30Z"')
(out/'preview.html').write_text(s)
print(json.dumps({'watertight':saved.is_watertight,'volume_mm3':saved.volume,'gussets':8,'bounds_mm':saved.extents.tolist()}))
