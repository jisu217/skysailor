from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-cross-arches-06x3'
base=trimesh.load(source/'ring-380-cross-arches-06x3.stl',force='mesh')
# Centered upright webs: 1 mm thick, 8 mm above the 2 mm floor.
# Extend into the outer wall, with a 0.05 mm floor overlap for robust union.
parts=[base]
for dims in ([379,1,8.05],[1,379,8.05]):
 web=trimesh.creation.box(extents=dims)
 web.apply_translation([0,0,5.975]);parts.append(web)
mesh=trimesh.boolean.union(parts,engine='manifold')
mesh.merge_vertices(digits_vertex=5);mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
path=out/'ring-380-cross-t-webs.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds,base.bounds)
assert saved.volume>base.volume
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('380mm 링 · Ø430 교차 리브 2개','380mm 링 · ㅗ자 단면 보강')
s=re.sub(r'<small>.*?</small>','<small>+자 바닥 폭 3mm / 두께 2mm · 중앙 세로 벽 두께 1mm / 바닥 위 높이 8mm · 교차 리브 0.6 × 3mm</small>',s)
s=s.replace('ring-380-cross-arches-06x3.stl','ring-380-cross-t-webs.stl')
(out/'preview.html').write_text(s)
spec={'web_thickness_mm':1,'web_height_above_floor_mm':8,'floor_thickness_mm':2,'T_section_total_height_mm':10,'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'watertight':True,'connected_solids':1}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
