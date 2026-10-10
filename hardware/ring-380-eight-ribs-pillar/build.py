from pathlib import Path
import math,json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-cross-t-webs-low'
base=trimesh.load(source/'ring-380-cross-t-webs-low.stl',force='mesh')
# Outer arc is a 430 mm diameter circle, chord 380 mm at z=2.
# Radial thickness 0.6 mm; width along Y 3 mm.
R=215.; inner=214.4; half=190.; spring=2.
angle=math.asin(half/R);cz=spring-math.sqrt(R*R-half*half)
n=720
t=np.linspace(-angle,angle,n+1)
profile=[(R*math.sin(a),cz+R*math.cos(a)) for a in t]
profile += [(inner*math.sin(a),cz+inner*math.cos(a)) for a in t[::-1]]
m=len(profile)
v=[(x,y,z) for y in [-1.5,1.5] for x,z in profile]
f=[]
# Triangulate each flat side as strips between outer and inner arcs.
for i in range(n):
 a,b=i,i+1;c,d=2*n+1-(i+1),2*n+1-i
 f.extend([(a,b,c),(a,c,d),(m+a,m+c,m+b),(m+a,m+d,m+c)])
for i in range(m):
 j=(i+1)%m;f.extend([(i,m+i,m+j),(i,m+j,j)])
arch=trimesh.Trimesh(vertices=v,faces=f);arch.fix_normals()
assert arch.is_volume
parts=[base]
for degrees in [45,135]:
 rib=arch.copy()
 rib.apply_transform(trimesh.transformations.rotation_matrix(math.radians(degrees),[0,0,1]))
 parts.append(rib)
pillar=trimesh.creation.cylinder(radius=1.5,height=cz+R-2,sections=96)
pillar.apply_translation([0,0,2+(cz+R-2)/2])
parts.append(pillar)
mesh=trimesh.boolean.union(parts,engine='manifold')
mesh.merge_vertices(digits_vertex=5);mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
path=out/'ring-380-eight-ribs-pillar.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
saved.merge_vertices(digits_vertex=5)
saved.update_faces(saved.nondegenerate_faces())
saved.update_faces(saved.unique_faces())
saved.remove_unreferenced_vertices()
saved.fill_holes()
saved.export(path)
saved=trimesh.load(path,force="mesh")
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds[0],[-190,-190,0])
assert abs(saved.bounds[1,2]-(cz+R))<.001
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>380mm 링 · X 리브와 중앙 기둥</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>380mm 링 · X 리브와 중앙 기둥</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>리브 4개 / 45° 간격 · 리브 0.6 × 3mm · 중앙 기둥 Ø3mm · +자 바닥 폭 6mm / 두께 2mm · 세로 벽 1.6 × 2mm</small>',s)
s=s.replace('ring-380-cross-t-webs-low.stl','ring-380-eight-ribs-pillar.stl')
(out/'preview.html').write_text(s)
spec={'rib_count':4,'pillar_diameter_mm':3,'pillar_from_floor_height_mm':cz+R-2,'circle_diameter_mm':430,'outer_arc_chord_mm':380,'rib_radial_thickness_mm':0.6,'rib_width_mm':3,'outer_arc_length_mm':2*angle*R,'centerline_arc_length_mm':2*angle*(R+inner)/2,'rise_above_floor_mm':R-math.sqrt(R*R-half*half),'total_height_mm':float(saved.bounds[1,2]),'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'connected_solids':1,'watertight':True}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
