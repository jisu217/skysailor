from pathlib import Path
import json,shutil
import numpy as np
import trimesh
import manifold3d
out=Path(__file__).resolve().parent;src=out.parent
names=['ring-print.stl','mid-ring-print.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','post-1-print.stl','post-2-print.stl']
results=[];meshes=[]
np.random.seed(24)
for name in names:
 original=trimesh.load(src/name,force='mesh');original.process(validate=True)
 before=len(original.faces)
 if before<1000:
  m=original.copy();err=0;volerr=0
 else:
  raw=manifold3d.Mesh(np.asarray(original.vertices,dtype=np.float32),np.asarray(original.faces,dtype=np.uint32),tolerance=1e-5)
  raw.merge()
  solid=manifold3d.Manifold(raw)
  assert solid.status()==manifold3d.Error.NoError,(name,solid.status())
  reduced=solid.simplify(.004 if name=='mid-ring-print.stl' else .015).to_mesh()
  m=trimesh.Trimesh(vertices=np.asarray(reduced.vert_properties)[:,:3],faces=np.asarray(reduced.tri_verts),process=True)
  idx=np.linspace(0,len(original.vertices)-1,min(4000,len(original.vertices)),dtype=int)
  pts=np.vstack((original.vertices[idx],original.sample(4000)))
  err=float(trimesh.proximity.closest_point(m,pts)[1].max())
  volerr=float(abs(m.volume/original.volume-1))
  assert m.is_watertight and m.is_volume,(name,'not watertight')
  assert err<.025 and volerr<.002,(name,err,volerr)
 m.apply_translation([0,0,-m.bounds[0,2]])
 m.export(out/name)
 check=trimesh.load(out/name,force='mesh');check.process(validate=True)
 assert check.is_watertight and check.is_volume
 results.append({'file':name,'original_triangles':before,'simplified_triangles':len(m.faces),'sampled_max_surface_error_mm':err,'volume_difference_percent':volerr*100})
 meshes.append(m)
 print(json.dumps(results[-1]),flush=True)
# Reproduce the three non-overlapping print layouts.
for m in meshes:m.apply_translation(-m.bounds[0])
meshes[0].export(out/'plate-1-base.stl')
p1=meshes[4].copy();p1.apply_translation([148,0,0]);p2=meshes[5].copy();p2.apply_translation([162,0,0])
trimesh.util.concatenate([meshes[1],p1,p2]).export(out/'plate-2-ring-and-posts.stl')
a2=meshes[3].copy();a2.apply_translation([0,meshes[2].extents[1]+6,0])
trimesh.util.concatenate([meshes[2],a2]).export(out/'plate-3-arches.stl')
(out/'validation.json').write_text(json.dumps(results,indent=2))
import zipfile
with zipfile.ZipFile(out/'simplified-print-plates.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['plate-1-base.stl','plate-2-ring-and-posts.stl','plate-3-arches.stl']:z.write(out/n,n)
print('TOTAL',sum(r['original_triangles'] for r in results),sum(r['simplified_triangles'] for r in results),flush=True)
