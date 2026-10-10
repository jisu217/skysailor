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
bz=floor-8
# Four open fingers: spherical inner contact, open diagonal quadrants.
# Bottom ends below equator capture the ball; insertion from below.
outer=sphere(6.3,bz)
outer=trimesh.boolean.difference([outer,sphere(5.2,bz)],engine='manifold')
claws=[]
for i in range(4):
 # Contact shoe trimmed at z=bz-2.3; mouth is smaller than ball diameter.
 shoe=trimesh.boolean.intersection([outer,box([7,2.2,5.6],[3.5,0,bz+.5])],engine='manifold')
 arm=box([1.1,2.2,6.4],[5.7,0,bz+3.65])
 # Rounded shoulder strengthens the attachment to the cap.
 shoulder=cyl(1.6,1.3,floor-1.1);shoulder.apply_translation([5.7,0,0])
 finger=trimesh.boolean.union([shoe,arm,shoulder],engine='manifold')
 finger.apply_transform(trimesh.transformations.rotation_matrix(i*np.pi/2,[0,0,1]));claws.append(finger)
lower=trimesh.boolean.union([lower]+claws,engine='manifold')
# Four square posts beneath cap at diagonal corners; bottom z=5.
posts=[]
for i in range(4):
 a=np.pi/4+i*np.pi/2
 x=8*np.cos(a);y=8*np.sin(a)
 post=box([2,2,floor-5],[x,y,(floor+5)/2])
 posts.append(post)
lower=trimesh.boolean.union([lower]+posts,engine='manifold')
ball=trimesh.boolean.union([sphere(5,bz),cyl(1.5,bz-8,(bz+2)/2)],engine='manifold')
meshes=[frame,upper,lower,ball];names=['frame-annular-crown','upper-cap','lower-cap-four-claws-posts','ball-and-stem']
for name,m in zip(names,meshes):
 assert m.is_volume and m.is_watertight and len(m.split())==1,name
 m.export(out/(name+'.stl'))
for a,b in [(frame,upper),(frame,lower),(ball,lower),(upper,lower)]:
 h=trimesh.boolean.intersection([a,b],engine='manifold');assert h.is_empty or abs(h.volume)<.001
assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0xc7a1dd,0x9fd8b0][i],roughness:.45,flatShading:true}))) });'''
assert old in s;s=s.replace(old,new)
s=re.sub(r'<h1>.*?</h1>','<h1>네 발톱 구관절 + X방향 사각기둥 4개</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>아래 캡 Ø20 / 두께1.2 · 위 캡 Ø14 유지 · 구 Ø10 / 접촉면 여유0.2 · 발톱4개 / 팔 두께1.1 / 폭2.2 · 긴 막대 Ø3 / 대각선 사각기둥 2×2mm 4개 / 아래 끝 z=5 · 끼움 탄성 및 작동각은 출력 검증 필요</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav>'+''.join('<a href="'+n+'.stl" download>'+n+'</a>' for n in names)+'</nav>',s,flags=re.S)
(out/'preview.html').write_text(s);print('Validated crown, enlarged lower cap, four claws and neutral pose clearances.')
