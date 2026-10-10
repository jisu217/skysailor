from pathlib import Path
import trimesh,numpy as np,json,re,math,shutil
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-double-disc-taller-center'
base=trimesh.load(src/'frame.stl',force='mesh');moving=trimesh.load(src/'double-disc-assembled.stl',force='mesh')
def cz(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=512);m.apply_translation([0,0,z]);return m
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Remove old center plate/wall while preserving the rest of the frame.
base=trimesh.boolean.difference([base,cz(28,7,2)],engine='manifold')
fixed=trimesh.creation.annulus(r_min=7.5,r_max=23.5,height=3,sections=512);fixed.apply_translation([0,0,.5])
restored=[]
for i in range(4):
 rot=trimesh.transformations.rotation_matrix(i*math.pi/2,[0,0,1])
 for m in [box([13.2,6,2],[21.5,0,1]),box([10.2,1.6,2],[23,0,3])]:
  m.apply_transform(rot);restored.append(m)
base=trimesh.boolean.union([base,fixed]+restored,engine='manifold')
wall=trimesh.creation.annulus(r_min=22.5,r_max=23.5,height=3.05,sections=512);wall.apply_translation([0,0,3.475])
base=trimesh.boolean.union([base,wall],engine='manifold')
# Clear upright cross webs inside the circular wall; retain floor at z=2.
base=trimesh.boolean.difference([base,cz(22.5,4,4)],engine='manifold')
moving=trimesh.boolean.union([cz(17.5,2,3.2),cz(17.5,2,-2.2),cz(2.5,3.6,.5)],engine='manifold')

turn=trimesh.geometry.align_vectors([0,0,1],[1,0,0])
def cx(r,l,x,z):
 m=trimesh.creation.cylinder(radius=r,height=l,sections=192);m.apply_transform(turn);m.apply_translation([x,0,z]);return m
worm=trimesh.load(root/'worm-v2-short/worm-v2-short-bore-1.20mm.stl',force='mesh');worm.apply_transform(turn);worm.apply_translation([5.7,0,5.5])
# z=6 with OD8 places tooth envelope at fixed annulus top z=2.
moving=trimesh.boolean.difference([moving,cx(4.2,8.4,9.7,5.5),cx(3.2,15.4,-2,5.5)],engine='manifold')
# Open the upper disc in front of the worm, through to its outside edge.
front=trimesh.creation.box(extents=[15,8.4,2.4]);front.apply_translation([13,0,3.2])
moving=trimesh.boolean.difference([moving,front],engine='manifold')
assert moving.is_volume and moving.is_watertight and len(moving.split())==1
# Single start lead 2.5mm: +5mm translation = +720deg rotation.
def pose(m,dx):
 c=m.copy();c.apply_transform(trimesh.transformations.rotation_matrix(2*math.pi*dx/2.5,[1,0,0],point=[0,0,5.5]));c.apply_translation([dx,0,0]);return c
cutters=[]
for dx in np.linspace(0,5,17):
 c=pose(worm,float(dx));c.vertices[:,1]*=1.025;c.vertices[:,2]=5.5+(c.vertices[:,2]-5.5)*1.025;cutters.append(c)
base=trimesh.boolean.difference([base]+cutters,engine='manifold')
checks=[]
for dx in np.linspace(0,5,21):
 w=pose(worm,float(dx));plate=moving.copy();plate.apply_translation([dx,0,0])
 h=trimesh.boolean.intersection([base,w],engine='manifold');v=0 if h.is_empty else abs(h.volume)
 h2=trimesh.boolean.intersection([base,plate],engine='manifold');v2=0 if h2.is_empty else abs(h2.volume)
 checks.append({'x_mm':float(dx),'worm_collision_mm3':v,'disc_collision_mm3':v2})
assert max(c['worm_collision_mm3'] for c in checks)<.001
assert max(c['disc_collision_mm3'] for c in checks)<.001
(out/'travel-checks.json').write_text(json.dumps({'range_mm':[0,5],'lead_mm':2.5,'rotation_degrees':720,'minimum_axial_overlap_mm':6.2,'checks':checks},indent=2))
assert base.is_volume and base.is_watertight
base.export(out/'fixed-frame-rack-travel5.stl')

for part in [base,moving]:
 hit=trimesh.boolean.intersection([part,worm],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
hit=trimesh.boolean.intersection([base,moving],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
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
s=re.sub(r'<h1>.*?</h1>','<h1>웜 회전 연동 홈 · 바깥쪽 이동 5mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>고정판 Ø47 / 두께 3mm / 둘레 벽 1mm × 높이 3mm / 내부 십자벽 없음 · 위아래 이동판 Ø35 / 두께 2mm · 중앙 구멍 Ø15 · 유격 0.2mm · 단일 축 0~5mm / 리드 2.5mm / 회전 720°</small>',s)
s=s.replace('<a href="fixed-frame-rack-travel5.stl" download>고정판 랙 STL</a></nav>','<a href="worm-bore-1.20mm.stl" download>웜 STL</a><a href="moving-discs-worm-clearance.stl" download>이동 원판 STL</a><a href="fixed-frame-rack-travel5.stl" download>고정판 랙 STL</a></nav>')
(out/'preview.html').write_text(s)
assert np.allclose(worm.bounds[:,0],[5.7,13.7])
print(json.dumps({'worm_max_plan_radius_mm':float(np.max(np.linalg.norm(worm.vertices[:,:2],axis=1))),'disc_radius_mm':17.5,'motor_worm_gap_mm':.2,'worm_x_range':worm.bounds[:,0].tolist()}))
