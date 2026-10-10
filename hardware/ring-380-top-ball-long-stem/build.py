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
lower=trimesh.boolean.union([cyl(7,4.2,floor-2.2),cyl(2.3,4,floor+.7)],engine='manifold')
bz=floor-11
shell=sphere(6.2,bz)
shell=trimesh.boolean.difference([shell,sphere(5.2,bz),cyl(3.2,9,bz-4.5)],engine='manifold')
neck=cyl(3,2.5,bz+6.3)
lower=trimesh.boolean.union([lower,shell,neck],engine='manifold')
ball=trimesh.boolean.union([sphere(5,bz),cyl(1.5,bz-8,(bz+2)/2)],engine='manifold')
# Split socket/cap into two glueable halves so the ball can be installed.
left=trimesh.boolean.intersection([lower,box([30,40,50],[-15,0,bz])],engine='manifold')
right=trimesh.boolean.intersection([lower,box([30,40,50],[15,0,bz])],engine='manifold')
meshes=[frame,upper,left,right,ball];names=['frame-annular-crown','upper-cap','lower-cap-socket-left','lower-cap-socket-right','ball-and-stem']
for name,m in zip(names,meshes):
 assert m.is_volume and m.is_watertight and len(m.split())==1,name
 m.export(out/(name+'.stl'))
for a,b in [(frame,upper),(frame,lower),(ball,lower),(upper,lower)]:
 h=trimesh.boolean.intersection([a,b],engine='manifold');assert h.is_empty or abs(h.volume)<.001
assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xc7a1dd,0xc7a1dd,0x9fd8b0][i],roughness:.45,flatShading:true}))) });'''
assert old in s;s=s.replace(old,new)
s=re.sub(r'<h1>.*?</h1>','<h1>아래 캡 3mm 연장 · 구관절과 긴 막대</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>꼭대기 원판 Ø12 / 구멍 Ø5 / 두께2 · 위아래 캡 Ø14 / 아래 캡 두께4.2 · 구 Ø10 / 소켓 여유0.2 / 막대 Ø3 / 아래 끝 z=5mm · 소켓은 좌우 분할 후 접착 · 기어 치형 없는 배치 시제품</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav>'+''.join('<a href="'+n+'.stl" download>'+n+'</a>' for n in names)+'</nav>',s,flags=re.S)
(out/'preview.html').write_text(s);print('Validated crown, caps, split socket, ball/stem and neutral pose clearances.')
