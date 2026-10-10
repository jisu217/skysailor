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
for x in [1.5,58.5]:supports.append(D(box([3,24,14],[x,0,9]),cyl(2.25,5,[x,0,10])))
rails=[]
for y in [-8,8]:rails += [box([54,2,2.1],[30,y,3]),box([54,3.6,1],[30,y,4.5])]
# Motor behind the rear wall, offset alongside screw. Base extension and open-top saddle.
motorfoot=box([20,14,2],[-7,-10,1]);saddle=D(box([10,9,10],[-12.5,-12,7]),cyl(3.2,12,[-12.5,-12,10]),box([12,10,8],[-12.5,-12,14]))
frame=U([floor,motorfoot,saddle]+rails+supports)
# Remove upper bearing halves as separate conceptual caps.
capcut=U([box([3.2,24.2,7],[x,0,13.5]) for x in [1.5,58.5]])
cap=t.boolean.intersection([frame,capcut],engine='manifold');frame=D(frame,capcut)
screw=U([thread(6,54),cyl(2,65,[28.5,0,10]),cyl(3.5,1,[4,0,10]),cyl(3.5,1,[56,0,10])])
nut=U([box([10,12,10],[30,0,10])]+[box([10,6,4.7],[30,y,4.65]) for y in [-8,8]])
for y in [-8,8]:nut=D(nut,box([12,4,1.5],[30,y,4.5]),box([12,2.4,4],[30,y,1.75]))
nut=D(nut,thread(23,37,.25))
# Moving fork wraps outside the front bearing wall; all three pieces move with nut.
links=[nut]
for side in [-1,1]:
 links.append(box([6,10.5,2.5],[30,side*9.75,13.75]))
 links.append(box([46.5,3,4],[52.25,side*14.5,12.25]))
