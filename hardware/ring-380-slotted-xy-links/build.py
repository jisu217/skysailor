from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-matched-xy-links'
base=trimesh.load(src/'frame.stl',force='mesh')
parts=[]
for name,z,angle in [('x-slider',-2.7,0),('y-slider',-4.7,math.pi/2)]:
 m=trimesh.load(src/(name+'.stl'),force='mesh')
 mid=trimesh.creation.box(extents=[37,3,1.4]);mid.apply_translation([0,0,z]);cutters=[mid]
 for x in [-18.5,18.5]:
  c=trimesh.creation.cylinder(radius=1.5,height=1.4,sections=96);c.apply_translation([x,0,z]);cutters.append(c)
 cut=trimesh.boolean.union(cutters,engine='manifold')
 cut.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]))
 m=trimesh.boolean.difference([m,cut],engine='manifold')
 assert m.is_watertight and m.is_volume and len(m.split())==1
 m.export(out/(name+'.stl'));parts.append(m)
base.export(out/'frame.stl')
meshes=[base]+parts;assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>XY 연결판 · 중앙 긴 슬롯</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>슬롯 각 40 × 3mm / 둥근 끝 · 연결판 두께 1mm · X/Y 높이 차 2mm · 이동 각 ±14mm</small>',s)
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
(out/'preview.html').write_text(s)
print('Both 40 x 3 mm slots cut; each slider remains one watertight solid.')
