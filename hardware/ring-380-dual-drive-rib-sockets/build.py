from pathlib import Path
import trimesh,numpy as np,math,json,re,shutil
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-dual-motor-clips';kit=root/'rib-eight-eye032-connector'
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
base=trimesh.load(src/'fixed-frame-dual-racks.stl',force='mesh')
# Remove integrated arches above the base; replace with eight individual curved strips.
base=trimesh.boolean.difference([base,box([410,410,240],[0,0,126])],engine='manifold')
R=214.7;alpha=math.asin(190/215);L=R*alpha;zc=2-math.sqrt(215**2-190**2);top=zc+R
sleeves=[];slots=[];ribs=[]
for i in range(8):
 a=i*math.pi/4;rad=np.array([math.cos(a),math.sin(a),0]);width=np.array([-math.sin(a),math.cos(a),0]);tangent=-rad*math.cos(alpha)+np.array([0,0,math.sin(alpha)]);normal=np.cross(tangent,width)
 # Socket starts 0.8mm below rib tip along its insertion axis.
 tip=rad*(R*math.sin(alpha))+np.array([0,0,zc+R*math.cos(alpha)])
 origin=tip-.8*tangent
 mat=np.eye(4);mat[:3,:3]=np.column_stack([width,normal,tangent]);mat[:3,3]=origin
 shell=box([5,2.6,4],[0,0,2]);slot=box([3.4,1,4],[0,0,2.8]);shell.apply_transform(mat);slot.apply_transform(mat)
 sleeves.append(shell);slots.append(slot)
 # Bend original flat rib into assembled curve; stack crown eyes at 0.32mm pitch.
 rib=trimesh.load(kit/f'rib-eye-{0 if i%2==0 else 45}deg.stl',force='mesh')
 # Subdivide long flat strip triangles before bending.
 for _ in range(9):
  if max(np.linalg.norm(rib.vertices[rib.edges[:,0]]-rib.vertices[rib.edges[:,1]],axis=1))<2:break
  rib=trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(rib.vertices,rib.faces,max_edge=2,max_iter=10),process=True);break
 v=rib.vertices.copy();u=v[:,0];trans=v[:,1];h=v[:,2]
 theta=(L-u)/R;rr=(R+h-.3)*np.sin(theta);zz=zc+(R+h-.3)*np.cos(theta)+i*.32*np.clip(u/L,0,1)**8
 # Crown eye stays flat and horizontal.
 eye=(u-L)**2+trans**2<=16.00001
 rr[eye]=L-u[eye];zz[eye]=top-.3+h[eye]+i*.32
 rib.vertices=rr[:,None]*rad+trans[:,None]*width+zz[:,None]*np.array([0,0,1])
 rib.fix_normals();assert rib.is_watertight
 rib.export(out/f'rib-{i+1}-assembled.stl');ribs.append(rib)
base=trimesh.boolean.union([base]+sleeves,engine='manifold');base=trimesh.boolean.difference([base]+slots,engine='manifold');assert base.is_volume and base.is_watertight
# Remove eight disconnected tips left by the old integrated arches above the sockets.
base=max(base.split(),key=lambda m:m.volume)
assert base.is_volume and base.is_watertight
base.export(out/'frame-with-eight-rib-sockets.stl')
pin=trimesh.load(kit/'lower-square-pin.stl',force='mesh');pin.apply_translation([0,0,top-.3-1.2])
cap=trimesh.load(kit/'upper-square-cap.stl',force='mesh');cap.apply_transform(trimesh.transformations.rotation_matrix(math.pi,[1,0,0]));cap.apply_translation([0,0,top-.3+2.56+2])
pin.export(out/'crown-pin-assembled.stl');cap.export(out/'crown-cap-assembled.stl')
parts=[trimesh.load(src/n,force='mesh') for n in ['moving-discs-motor-clips.stl','worm-assembled.stl','lower-y-worm-assembled.stl']]
meshes=[base]+parts+ribs+[pin,cap];assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for m in meshes])+';counts',s)
s=s.replace('[0x85c9de,0xf0b66b,0xb3c6dd,0xb3c6dd][i]','[0x85c9de,0xf0b66b,0xb3c6dd,0xb3c6dd,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0xf0b66b,0xf0b66b][i]')
s=re.sub(r'<h1>.*?</h1>','<h1>리브 소켓 8개 + 꼭대기 원판 결합부 · XY 구동</h1>',s)
s=s.replace('</small>',' · 리브 소켓 3.4×1mm / 꼭대기 원판 Ø8×0.32mm 8장 / 사각핀 + 원형 캡</small>',1)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="frame-with-eight-rib-sockets.stl" download>소켓 포함 프레임 STL</a><a href="moving-discs-motor-clips.stl" download>모터 고정 이동판 STL</a></nav>',s,flags=re.S)
for n in ['moving-discs-motor-clips.stl','worm-assembled.stl','lower-y-worm-assembled.stl','worm-bore-1.20mm.stl']:shutil.copy2(src/n,out/n)
(out/'preview.html').write_text(s)
print('Built 8 sockets and 8 curved eye ribs, crown pin/cap. Motor clips retained.')
