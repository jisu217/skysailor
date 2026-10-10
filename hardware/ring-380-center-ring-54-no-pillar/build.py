from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-cross-t-webs-low'
base=trimesh.load(source/'ring-380-cross-t-webs-low.stl',force='mesh')

import math
R=215.; inner=214.4; angle=math.asin(190/R); cz=2-math.sqrt(R*R-190**2); n=720
t=np.linspace(-angle,angle,n+1)
profile=[(R*math.sin(a),cz+R*math.cos(a)) for a in t]+[(inner*math.sin(a),cz+inner*math.cos(a)) for a in t[::-1]]
m=len(profile);v=[(x,y,z) for y in [-1.5,1.5] for x,z in profile];f=[]
for i in range(n):
 a,b=i,i+1;c,d=2*n-i,2*n+1-i
 f.extend([(a,b,c),(a,c,d),(m+a,m+c,m+b),(m+a,m+d,m+c)])
for i in range(m):
 j=(i+1)%m;f.extend([(i,m+i,m+j),(i,m+j,j)])
arch=trimesh.Trimesh(vertices=v,faces=f);arch.fix_normals();parts=[base]
for deg in [45,135]:
 rib=arch.copy();rib.apply_transform(trimesh.transformations.rotation_matrix(math.radians(deg),[0,0,1]));parts.append(rib)
base=trimesh.boolean.union(parts,engine='manifold')

# Remove the upright cross webs within the new platform, preserving the pillar.
web_clear=trimesh.creation.cylinder(radius=27,height=2.01,sections=512)
web_clear.apply_translation([0,0,3.005]) # z=2..4.01
base=trimesh.boolean.difference([base,web_clear],engine='manifold')
floor=trimesh.creation.annulus(r_min=12.5,r_max=27,height=2,sections=512)
floor.apply_translation([0,0,1])
wall=trimesh.creation.annulus(r_min=25.4,r_max=27,height=2.05,sections=512)
wall.apply_translation([0,0,2.975])
mesh=trimesh.boolean.union([base,floor,wall],engine='manifold')
# Clear the full central opening, including crossing floor and pillar foot.
hole=trimesh.creation.cylinder(radius=12.5,height=4.02,sections=512)
hole.apply_translation([0,0,2])
mesh=trimesh.boolean.difference([mesh,hole],engine='manifold')
path=out/'ring-380-center-ring-54-no-pillar.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
saved.merge_vertices(digits_vertex=5);saved.update_faces(saved.nondegenerate_faces());saved.update_faces(saved.unique_faces());saved.remove_unreferenced_vertices();saved.fill_holes()
saved.export(path);saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>중앙 링 Ø54 / 구멍 Ø25</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>중앙 링 Ø54 / 구멍 Ø25</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>중앙 기둥 없음 · 중앙 링 외경 54mm · 관통 구멍 25mm · 바닥 2mm · 둘레 벽 두께 1.6mm / 높이 2mm</small>',s)
s=s.replace('ring-380-cross-t-webs-low.stl','ring-380-center-ring-54-no-pillar.stl')
(out/'preview.html').write_text(s)
print(json.dumps({'volume_cm3':saved.volume/1000,'watertight':True,'solids':1}))
