from pathlib import Path
import json,re,math
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-240-cross-base-2mm'
# L profile: outer radius 190, floor radial width 3, floor thickness 2.
n=1440
profile=[(190,0),(190,3),(189,3),(189,2),(187,2),(187,0)]
vertices=[(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for r,z in profile for i in range(n)]
faces=[]
for k in range(6):
 for i in range(n):
  j=(i+1)%n;l=(k+1)%6
  a,b,c,d=k*n+i,k*n+j,l*n+j,l*n+i
  faces.extend([(a,b,c),(a,c,d)])
parts=[trimesh.Trimesh(vertices=vertices,faces=faces)]
for dims in ([378,3,2],[3,378,2]):
 plate=trimesh.creation.box(extents=dims);plate.apply_translation([0,0,1]);parts.append(plate)
for i in range(8):
 v=[[r,y,z] for y in [-.5,.5] for r,z in [(186.9,1.95),(189.1,1.95),(189.1,3.)]]
 f=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
 wedge=trimesh.Trimesh(vertices=v,faces=f);wedge.fix_normals()
 wedge.apply_transform(trimesh.transformations.rotation_matrix(i*math.pi/4,[0,0,1]));parts.append(wedge)
mesh=trimesh.boolean.union(parts,engine='manifold')
mesh.merge_vertices(digits_vertex=5);mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
path=out/'ring-380-cross-base-2mm.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds,[[-190,-190,0],[190,190,3]])
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('240mm','380mm').replace('ring-240-cross-base-2mm.stl','ring-380-cross-base-2mm.stl').replace('d=480','d=760').replace('Math.min(1000,d*','Math.min(1600,d*')
(out/'preview.html').write_text(s)
spec={'outer_diameter_mm':380,'floor_width_mm':3,'floor_thickness_mm':2,'total_height_mm':3,'gussets':8,'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'watertight':True}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
