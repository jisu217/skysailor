from pathlib import Path
import numpy as np,trimesh,json
out=Path(__file__).resolve().parent
src=out.parent/'rail-dome-rim-v1'
base=trimesh.load(src/'dome-with-L-rim.stl',force='mesh');base.process(validate=True)
# Curved rectangular ribs; top overlaps dome inner surface by 0.2 mm.
# Bottom projects 5mm into cavity measured vertically. Ends merge into rim.
R=199.;zc=-160.;width=1.6;projection=5.
xs=np.linspace(-117.8,117.8,601);verts=[]
for x in xs:
 for y,zoffset in [(-.8,-projection),(.8,-projection),(-.8,.2),(.8,.2)]:
  z=zc+np.sqrt(R*R-x*x-y*y)+zoffset
  verts.append([x,y,z])
faces=[]
for i in range(len(xs)-1):
 a=4*i;b=a+4
 for q in [(0,1),(1,3),(3,2),(2,0)]:
  u,v=q;faces.extend([[a+u,b+u,b+v],[a+u,b+v,a+v]])
faces.extend([[0,2,3],[0,3,1]])
a=4*(len(xs)-1);faces.extend([[a,a+1,a+3],[a,a+3,a+2]])
rib=trimesh.Trimesh(verts,faces,process=True);rib.fix_normals();assert rib.is_volume
ribs=[]
for angle in [np.pi/4,3*np.pi/4]:
 m=rib.copy();m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));ribs.append(m)
x=trimesh.boolean.union(ribs,engine='manifold');x.process(validate=True)
combined=trimesh.boolean.union([base,x],engine='manifold');combined.process(validate=True)
assert combined.is_watertight and combined.is_volume and len(combined.split())==1
combined.export(out/'dome-rim-X-ribs.stl');x.export(out/'X-ribs.stl')
html=(src/'assembly-preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':np.round(combined.vertices,5).tolist(),'faces':combined.faces.tolist()})+html[b:]
html=html.replace('02 · 돔 + ㄴ자 테두리','03 · 돔 곡면 X자 보강대').replace('지름 240 mm · 테두리 5 × 5 mm · 틀 두께 1.6 mm','지름 240 mm · X자 폭 1.6 mm · 아래 돌출 5 mm').replace('dome-with-L-rim.stl','dome-rim-X-ribs.stl')
html=html.replace('<details><summary>ⓘ</summary><p>','<details><summary>ⓘ</summary><p>X자 보강대는 돔 내부 곡면을 따라가며 중앙에서 교차하고 네 끝이 둘레 틀에 연결됩니다. 폭 1.6mm, 수직 방향 안쪽 돌출 5mm입니다. 회전축이나 레일은 아직 추가하지 않았습니다.<br>')
html=html.replace('let az=-1.1,el=.48','let az=-1.1,el=-.48')
(out/'assembly-preview.html').write_text(html)
spec={'rib_width_mm':1.6,'rib_vertical_projection_mm':5,'triangles':len(combined.faces),'watertight':bool(combined.is_watertight),'connected_solids':len(combined.split())}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(spec)
