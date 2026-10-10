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
lower=trimesh.boolean.union([cyl(10,1.2,floor-.7),cyl(2.3,4,floor+.7)],engine='manifold')
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
 angle=np.pi/4+i*np.pi/2;p=[6*np.cos(angle),6*np.sin(angle),0]
 sock=socket.copy();sock.apply_translation(p);sockets.append(sock)
 ball=trimesh.boolean.union([sphere(2.5,bz),cyl(.9,4,bz-3.5)],engine='manifold');ball.apply_translation(p);balls.append(ball)
lower=trimesh.boolean.union([lower]+sockets,engine='manifold')
meshes=[frame,upper,lower]+balls;names=['frame-annular-crown','upper-cap','lower-cap-four-corner-sockets']+[f'ball-short-stub-{i+1}' for i in range(4)]
for name,m in zip(names,meshes):
 assert m.is_volume and m.is_watertight and len(m.split())==1,name
 m.export(out/(name+'.stl'))
for a,b in [(frame,upper),(frame,lower),(upper,lower)]+[(ball,lower) for ball in balls]:
 h=trimesh.boolean.intersection([a,b],engine='manifold');assert h.is_empty or abs(h.volume)<.001
assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xc7a1dd,0x9fd8b0,0x9fd8b0,0x9fd8b0,0x9fd8b0][i],roughness:.45,flatShading:true}))) });'''
assert old in s;s=s.replace(old,new)
s=re.sub(r'<h1>.*?</h1>','<h1>꼭대기 캡 대각선 네 귀퉁이 구관절</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>아래 캡 Ø20 × 1.2mm · 대각선 구관절4개 / 배치 반경6mm / 구 Ø5 / 소켓 여유0.2mm · 짧은 연결부 Ø1.8 · 긴 기둥·중앙 구관절 제거 · 끼움 및 강도 미검증</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav>'+''.join('<a href="'+n+'.stl" download>'+n+'</a>' for n in names)+'</nav>',s,flags=re.S)
(out/'preview.html').write_text(s);print('Validated crown, enlarged lower cap, four claws and neutral pose clearances.')
