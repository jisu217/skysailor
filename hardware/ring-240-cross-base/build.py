from pathlib import Path
import json
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-240-l-8-gussets'
base=trimesh.load(source/'ring-240-l-8-gussets.stl',force='mesh')
# Both plates occupy z=0..1, sharing the ring's flat underside.
parts=[base]
for extents in ([238,3,1],[3,238,1]):
    plate=trimesh.creation.box(extents=extents)
    plate.apply_translation([0,0,.5])
    parts.append(plate)
mesh=trimesh.boolean.union(parts,engine='manifold')
path=out/'ring-240-cross-base.stl'
mesh.export(path)
saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds,[[-120,-120,0],[120,120,2]])
assert saved.volume>base.volume
html=(source/'preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+html[b:]
html=html.replace('240mm ㄴ자 링 · 삼각 받침 8개','240mm 링 · +자 바닥판')
html=html.replace('받침 8개 / 두께 1mm','받침 8개 · +자 판 폭 3mm / 두께 1mm')
html=html.replace('ring-240-l-8-gussets.stl','ring-240-cross-base.stl')
(out/'preview.html').write_text(html)
print(json.dumps({'watertight':saved.is_watertight,'connected_solids':len(saved.split()),'volume_mm3':saved.volume,'extents_mm':saved.extents.tolist()}))