links.append(box([3,32,4],[75,0,12.25]))
links.append(box([6,6,4],[78,0,12.25]))
links.append(cyl(3,4,[80,0,12.25],'z'))
nut=D(U(links),cyl(1.1,6,[80,0,12.25],'z'))
# Rear stationary attachment eye below the motor, attached to base extension.
rear=U([box([7,7,2],[-19,-10,1]),cyl(3.5,2,[-21,-10,1],'z')])
frame=D(U([frame,rear]),cyl(1.1,4,[-21,-10,1],'z'))
# Involute gears generated without modifying cq_gears; see make_gears.py.
big=t.load(out/'large-gear-assembled.stl');small=t.load(out/'motor-gear-assembled.stl')
motor=cyl(3,15,[-12.5,-12,10]);shaft=cyl(.6,3.5,[-3.25,-12,10])
# Rigid two-piece case around complete stroke. Open front for twin output arms.
# Outer skin 2mm, lid roof z20..22; split at z10 with 0.2mm seam clearance.
shell=D(box([87,38,24],[18.5,0,10]),box([86,34,26],[20,0,13]))
low=t.boolean.intersection([shell,box([120,70,12],[20,0,4])],engine='manifold')
up=t.boolean.intersection([shell,box([120,70,11.8],[20,0,16.1])],engine='manifold')
# Internal top cavity ends at 20; add flat lid explicitly.
up=U([up,box([87,38,2],[18.5,0,21])])
# Join front/rear bearing caps directly to removable lid using short rigid webs.
up=U([up,cap]+[box([3,20,4.1],[x,0,18]) for x in [1.5,58.5]])
# Upper motor cradle clamps by controlled bore, never by squeezing the moving nut.
mc=D(box([10,9,8],[-12.5,-12,16]),cyl(3.2,12,[-12.5,-12,10]))
up=U([up,mc])
# Rear motor axial stop and wire exit.
low=U([low,box([1,7,10],[-21,-12,5])])
low=D(low,cyl(1.5,8,[-23,-12,9]))
# Four external M2 fastening pads, preliminary pilot holes in lower half.
for x in [-18,50]:
 for y in [-20.5,20.5]:
  low=U([low,box([7,7,12],[x,y,4])])
  up=U([up,box([7,7,11.8],[x,y,16.1])])
  low=D(low,cyl(.8,10,[x,y,6],'z'))
  up=D(up,cyl(1.1,14,[x,y,16.5],'z'))
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
(out/'inspection.json').write_text(json.dumps({'checks':checks,'lead_mm':2,'gear_ratio':3,'travel_mm':[-10,10],'status':'cq_gears involute gears; attachment and print fit still require validation'},indent=2))
# Reuse camera controls, with new part-based model.
s=(out.parent/'615-motor-worm-study/preview.html').read_text()
s=s.replace('615 모터 · 웜기어 개선','615 · 신축형 리드스크루 액추에이터').replace('615 모터 + 웜기어','cq_gears 인벌류트 기어 · 케이스 액추에이터').replace('회색: 모터·축 · 보라: 웜기어','고정 프레임 + 주황 출력부 · 너트와 출력 끝이 함께 전진·후진')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+'''<aside><b>공개 기어 모델 적용</b><label>출력부 이동 <output id="sv">0</output> mm<input id="slide" type="range" min="-10" max="10" value="0" step="0.1"></label><button id="zero">중앙</button><label><input type="checkbox" id="ghost" checked> 출력부 반투명</label><label><input type="checkbox" id="caseghost" checked> 케이스 반투명</label><label><input type="checkbox" id="open"> 위 덮개 열기</label><p>615 모터 Ø6 × 15mm<br>기어 12 : 36 · 감속 3:1<br>cq_gears · 인벌류트 치형<br>모듈 0.5 / 압력각 25°<br>치폭 2mm / 축 간격 12mm<br>피치원 기준 치측 여유 합계 0.12mm<br>나사 바깥지름 7.6mm<br>리드 2mm · 나사 길이 48mm<br>이동 범위 ±10mm<br>모터 1회전당 이동 약 0.67mm</p><p>케이스 벽·천장 2mm<br>상하 덮개 + M2 체결부 4곳<br>나사축 받침·모터 누름부를 덮개와 일체화<br>앞쪽 출력 통로 + 뒤쪽 배선 구멍<br>프레임 본체 길이 60mm<br>출력 끝 중심 X=70–90mm<br>최단–최장 길이 차이 20mm<br>앞쪽 출력 연결 구멍 Ø2.2<br>양쪽 T 가이드로 너트 회전·들림 방지<br>앞뒤 받침 + 칼라로 나사축 밀림 제한<br>출력부가 앞 받침 양옆을 지나감 · 틈 1mm</p><small>배치·작동 검토용입니다. 공개 cq_gears 모델로 기어를 생성했습니다. 기어와 축 고정, M2 파일럿 구멍의 체결력은 시험이 필요합니다. 출력용 확정 모델이 아닙니다.</small><p><a href="gear-pair.zip" download>기어 2개 STL·STEP</a><a href="https://github.com/meadiode/cq_gears" target="_blank">원본 cq_gears</a></p></aside>'''+s[b:]
s=s.replace('d=120,target=new T.Vector3(-8,0,6)','d=400,target=new T.Vector3(33,-2,7)')
a=s.index('function cylinder(');b=s.index("$('angle').onclick",a)
s=s[:a]+'''function move(){for(let name of ['frame','bearing-caps'])if(meshes[name]){meshes[name].material.transparent=true;meshes[name].material.opacity=$('caseghost').checked?.32:1;}if(meshes['bearing-caps'])meshes['bearing-caps'].position.z=$('open').checked?27:0;let v=+$('slide').value;$('sv').textContent=v.toFixed(1);if(meshes.nut){meshes.nut.position.x=v;meshes.nut.material.opacity=$('ghost').checked?.5:1;}for(let name of ['screw','large-gear'])if(meshes[name])meshes[name].rotation.x=-v*Math.PI;for(let name of ['motor-gear','motor-shaft'])if(meshes[name])meshes[name].rotation.x=v*Math.PI*3;render();}
Promise.all(['frame','bearing-caps','screw','nut','large-gear','motor-gear','motor','motor-shaft'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let rotate=['screw','large-gear','motor-gear','motor-shaft'].includes(name),y=name.startsWith('motor-')?-12:0;if(rotate)g.translate(0,-y,-10);let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef,0xf3ad60,0xc19aef,0xefa184,0xb7c3ce,0xb7c3ce][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:name==='nut',opacity:name==='nut'?.5:1}));if(rotate)m.position.set(0,y,10);meshes[name]=m;scene.add(m)})).then(()=>{move();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('slide').oninput=move;$('zero').onclick=()=>{$('slide').value=0;move()};$('ghost').onchange=move;$('caseghost').onchange=$('open').onchange=move;
'''+s[b:]
s=s.replace('<button id="side">옆에서</button>','<button id="side">옆에서</button><button id="gears">기어 확대</button>')
s=s.replace("$('angle').onclick=()=>{az=-1.2;el=.7;render()}","$('gears').onclick=()=>{target.set(-2.5,-5,10);d=85;az=-2.2;el=.85;$('open').checked=true;move()};$('angle').onclick=()=>{target.set(33,-2,7);d=400;az=-1.2;el=.7;render()}")
(out/'preview.html').write_text(s)
(out.parent/'model-viewer/current.json').write_text(json.dumps({'model':out.name,'note':'cq_gears 인벌류트 12:36 기어 적용 / 기존 나사축 유지'},ensure_ascii=False))
print('Built extending output; 9 travel positions clear',flush=True)
