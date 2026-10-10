from pathlib import Path
import trimesh as t,numpy as np,json,re
out=Path(__file__).resolve().parent

def box(d,p):
 m=t.creation.box(d);m.apply_translation(p);return m
def cyl(r,h,p,axis='x'):
 m=t.creation.cylinder(r,h,sections=64)
 if axis=='x':m.apply_transform(t.geometry.align_vectors([0,0,1],[1,0,0]))
 m.apply_translation(p);return m
def U(ms):return t.boolean.union(ms,engine='manifold')
def D(a,*bs):return t.boolean.difference([a,*bs],engine='manifold')
def thread(x0,x1,extra=0):
 xs=np.linspace(x0,x1,int((x1-x0)*30)+1);th=np.arange(80)*2*np.pi/80;X,TH=np.meshgrid(xs,th,indexing='ij')
 q=np.abs((TH/(2*np.pi)-X/2+.5)%1-.5);r=2.8+np.clip((.4-q)/.3,0,1)+extra
 v=np.c_[X.ravel(),(r*np.cos(TH)).ravel(),(10+r*np.sin(TH)).ravel()];f=[];nt=len(th);nx=len(xs)
 for i in range(nx-1):
  for j in range(nt):
   a=i*nt+j;b=i*nt+(j+1)%nt;c=(i+1)*nt+j;d=(i+1)*nt+(j+1)%nt;f.extend([[a,b,c],[b,d,c]])
 v=np.vstack([v,[x0,0,10],[x1,0,10]])
 for j in range(nt):f.extend([[nx*nt,(j+1)%nt,j],[nx*nt+1,(nx-1)*nt+j,(nx-1)*nt+(j+1)%nt]])
 m=t.Trimesh(v,f,process=True);m.fix_normals();return m
# U shaped side section: floor, rear and front bearing walls. Split wall caps for assembly.
floor=box([60,24,2],[30,0,1]);supports=[]
supports=[D(box([3,24,18],[1.5,0,7]),cyl(2.25,5,[1.5,0,10])),D(box([3,16.6,16.6],[58.5,0,10]),cyl(2.25,5,[58.5,0,10]))]
rails=[]

# Motor behind the rear wall, offset alongside screw. Base extension and open-top saddle.
motorfoot=box([20,14,2],[-7,-10,1]);saddle=D(box([10,9,10],[-12.5,-12,7]),cyl(3.2,12,[-12.5,-12,10]),box([12,10,8],[-12.5,-12,14]))
frame=U([saddle]+supports)
# Remove upper bearing halves as separate conceptual caps.
capcut=U([box([3.2,24.2,20],[x,0,20]) for x in [1.5,58.5]])
cap=t.boolean.intersection([frame,capcut],engine='manifold');frame=D(frame,capcut)
screw=U([thread(6,54),cyl(2,65,[28.5,0,10]),cyl(3.5,1,[4,0,10]),cyl(3.5,1,[56,0,10])])
# Rectangular threaded nut only, without arms, tabs or eyes.
nut=D(box([10,12,12],[30,0,10]),thread(23,37,.25))
# Involute gears generated without modifying cq_gears; see make_gears.py.
big=t.load(out/'large-gear-assembled.stl');small=t.load(out/'motor-gear-assembled.stl')
motor=cyl(3,15,[-12.5,-12,10]);shaft=cyl(.6,3.5,[-3.25,-12,10])
# Stepped enclosure: short rear motor bay and long square nut guide, concentric to screw.
outer=U([box([31,38,24],[-9.5,0,10]),box([58,16.6,16.6],[33,0,10])])
shell=D(outer,box([27,34,20],[-9.5,0,10]),box([60,12.6,12.6],[33,0,10]))
low=t.boolean.intersection([shell,box([120,70,12],[20,0,4])],engine='manifold')
up=t.boolean.intersection([shell,box([120,70,11.8],[20,0,16.1])],engine='manifold')
low=U([low,box([10,9,2],[-12.5,-12,1])])
up=U([up,cap,box([3,20,4.1],[1.5,0,18])])
# Upper motor cradle clamps by controlled bore, never by squeezing the moving nut.
mc=D(box([10,9,8],[-12.5,-12,16]),cyl(3.2,12,[-12.5,-12,10]))
up=U([up,mc])
# Rear motor axial stop and wire exit.
low=U([low,box([1,7,10],[-21,-12,5])])
low=D(low,cyl(1.5,8,[-23,-12,9]))
frame=U([frame,low]);cap=up
assert len(frame.split())==1 and len(cap.split())==1
# Clearances to fixed motor and screw, including lid closure.
for part in [frame,cap]:
 for obj in [motor,shaft,screw]:
  hit=t.boolean.intersection([part,obj],engine='manifold');assert hit.is_empty or abs(hit.volume)<.001
# Clear full swept gear envelope from motor-foot floor (0.3mm radial clearance).
frame=D(frame,cyl(9.8,2.6,[-2.5,0,10]))
parts={'frame':frame,'bearing-caps':cap,'screw':screw,'nut':nut,'large-gear':big,'motor-gear':small,'motor':motor,'motor-shaft':shaft}
for name,m in parts.items():
 assert m.is_volume,name
 (out/(name+'.json')).write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
for g in [big,small]:
 for fixed in [frame,cap]:
  h=t.boolean.intersection([g,fixed],engine='manifold');assert h.is_empty or abs(h.volume)<.001
