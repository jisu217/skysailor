from pathlib import Path
import trimesh,numpy as np,json,re,math,shutil
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-double-disc-taller-center'
base=trimesh.load(src/'frame.stl',force='mesh');moving=trimesh.load(src/'double-disc-assembled.stl',force='mesh')
turn=trimesh.geometry.align_vectors([0,0,1],[1,0,0])
def cx(r,l,x,z):
 m=trimesh.creation.cylinder(radius=r,height=l,sections=192);m.apply_transform(turn);m.apply_translation([x,0,z]);return m
worm=trimesh.load(root/'worm-v2-short/worm-v2-short-bore-1.20mm.stl',force='mesh');worm.apply_transform(turn);worm.apply_translation([5.7,0,5.5])
# z=6 with OD8 places tooth envelope at fixed annulus top z=2.
moving=trimesh.boolean.difference([moving,cx(4.2,8.4,9.7,5.5),cx(3.2,15.4,-2,5.5)],engine='manifold')
# Open the upper disc in front of the worm, through to its outside edge.
front=trimesh.creation.box(extents=[12,8.4,2.4]);front.apply_translation([15.7,0,3.2])
moving=trimesh.boolean.difference([moving,front],engine='manifold')
assert moving.is_volume and moving.is_watertight and len(moving.split())==1
# Trial tooth-shaped grooves: repeated at one lead, with 0.1 radial allowance.
cutters=[]
for offset in [-2.5,0,2.5]:
 c=worm.copy();c.vertices[:,1]*=1.025;c.vertices[:,2]=5.5+(c.vertices[:,2]-5.5)*1.025;c.apply_translation([offset,0,0]);cutters.append(c)
base=trimesh.boolean.difference([base]+cutters,engine='manifold')
assert base.is_volume and base.is_watertight
base.export(out/'fixed-frame-trial-rack.stl')

for part in [base,moving]:
 hit=trimesh.boolean.intersection([part,worm],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
moving.export(out/'moving-discs-worm-clearance.stl');worm.export(out/'worm-assembled.stl')
shutil.copy2(root/'worm-v2-short/worm-v2-short-bore-1.20mm.stl',out/'worm-bore-1.20mm.stl')
meshes=[base,moving,worm];assembly=trimesh.util.concatenate(meshes)
s=(root/'ring-380-moving-worm-615/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
a=s.index('g.clearGroups()');b=s.index('scene.add(new T.HemisphereLight',a)
s=s[:a]+'''let offset=0;const counts='''+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xb3c6dd][i],roughness:.45,flatShading:true}))) });
function cylX(r,len,x,z,color){const m=new T.Mesh(new T.CylinderGeometry(r,r,len,64),new T.MeshStandardMaterial({color,roughness:.45}));m.rotation.z=Math.PI/2;m.position.set(x,0,z);scene.add(m)}
cylX(3,15,-2,5.5,0x66768b);cylX(.6,3,6.9,5.5,0xd2d7dd);
'''+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>웜 앞쪽 개방 · 이동 원판</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>웜 앞쪽 가장자리 개방 · 모터–웜 간격 0.2mm · 고정판은 기존 시험 홈 / 전체 이동용 치형 미설계</small>',s)
s=s.replace('</nav>','<a href="worm-bore-1.20mm.stl" download>웜 STL</a><a href="moving-discs-worm-clearance.stl" download>이동 원판 STL</a></nav>')
(out/'preview.html').write_text(s)
assert np.max(np.linalg.norm(worm.vertices[:,:2],axis=1))<14.5
print(json.dumps({'worm_max_plan_radius_mm':float(np.max(np.linalg.norm(worm.vertices[:,:2],axis=1))),'disc_radius_mm':14.5,'motor_worm_gap_mm':.2,'worm_x_range':worm.bounds[:,0].tolist()}))
