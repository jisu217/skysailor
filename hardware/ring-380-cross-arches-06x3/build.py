from pathlib import Path
import math,json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-cross-base-2mm'
base=trimesh.load(source/'ring-380-cross-base-2mm.stl',force='mesh')
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
second=arch.copy()
second.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1]))
mesh=trimesh.boolean.union([base,arch,second],engine='manifold')
mesh.merge_vertices(digits_vertex=5);mesh.update_faces(mesh.nondegenerate_faces());mesh.update_faces(mesh.unique_faces());mesh.remove_unreferenced_vertices()
path=out/'ring-380-cross-arches-06x3.stl';mesh.export(path)
saved=trimesh.load(path,force='mesh')
assert saved.is_watertight and saved.is_volume and len(saved.split())==1
assert np.allclose(saved.bounds[0],[-190,-190,0])
assert abs(saved.bounds[1,2]-(cz+R))<.001
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':saved.vertices.tolist(),'faces':saved.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('380mm 링 · 바닥 두께 2mm','380mm 링 · Ø430 교차 리브 2개')
s=re.sub(r'<small>.*?</small>','<small>링 외경 380mm · 리브 원 직경 430mm · 리브 2개 / 90° 교차 · 두께 0.6mm / 폭 3mm · 전체 높이 %.2fmm</small>'%(cz+R),s)
s=re.sub(r'<div style="margin-top:16px.*?</div></header>','</header>',s)
s=s.replace('ring-380-cross-base-2mm.stl','ring-380-cross-arches-06x3.stl').replace('new T.Vector3(0,0,1)','new T.Vector3(0,0,48)').replace('target.set(0,0,1)','target.set(0,0,48)').replace('d=760','d=820')
(out/'preview.html').write_text(s)
spec={'rib_count':2,'rib_angle_degrees':90,'circle_diameter_mm':430,'outer_arc_chord_mm':380,'rib_radial_thickness_mm':0.6,'rib_width_mm':3,'outer_arc_length_mm':2*angle*R,'centerline_arc_length_mm':2*angle*(R+inner)/2,'rise_above_floor_mm':R-math.sqrt(R*R-half*half),'total_height_mm':float(saved.bounds[1,2]),'volume_cm3':saved.volume/1000,'PLA_Basic_g':saved.volume/1000*1.24,'connected_solids':1,'watertight':True}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
