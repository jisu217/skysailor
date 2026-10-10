from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-240-cross-base'
original=trimesh.load(source/'ring-240-cross-base.stl',force='mesh')
# Shift the full original assembly up 1 mm and fill the underside.
raised=original.copy();raised.apply_translation([0,0,1])
base=trimesh.creation.annulus(r_min=117,r_max=120,height=2,sections=1440)
base.apply_translation([0,0,1])
parts=[raised,base]
for dims in ([238,3,2],[3,238,2]):
    plate=trimesh.creation.box(extents=dims)
    plate.apply_translation([0,0,1]);parts.append(plate)
result=trimesh.boolean.union(parts,engine='manifold')
path=out/'ring-240-cross-base-2mm.stl';result.export(path)
saved=trimesh.load(path,force='mesh')
saved.merge_vertices(digits_vertex=5)
saved.update_faces(saved.nondegenerate_faces())
saved.update_faces(saved.unique_faces())
saved.remove_unreferenced_vertices()
saved.export(path)
saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds,[[-120,-120,0],[120,120,3]])
# The portion above the new floor must match the original raised details.
cutter=trimesh.creation.box(extents=[250,250,2]);cutter.apply_translation([0,0,3])
top=trimesh.boolean.intersection([saved,cutter],engine='manifold')
expected=trimesh.boolean.intersection([raised,cutter],engine='manifold')
assert abs(top.volume-expected.volume)<.01
s=(source/'preview.html').read_text()
a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('240mm 링 · +자 바닥판','240mm 링 · 바닥 두께 2mm')
s=re.sub(r'<small>.*?</small>','<small>외경 240mm · 전체 높이 3mm · 바닥 / +자 판 두께 2mm · 폭 3mm · 벽 / 받침 두께 1mm · 받침 8개</small>',s)
s=s.replace('ring-240-cross-base.stl','ring-240-cross-base-2mm.stl')
s=s.replace('M30 80H180V20H130V50H30Z','M30 90H180V10H130V37H30Z').replace('M30 50L130 20V50Z','M30 37L130 10V37Z').replace('y="14"','y="9"')
s=s.replace('단면은 이해를 위해 확대 표시','바닥 2mm + 위쪽 턱 1mm · 단면 확대')
(out/'preview.html').write_text(s)
spec={'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'watertight':True,'solids':1,'height_mm':3,'floor_mm':2}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
print(json.dumps(spec))
