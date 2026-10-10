from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
# Remove the upright cross webs within the new platform, preserving the pillar.
web_clear=trimesh.creation.annulus(r_min=1.51,r_max=26,height=2.01,sections=256)
web_clear.apply_translation([0,0,3.005]) # z=2..4.01
base=trimesh.boolean.difference([base,web_clear],engine='manifold')
floor=trimesh.creation.annulus(r_min=12.5,r_max=26,height=2,sections=512)
floor.apply_translation([0,0,1])
wall=trimesh.creation.annulus(r_min=24.4,r_max=26,height=2.05,sections=512)
wall.apply_translation([0,0,2.975])
mesh=trimesh.boolean.union([base,floor,wall],engine='manifold')
# Clear the full central opening, including crossing floor and pillar foot.
hole=trimesh.creation.cylinder(radius=12.5,height=4.02,sections=512)
hole.apply_translation([0,0,2])
mesh=trimesh.boolean.difference([mesh,hole],engine='manifold')
path=out/'ring-380-center-ring-52-25.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
saved.merge_vertices(digits_vertex=5);saved.update_faces(saved.nondegenerate_faces());saved.update_faces(saved.unique_faces());saved.remove_unreferenced_vertices();saved.fill_holes()
saved.export(path);saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>중앙 링 Ø52 / 구멍 Ø25</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>중앙 링 Ø52 / 구멍 Ø25</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>중앙 링 외경 52mm · 관통 구멍 25mm · 바닥 2mm · 둘레 벽 두께 1.6mm / 높이 2mm</small>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','ring-380-center-ring-52-25.stl')
(out/'preview.html').write_text(s)
print(json.dumps({'volume_cm3':saved.volume/1000,'watertight':True,'solids':1}))
