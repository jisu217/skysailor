from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
def box(size,pos):
 m=trimesh.creation.box(extents=size);m.apply_translation(pos);return m
# Carriage center x=40; adjustable x=25..55. Axle direction Y.
parts=[box([20,11,1.5],[40,0,8.25])]
for y in [-4.5,4.5]:
 parts.append(box([20,2,8.8],[40,y,3.1]))
 parts.append(box([20,3.1,1],[40,np.sign(y)*3,-.8]))
rollers=[]
for x in [33,47]:
 for ay in [-3,3]:
  axle=trimesh.creation.cylinder(radius=.7,height=4,sections=48)
  axle.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));axle.apply_translation([x,ay,4.5]);parts.append(axle)
 for y in [-1.9,1.9]:
  wheel=trimesh.creation.annulus(r_min=.9,r_max=2.5,height=1.4,sections=96)
  wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));wheel.apply_translation([x,y,4.5]);rollers.append(wheel)
body=trimesh.boolean.union(parts,engine='manifold')
assert body.is_volume and body.is_watertight
for x in [25,40,55]:
 test=body.copy();test.apply_translation([x-40,0,0])
 intersection=trimesh.boolean.intersection([base,test],engine='manifold')
 assert intersection.is_empty or abs(intersection.volume)<1e-5
body.export(out/'carriage-body-assembled.stl')
rollers[0].export(out/'roller-assembled.stl')
meshes=[base,body]+rollers
assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>X 롤러 이동부 · 이동량 30mm</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>X 롤러 이동부 · 이동량 30mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>배치 검토용 · 롤러 4개 Ø5mm · 아래 빠짐 방지 턱 · 중앙에서 25–55mm</small><div style="margin-top:16px"><label>X 위치 <input id="travel" type="range" min="25" max="55" value="40" step="0.1"><span id="position">40mm</span></label><button id="closeup">이동부 확대</button></div>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','assembly.stl')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
counts=[len(m.faces)*3 for m in meshes]
new='const moving=new T.Group();scene.add(moving);let offset=0;const counts='+json.dumps(counts)+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;const part=new T.Mesh(geom,new T.MeshStandardMaterial({color:i===0?0x85c9de:i===1?0xf0b66b:0x455568,roughness:.5,flatShading:true}));if(i===0)scene.add(part);else moving.add(part)});'''
assert old in s;s=s.replace(old,new)
s=s.replace("update();document.querySelector('#status')", "document.querySelector('#travel').oninput=e=>{moving.position.x=Number(e.target.value)-40;document.querySelector('#position').textContent=e.target.value+'mm';update()};document.querySelector('#closeup').onclick=()=>{target.set(40+moving.position.x,0,3);d=70;az=-1.1;el=.6;update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(30,Math.min')
(out/'preview.html').write_text(s)
print('Validated carriage clearance at travel start, middle and end; preview slider ready.')
