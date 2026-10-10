from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-top-ball-joint'
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
def cylinder(r,h,p):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=64);m.apply_translation(p);return m
def rod(a,b,r):
 a=np.array(a);b=np.array(b);m=trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=48);m.apply_transform(trimesh.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);return m
def ring(ri,ro,h,z):
 m=trimesh.creation.annulus(r_min=ri,r_max=ro,height=h,sections=128);m.apply_translation([0,0,z]);return m
def union(ms):return trimesh.boolean.union(ms,engine='manifold')
frame=trimesh.load(src/'frame-annular-crown.stl',force='mesh');cap=trimesh.load(src/'upper-cap.stl',force='mesh');top=frame.bounds[1,2];floor=top-2;gz=floor-9
# Fixed cap and fork support outer gimbal's X trunnions.
fixed=union([cylinder(7,1.2,[0,0,floor-.7]),cylinder(2.3,4,[0,0,floor+.7]),box([22,3,1.2],[0,0,floor-1.1]),box([2,3,8.5],[10,0,floor-5]),box([2,3,8.5],[-10,0,floor-5])])
fixed=trimesh.boolean.difference([fixed,rod([-12,0,gz],[12,0,gz],.95)],engine='manifold')
outer=union([ring(7,9,2,gz),rod([-10.8,0,gz],[10.8,0,gz],.75)])
# Clear axle across the center, preserving only external trunnions.
outer=trimesh.boolean.difference([outer,cylinder(7,4,[0,0,gz]),rod([0,-11,gz],[0,11,gz],.95)],engine='manifold')
inner=union([cylinder(5.5,2,[0,0,gz]),rod([0,-8.5,gz],[0,8.5,gz],.75),rod([0,0,gz],[0,0,gz-24],1.5),box([16,3,1.2],[3,0,gz-3]),box([3,16,1.2],[0,3,gz-3]),rod([0,0,gz],[0,0,gz-3],2)])
# Two pushrods with joint markers, motor cranks and fixed motor cradle placeholders.
links=[];motors=[];cranks=[]
for axis in [0,1]:
 p=np.array([0.,0.,gz-3]);p[axis]=9
 q=np.array([0.,0.,10.]);q[axis]=9
 links.append(rod(q,p,.65))
 for pos in [p,q]:
  joint=trimesh.creation.icosphere(subdivisions=2,radius=1.3);joint.apply_translation(pos);links.append(joint)
 center=q.copy();center[axis]-=2
 a=center.copy();b=center.copy();a[1-axis]-=8;b[1-axis]-=1
 motors.append(rod(a,b,3))
 cranks.append(rod(center,q,.8));cranks.append(rod(a,center,.6))
 cradle=box([8,4,2] if axis==0 else [4,8,2], [7,-4,5] if axis==0 else [-4,7,5]);cranks.append(cradle)
# Proposed moving payload plate, mounted on central stem.
payload=box([36,20,1],[0,0,gz-24])
meshes=[frame,cap,fixed,outer,inner,trimesh.util.concatenate(links),trimesh.util.concatenate(motors),trimesh.util.concatenate(cranks),payload]
names=['frame','top-cap','fixed-fork','outer-gimbal','inner-gimbal-stem','pushrods-joint-markers','motor-placeholders','cranks-mount-placeholders','payload-plate']
for n,m in zip(names,meshes):
 assert m.is_watertight,n
 m.export(out/(n+'.stl'))
assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for m in meshes])+';counts',s)
s=s.replace('[0x85c9de,0xf0b66b,0xc7a1dd,0xc7a1dd,0x9fd8b0][i]','[0x85c9de,0xf0b66b,0xc7a1dd,0xff9f80,0x9fd8b0,0xffd166,0x66768b,0xb3c6dd,0x9fd8b0][i]')
s=re.sub(r'<h1>.*?</h1>','<h1>꼭대기 2축 관절 + 직각 연결봉 2개</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>배치 검토용 · 주황/초록: 직교 회전축 · 노랑: 연결봉 · 아래 모터2개 + 크랭크 반경2mm · 아래 하중판36×20mm · 봉 끝 관절/감속기/축 고정 상세 미설계 · 출력용 아님</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav></nav>',s,flags=re.S)
(out/'preview.html').write_text(s)
print('Concept assembly saved; no full-motion or fabrication validation.')
