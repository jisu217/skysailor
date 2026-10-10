"""400 mm diameter / 80 mm cap. uv run --with trimesh --with shapely --with mapbox-earcut --with scipy build.py"""
from pathlib import Path
import json,math,argparse
import numpy as np
import trimesh
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
p=argparse.ArgumentParser();p.add_argument('--cell',type=float,default=32);p.add_argument('--rib',type=float,default=1.6);p.add_argument('--thickness',type=float,default=1.2);p.add_argument('--rim',type=float,default=3);a=p.parse_args()
assert a.cell>2*a.rib>0 and a.thickness>0 and a.rim>0
out=Path(__file__).resolve().parent
radius=200.;depth=80.;sphere=(radius**2+depth**2)/(2*depth)
disk=Point(0,0).buffer(radius,quad_segs=256);inside=Point(0,0).buffer(radius-a.rim,quad_segs=256)
side=a.cell/math.sqrt(3);holes=[]
# Shift a lattice vertex to the apex, ensuring a rib junction at the centre.
for q in range(-12,13):
 for r in range(-12,13):
  x=1.5*side*q-side;y=math.sqrt(3)*side*(r+q/2)
  poly=Polygon([(x+side*math.cos(k*math.pi/3),y+side*math.sin(k*math.pi/3)) for k in range(6)])
  hole=poly.buffer(-a.rib/2,join_style=2).intersection(inside)
  if not hole.is_empty and hole.area>2:holes.append(hole)
frame=disk.difference(unary_union(holes))
assert frame.geom_type=='Polygon'
mesh=trimesh.creation.extrude_polygon(frame,height=a.thickness,engine='earcut')
v,f=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=3,max_iter=12)
z=np.sqrt(sphere*sphere-v[:,0]**2-v[:,1]**2)-(sphere-depth)
# Outer 0.9 mm of the ring has a flat top to retain a printable, closed edge.
top=np.maximum(a.thickness,z)
v[:,2]=top-a.thickness+v[:,2]
mesh=trimesh.Trimesh(v,f,process=True);mesh.fix_normals()
assert mesh.is_watertight and mesh.is_volume and len(mesh.split())==1
mesh.export(out/'dome400-hex.stl');mesh.export(out/'dome400-hex.glb')
info=dict(diameter_mm=400,depth_mm=80,sphere_radius_mm=sphere,cell_flat_to_flat_projected_mm=a.cell,rib_projected_width_mm=a.rib,vertical_thickness_mm=a.thickness,rim_projected_width_mm=a.rim,holes=len(holes),volume_cm3=mesh.volume/1000,estimated_PLA_g=mesh.volume/1000*1.24,bounds_mm=mesh.bounds.tolist(),watertight=mesh.is_watertight,components=len(mesh.split()),note='Hexagons projected from XY onto sphere; not regular in surface metric. Outer rim lip locally flattened. Mass excludes film/glue. Full assembly, not split for printing.')
(out/'dimensions.json').write_text(json.dumps(info,indent=2));print(json.dumps(info,indent=2))
