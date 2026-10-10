from pathlib import Path
import trimesh,numpy as np,json,re,math,shutil
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-double-disc-taller-center'
base=trimesh.load(src/'frame.stl',force='mesh');moving=trimesh.load(src/'double-disc-assembled.stl',force='mesh')
turn=trimesh.geometry.align_vectors([0,0,1],[1,0,0])
def cx(r,l,x,z):
 m=trimesh.creation.cylinder(radius=r,height=l,sections=192);m.apply_transform(turn);m.apply_translation([x,0,z]);return m
worm=trimesh.load(root/'worm-v1/worm-v1-bore-1.20mm.stl',force='mesh');worm.apply_transform(turn);worm.apply_translation([6,0,6])
# z=6 with OD8 places tooth envelope at fixed annulus top z=2.
moving=trimesh.boolean.difference([moving,cx(4.2,18.4,15,6),cx(3.2,15.4,-2,6)],engine='manifold')
assert moving.is_volume and moving.is_watertight and len(moving.split())==1
for part in [base,moving]:
 hit=trimesh.boolean.intersection([part,worm],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
moving.export(out/'moving-discs-worm-clearance.stl');worm.export(out/'worm-assembled.stl')
shutil.copy2(root/'worm-v1/worm-v1-bore-1.20mm.stl',out/'worm-bore-1.20mm.stl')
meshes=[base,moving,worm];assembly=trimesh.util.concatenate(meshes)
s=(root/'ring-380-moving-worm-615/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
a=s.index('g.clearGroups()');b=s.index('scene.add(new T.HemisphereLight',a)
s=s[:a]+'''let offset=0;const counts='''+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xb3c6dd][i],roughness:.45,flatShading:true}))) });
function cylX(r,len,x,z,color){const m=new T.Mesh(new T.CylinderGeometry(r,r,len,64),new T.MeshStandardMaterial({color,roughness:.45}));m.rotation.z=Math.PI/2;m.position.set(x,0,z);scene.add(m)}
cylX(3,15,-2,6,0x66768b);cylX(.6,5,7.5,6,0xd2d7dd);
'''+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>기존 웜 모델 Ø8 · 축 구멍 Ø1.2</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>웜 외경 8mm / 길이 18mm / 리드 4mm · 고정 원판 윗면 높이에 접촉 · 이동 원판 회전 여유 0.2mm · 랙 미설계</small>',s)
s=s.replace('</nav>','<a href="worm-bore-1.20mm.stl" download>웜 STL</a><a href="moving-discs-worm-clearance.stl" download>이동 원판 STL</a></nav>')
(out/'preview.html').write_text(s)
print('Existing bored worm reused unscaled; swept clearance cut; no worm/frame or worm/disc volume interference.')
