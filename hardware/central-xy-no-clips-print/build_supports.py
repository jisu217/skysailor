from pathlib import Path
import numpy as np, trimesh as t,json,math
out=Path(__file__).resolve().parent
R=73.12499584679449
def box(d,p):
 m=t.creation.box(d);m.apply_translation(p);return m
def cyl(r,h,p):
 m=t.creation.cylinder(r,h,sections=96);m.apply_translation(p);return m
def U(ms):return t.boolean.union(ms,engine='manifold')
def D(a,*bs):return t.boolean.difference([a,*bs],engine='manifold')
def ring(ro,ri,z,h):return D(cyl(ro,h,[0,0,z+h/2]),cyl(ri,h+2,[0,0,z+h/2]))
fixed=[ring(23.7,7.7,-1,3),ring(23.7,22.7,2,3)]
upper=[cyl(17.5,2,[0,0,3.2])];holes=[];anchors=[];ends=[]
for i in range(3):
 a=i*2*np.pi/3;fa=a+np.pi/6
 A=np.array([R*np.cos(fa),R*np.sin(fa),0]);B=np.array([14.5*np.cos(a),14.5*np.sin(a),0]);anchors.append(A);ends.append(B)
 arm=box([R-22+1,3,2],[(R+22)/2,0,0]);arm.apply_transform(t.transformations.rotation_matrix(fa,[0,0,1]));fixed.append(arm)
 pad=box([11,9,2],[0,0,0]);pad.apply_transform(t.transformations.rotation_matrix(fa,[0,0,1]));pad.apply_translation(A);fixed.append(pad)
 fixed.append(cyl(2.5,6.8,A+[0,0,4.4]));holes.append(cyl(1.1,10,A+[0,0,4]))
 upper.append(cyl(2.5,5.6,B+[0,0,7]));
base=D(U(fixed),*holes)
top=U(upper)
for B in ends:top=D(top,cyl(1.1,12,B+[0,0,6]))
# Blind center socket for one-piece lower disc / connecting shaft.
top=D(top,cyl(2.6,1.4,[0,0,2.7]))
bottom=U([cyl(17.5,2,[0,0,-2.2]),cyl(2.5,4.4,[0,0,1])])
# Heads prevent dropping through. Glue distal tip only in stationary support, keeping rotating eye free.
frontpin=U([cyl(1,9.3,[0,0,9.05]),cyl(2,.8,[0,0,14.1])])
rearpin=U([cyl(1,8.7,[0,0,5.55]),cyl(2,.8,[0,0,10.3])])
parts={'fixed-base':base,'moving-top':top,'moving-bottom':bottom,'front-pivot-pin':frontpin,'rear-pivot-pin':rearpin}
for name,m in parts.items():
 assert m.is_volume and len(m.split())==1,name
 m.export(out/f'{name}.stl');q=t.load(out/f'{name}.stl');assert q.is_volume and q.is_watertight,name
 (out/f'{name}.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
# Collision inspection at center and 12 boundary poses (sampled, not proof of continuous motion).
units={n:t.load(out/f'{n}.stl') for n in ['body','cap','rack','worm']}
report=[]
def clear(a,b,label):
 if np.any(np.minimum(a.bounds[1],b.bounds[1])-np.maximum(a.bounds[0],b.bounds[0])<=0):return
 h=t.boolean.intersection([a,b],engine='manifold');v=0 if h.is_empty else abs(h.volume)
 assert v<.001,(label,v)
for x,y in [(0,0)]+[(5*np.cos(a),5*np.sin(a)) for a in np.arange(12)*np.pi/6]:
 moving=[]
 for m in [top,bottom]:
  m=m.copy();m.apply_translation([x,y,0]);moving.append(m);clear(m,base,'moving plate / base')
 assemblies=[]
 for i,(A,B) in enumerate(zip(anchors,ends)):
  target=B+[x,y,0];u=(target-A)/np.linalg.norm(target-A);s=np.linalg.norm(target-A)-61
  mat=t.transformations.rotation_matrix(math.atan2(u[1],u[0]),[0,0,1]);mat[:3,3]=A+36*u+[0,0,10]
  meshes=[]
  for name,source in units.items():
   m=source.copy()
   if name=='rack':m.apply_translation([s,0,0])
   if name=='worm':m.apply_transform(t.transformations.rotation_matrix(-s*2*np.pi/2.5,[1,0,0],point=[0,0,6]))
   m.apply_transform(mat);meshes.append(m);clear(m,base,name+'/fixed base')
   for p in moving:clear(m,p,name+'/moving plate')
  for prior in assemblies:
   for p in prior:
    for q in meshes:clear(p,q,'between actuators')
  assemblies.append(meshes)
 report.append({'xy':[x,y],'clear':True})
(out/'support-inspection.json').write_text(json.dumps(report,indent=2));print('13 sampled assembly poses: no collisions')
# Render the actual printable supports, not the old idealized procedural mock-ups.
s=(out.parent/'central-xy-tested-actuators/preview.html').read_text()
s=s.replace('시험한 615 웜 액추에이터 × 3','615 액추에이터 × 3 · 걸쇠 제거 · 출력 키트').replace('실제 시험 치형·스냅 몸통','기존 시험 치형·접착 몸통')
a=s.index('disc(23.7');b=s.index('async function loadUnits()',a)
s=s[:a]+'''let moving=new T.Group();scene.add(moving);
const anchorRadius=73.12499584679449,pivotX=-36,actuatorZ=10;
let anchors=[],ends=[],units=[],colors=[0x90d5a5,0xf49b8f,0xa9b8ff];
for(let i=0;i<3;i++){let a=i*2*Math.PI/3,fa=a+Math.PI/6;anchors.push(new T.Vector3(anchorRadius*Math.cos(fa),anchorRadius*Math.sin(fa),0));ends.push(new T.Vector3(14.5*Math.cos(a),14.5*Math.sin(a),0));}
async function loadSupports(){for(let name of ['fixed-base','moving-top','moving-bottom','front-pivot-pin','rear-pivot-pin']){let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let mat=name==='fixed-base'?fixedMat:name.includes('pin')?purple:orange;
if(name.includes('pivot-pin')){for(let p of name.startsWith('front')?ends:anchors){let m=new T.Mesh(g,mat);m.position.set(p.x,p.y,0);(name.startsWith('front')?moving:scene).add(m);}}else (name==='fixed-base'?scene:moving).add(new T.Mesh(g,mat));}render();}
''' + s[b:]
s=s.replace('loadUnits().catch','Promise.all([loadUnits(),loadSupports()]).catch')
s=s.replace('</aside>','<p><a style="color:#9ed9ff" href="print-kit/actuators-3x.3mf" download>액추에이터 3세트 3MF</a><br><a style="color:#9ed9ff" href="print-kit/supports.3mf" download>중앙 원판·받침 3MF</a><br><a style="color:#9ed9ff" href="central-xy-no-clips-kit.zip" download>전체 출력 ZIP</a></p></aside>')
s=s.replace('시험한 액추에이터 형상을 사용합니다.','걸쇠 4곳과 걸림턱 제거, 작은 정렬핀 유지. 몸통 상하부는 접착 고정합니다. 회전핀 끝만 받침에 접착하고 회전 구멍에는 접착하지 마세요.')
(out/'preview.html').write_text(s)
