from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-center-support35'
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
def sphere(r,z):
 m=trimesh.creation.icosphere(subdivisions=4,radius=r);m.apply_translation([0,0,z]);return m
frame=trimesh.load(src/'frame-support35-lip2.stl',force='mesh');top=float(frame.bounds[1,2]);floor=top-2
# Replace the crossing center with a common annular crown.
frame=trimesh.boolean.difference([frame,cyl(6,16,top)],engine='manifold')
eye=trimesh.creation.annulus(r_min=2.5,r_max=6,height=2,sections=192);eye.apply_translation([0,0,top-1])
frame=trimesh.boolean.union([frame,eye],engine='manifold')
# Upper cap has a blind socket receiving the lower cap's cylindrical post.
upper=cyl(7,1.5,top+.85)
upper=trimesh.boolean.difference([upper,cyl(2.5,1.3,top+.35)],engine='manifold')
rim=trimesh.creation.annulus(r_min=13,r_max=15,height=1.2,sections=192);rim.apply_translation([0,0,floor-.7])
spokes=[]
for angle in [np.pi/4,3*np.pi/4]:
 m=box([28,3,1.2],[0,0,floor-.7]);m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));spokes.append(m)
lower=trimesh.boolean.union([rim,cyl(4,1.2,floor-.7),cyl(2.3,4,floor+.7)]+spokes,engine='manifold')
# Four compact snap sockets under the diagonal corners of the cap.
bz=floor-5.5
outer=trimesh.boolean.difference([sphere(3.4,bz),sphere(2.7,bz)],engine='manifold')
fingers=[]
for i in range(4):
 shoe=trimesh.boolean.intersection([outer,box([4,1.4,3.2],[2,0,bz+.3])],engine='manifold')
 arm=box([.8,1.4,4.3],[3,0,bz+2.3])
 f=trimesh.boolean.union([shoe,arm],engine='manifold')
 f.apply_transform(trimesh.transformations.rotation_matrix(i*np.pi/2,[0,0,1]));fingers.append(f)
socket=trimesh.util.concatenate(fingers)
balls=[];sockets=[]
for i in range(4):
 angle=np.pi/4+i*np.pi/2;p=[11*np.cos(angle),11*np.sin(angle),0]
 sock=socket.copy();sock.apply_translation(p);sockets.append(sock)
 ball=trimesh.boolean.union([sphere(2.5,bz),cyl(.9,4,bz-3.5)],engine='manifold');ball.apply_translation(p);balls.append(ball)
lower=trimesh.boolean.union([lower]+sockets,engine='manifold')
meshes=[frame,upper,lower]+balls;names=['frame-annular-crown','upper-cap','lower-cap-four-corner-sockets']+[f'ball-short-stub-{i+1}' for i in range(4)]
for name,m in zip(names,meshes):
 assert m.is_volume and m.is_watertight and len(m.split())==1,name
 m.export(out/(name+'.stl'))
for a,b in [(frame,upper),(frame,lower),(upper,lower)]+[(ball,lower) for ball in balls]:
 h=trimesh.boolean.intersection([a,b],engine='manifold');assert h.is_empty or abs(h.volume)<.001
# Concept: paired links to two nested orthogonal hinge stages.
def beam(a,b,r):
 a=np.array(a);b=np.array(b);m=trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=48);m.apply_transform(trimesh.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);return m
rotation=trimesh.transformations.rotation_matrix(np.pi/4,[0,0,1])
def rotated(m):
 m.apply_transform(rotation);return m
# Outer frame and inner plate shown in neutral pose, with distinct hinge axes.
gz=11
middle=trimesh.creation.annulus(r_min=8.8,r_max=13,height=2,sections=128);middle.apply_translation([0,0,gz]);middle=rotated(middle)
payload=rotated(box([15,15,1.2],[0,0,gz]))
# Two orthogonal pivot axes; holes include radial clearance.
ax_x=rotated(beam([-14,0,gz],[14,0,gz],.8))
ax_y=rotated(beam([0,-10,gz],[0,10,gz],.8))
cutx=rotated(beam([-15,0,gz],[15,0,gz],1))
cuty=rotated(beam([0,-15,gz],[0,15,gz],1))
middle=trimesh.boolean.difference([middle,cutx,cuty],engine='manifold')
# Keep only axle tips, leaving the center open for the inner stage.
ax_x=trimesh.boolean.difference([ax_x,cyl(10,5,gz)],engine='manifold')
payload=trimesh.boolean.union([payload,ax_y],engine='manifold')
links=[];end_hinges=[]
for i in range(4):
 angle=np.pi/4+i*np.pi/2;rad=np.array([np.cos(angle),np.sin(angle),0]);tangent=np.array([-np.sin(angle),np.cos(angle),0])
 # Opposite pairs land on different stages; actual actuation is not yet defined.
 radius=11 if i%2==0 else 7
 bottom=rad*radius+np.array([0,0,gz+2])
 top_p=rad*11+np.array([0,0,bz-4])
 links.append(beam(top_p,bottom,.75))
 end_hinges.append(beam(bottom-tangent*2,bottom+tangent*2,.9))
 # Clevis-style visual bracket below each rod endpoint.
 for side in [-1,1]:
  p=bottom+tangent*side*1.7
  end_hinges.append(box([1.2,1.2,2],[p[0],p[1],gz+1.5]))
extra=[middle,ax_x,payload,trimesh.util.concatenate(links),trimesh.util.concatenate(end_hinges)]
meshes+=extra
names+=['middle-x-frame','x-pivot-stubs','inner-y-platform','paired-long-links','lower-hinge-layout']
for n,m in zip(names[-5:],extra):m.export(out/(n+'.stl'))
assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xc7a1dd,0x9fd8b0,0x9fd8b0,0x9fd8b0,0x9fd8b0,0xffad75,0xb3c6dd,0x9fd8b0,0xffd166,0xb3c6dd][i],roughness:.45,flatShading:true}))) });'''
assert old in s;s=s.replace(old,new)
s=re.sub(r'<h1>.*?</h1>','<h1>Ø30 X보강 캡 + 두 쌍 연결봉 + 중첩 힌지</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>상부 Ø30 / 외곽 링 폭2 / X보강 폭3 / 두께1.2 · 구관절4개 Ø5 · 두 쌍 연결봉 · 아래 중간 프레임 + 직교 힌지 하중판 · 배치 검토용: 힌지 고정·구동·전체 운동 검증 전 / 출력용 아님</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav></nav>',s,flags=re.S)
(out/'preview.html').write_text(s);print('Validated crown, enlarged lower cap, four claws and neutral pose clearances.')