# Sample the screw/nut/frame motion; gear mesh is independently checked by make_gears.py.
checks=[]
for s in [-10,-7.5,-5,-2.5,0,2.5,5,7.5,10]:
 n=nut.copy();n.apply_translation([s,0,0]);w=screw.copy();w.apply_transform(t.transformations.rotation_matrix(-s*np.pi,[1,0,0],point=[0,0,10]))
 row={'travel':s}
 for label,m in [('frame',frame),('screw',w),('caps',cap)]:
  hit=t.boolean.intersection([n,m],engine='manifold');vol=0 if hit.is_empty else abs(hit.volume);row[label]=vol;assert vol<.001,row
 checks.append(row)
(out/'inspection.json').write_text(json.dumps({'checks':checks,'lead_mm':2,'gear_ratio':3,'travel_mm':[-10,10],'guide':'square casing inner 12.6x12.6mm; 0.3mm clearance each side','front_outer_mm':[16.6,16.6],'rear_outer_mm':[38,24],'nut_outer_mm':[10,12,12],'nut_center':[30,0,10],'screw_axis_yz':[0,10],'eyes':None,'status':'cq_gears involute gears; attachment and print fit still require validation'},indent=2))
# Reuse camera controls, with new part-based model.
s=(out.parent/'615-motor-worm-study/preview.html').read_text()
s=s.replace('615 모터 · 웜기어 개선','615 · 신축형 리드스크루 액추에이터').replace('615 모터 + 웜기어','가느다란 앞 케이스 · 짧은 모터 케이스').replace('회색: 모터·축 · 보라: 웜기어','주황: 나사산에 맞물리는 사각 너트 · 연결부·고리·가이드 제거')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+'''<aside><b>앞·뒤 케이스 크기 분리</b><label>너트 위치 확인 <output id="sv">0</output> mm<input id="slide" type="range" min="-10" max="10" value="0" step="0.1"></label><button id="zero">중앙</button><label><input type="checkbox" id="ghost"> 너트 반투명</label><label><input type="checkbox" id="caseghost" checked> 케이스 반투명</label><label><input type="checkbox" id="open"> 위 덮개 열기</label><p>앞 단면 12 × 12mm 정사각형<br>축 방향 길이 10mm<br>너트 중심 = 나사축 중심<br>안쪽 나선 홈 유지<br>나사 바깥지름 7.6mm / 리드 2mm<br>615 모터 + 인벌류트 기어 12:36</p><p>너트 연결 팔·날개 제거<br>앞·뒤 고리 제거<br>케이스 옆 체결 귀 4곳 제거<br>케이스 양쪽 가이드 홈·보강 돌출 제거<br>앞 케이스 외부 16.6 × 16.6mm<br>내부 12.6 × 12.6mm<br>너트 둘레 각 0.3mm 여유<br>뒤 케이스 폭 38 × 높이 24mm<br>벽 두께 2mm / 나사축 중심 유지</p><small>앞쪽 사각 통로가 너트 회전을 제한합니다. 출력 공차에 따른 마찰과 끼움은 시험이 필요합니다. 덮개 고정과 너트 연결부는 다음 단계에서 설계합니다.</small></aside>'''+s[b:]
s=s.replace('d=120,target=new T.Vector3(-8,0,6)','d=400,target=new T.Vector3(33,-2,7)')
a=s.index('function cylinder(');b=s.index("$('angle').onclick",a)
s=s[:a]+'''function move(){for(let name of ['frame','bearing-caps'])if(meshes[name]){meshes[name].material.transparent=true;meshes[name].material.opacity=$('caseghost').checked?.32:1;}if(meshes['bearing-caps'])meshes['bearing-caps'].position.z=$('open').checked?27:0;let v=+$('slide').value;$('sv').textContent=v.toFixed(1);if(meshes.nut){meshes.nut.position.x=v;meshes.nut.material.opacity=$('ghost').checked?.5:1;}for(let name of ['screw','large-gear'])if(meshes[name])meshes[name].rotation.x=-v*Math.PI;for(let name of ['motor-gear','motor-shaft'])if(meshes[name])meshes[name].rotation.x=v*Math.PI*3;render();}
Promise.all(['frame','bearing-caps','screw','nut','large-gear','motor-gear','motor','motor-shaft'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let rotate=['screw','large-gear','motor-gear','motor-shaft'].includes(name),y=name.startsWith('motor-')?-12:0;if(rotate)g.translate(0,-y,-10);let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef,0xf3ad60,0xc19aef,0xefa184,0xb7c3ce,0xb7c3ce][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:name==='nut',opacity:name==='nut'?.5:1}));if(rotate)m.position.set(0,y,10);meshes[name]=m;scene.add(m)})).then(()=>{move();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('slide').oninput=move;$('zero').onclick=()=>{$('slide').value=0;move()};$('ghost').onchange=move;$('caseghost').onchange=$('open').onchange=move;
'''+s[b:]
s=s.replace('<button id="side">옆에서</button>','<button id="side">옆에서</button><button id="gears">기어 확대</button>')
s=s.replace("$('angle').onclick=()=>{az=-1.2;el=.7;render()}","$('gears').onclick=()=>{target.set(-2.5,-5,10);d=85;az=-2.2;el=.85;$('open').checked=true;move()};$('angle').onclick=()=>{target.set(33,-2,7);d=400;az=-1.2;el=.7;render()}")
(out/'preview.html').write_text(s)
(out.parent/'model-viewer/current.json').write_text(json.dumps({'model':out.name,'note':'앞쪽 16.6mm 사각 케이스 / 뒤쪽 모터·기어 케이스 / 너트 여유0.3mm'},ensure_ascii=False))
print('Built extending output; 9 travel positions clear',flush=True)
