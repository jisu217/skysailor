"""Four printable quarter solids with 1.6 mm seam ribs on each side."""
import runpy, json
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import box
out=Path(__file__).resolve().parent
base=runpy.run_path(str(out/'build.py'))
frame=base['frame']; disk=base['disk']; sphere=290.; thickness=1.2
# Pair of mating ribs at each seam: 3.2 mm assembled width.
frame=frame.union(box(-1.6,-201,1.6,201).intersection(disk)).union(box(-201,-1.6,201,1.6).intersection(disk))
scene=trimesh.Scene(); records=[]
for i,(sx,sy) in enumerate([(1,1),(-1,1),(-1,-1),(1,-1)],1):
 region=box(0 if sx>0 else -201,0 if sy>0 else -201,201 if sx>0 else 0,201 if sy>0 else 0)
 shape=frame.intersection(region).simplify(0.00001,preserve_topology=True)
 assert shape.geom_type=='Polygon'
 m=trimesh.creation.extrude_polygon(shape,height=thickness,engine='earcut')
 v,f=trimesh.remesh.subdivide_to_size(m.vertices,m.faces,max_edge=3,max_iter=12)
 top=np.maximum(thickness,np.sqrt(sphere*sphere-v[:,0]**2-v[:,1]**2)-210)
 v[:,2]+=top-thickness
 m=trimesh.Trimesh(v,f,process=True);m.fix_normals()
 assert m.is_watertight and m.is_volume and len(m.split())==1
 name=f'quarter-{i}'
 m.export(out/f'{name}.stl');m.export(out/f'{name}.glb')
 scene.add_geometry(m,node_name=name,geom_name=name)
 records.append(dict(name=name,offset=[sx*16,sy*16,0],size_mm=m.extents.tolist(),mass_PLA_g=m.volume/1000*1.24,watertight=True,components=1))
scene.export(out/'quarters.glb')
(out/'quarters.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records,indent=2))
