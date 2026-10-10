from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
disc=trimesh.creation.cylinder(radius=10.5,height=2,sections=256)
disc.apply_translation([0,0,1])
mesh=trimesh.boolean.union([base,disc],engine='manifold')
path=out/'ring-380-center-disc-21.stl'
mesh.export(path)
saved=trimesh.load(path,force='mesh')
saved.merge_vertices(digits_vertex=5)
saved.update_faces(saved.nondegenerate_faces());saved.update_faces(saved.unique_faces());saved.remove_unreferenced_vertices();saved.fill_holes()
saved.export(path);saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds,base.bounds)
assert saved.volume>base.volume
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>380mm 링 · 중앙 원판 Ø21mm</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>380mm 링 · 중앙 원판 Ø21mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>중앙 원판 Ø21mm / 두께 2mm · 바닥과 같은 높이 · 중앙 기둥 Ø3mm · 리브 4개</small>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','ring-380-center-disc-21.stl')
(out/'preview.html').write_text(s)
spec={'disc_diameter_mm':21,'disc_thickness_mm':2,'disc_bottom_z_mm':0,'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'watertight':True,'connected_solids':1}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
