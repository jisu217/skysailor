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
# Reversed motor alongside screw; asymmetric rear bay.
screw=U([thread(8,54),cyl(2,65,[28.5,0,10]),cyl(3.5,1,[3,0,10]),cyl(3.5,1,[7,0,10]),cyl(3.5,1,[56,0,10])])
nutcore=D(box([10,12,12],[30,0,10]),thread(23,37,.25))
# Two semicylindrical output shells; longitudinal side gaps clear the -O- arms.
tube=D(cyl(5.7,52,[60,0,10]),cyl(4.3,54,[60,0,10]),box([54,16,3],[60,0,10]))
nut=U([nutcore,tube])
big=t.load(out/'large-gear-assembled.stl');small=t.load(out/'motor-gear-assembled.stl')
motor=cyl(3,15,[7.5,-12,10]);shaft=cyl(.6,3.5,[-1.75,-12,10])
outer=U([box([24,28.8,24],[6,-2.6,10]),box([58,16.6,16.6],[33,0,10])])
shell=D(outer,box([8,24.8,20],[0,-2.6,10]),box([21,7,20],[6.5,-11.5,10]),box([60,12.6,12.6],[33,0,10]))
shoulder=D(box([2,16.6,16.6],[5,0,10]),cyl(2.25,4,[5,0,10]))
# Front bearing: horizontal arms and an annular bearing, open above and below.
front=D(U([cyl(3.1,3,[58.5,0,10]),box([3,16.6,2],[58.5,0,10])]),cyl(2.25,5,[58.5,0,10]))
cradle=D(box([10,9,20],[7.5,-12,10]),cyl(3.2,12,[7.5,-12,10]))
whole=U([shell,shoulder,front,cradle])
whole=D(whole,cyl(2.25,12,[2,0,10]),cyl(9.8,2.6,[-2.5,0,10]),cyl(3.8,2.6,[-2.5,-12,10]),cyl(1.5,5,[17,-12,10]))
frame=t.boolean.intersection([whole,box([150,80,40],[30,0,-10])],engine='manifold')
cap=t.boolean.intersection([whole,box([150,80,40],[30,0,30])],engine='manifold')
assert len(frame.split())==1 and len(cap.split())==1
for part in [frame,cap]:
 for obj in [motor,shaft,screw]:
  hit=t.boolean.intersection([part,obj],engine='manifold');assert hit.is_empty or abs(hit.volume)<.001,('fixed collision',abs(hit.volume))
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
(out/'inspection.json').write_text(json.dumps({'checks':checks,'lead_mm':2,'gear_ratio':3,'travel_mm':[-10,10],'guide':'square casing inner 12.6x12.6mm; 0.3mm clearance each side','front_outer_mm':[16.6,16.6],'rear_outer_mm':[28.8,24], 'output_tube_od_id_mm':[11.4,8.6], 'output_side_slot_mm':3, 'motor_reversed':True,'nut_outer_mm':[10,12,12],'nut_center':[30,0,10],'screw_axis_yz':[0,10],'eyes':None,'rear_bearing':{'wall_x_mm':[4,6],'shaft_diameter_mm':4,'bore_diameter_mm':4.5,'radial_gap_mm':.25,'collar_gap_each_mm':.5},'thread_start_x_mm':8,'status':'cq_gears involute gears; attachment and print fit still require validation'},indent=2))
# Reuse camera controls, with new part-based model.
s=(out.parent/'615-motor-worm-study/preview.html').read_text()
s=s.replace('615 모터 · 웜기어 개선','615 · 신축형 리드스크루 액추에이터').replace('615 모터 + 웜기어','반전 모터 · 반원통 출력봉').replace('회색: 모터·축 · 보라: 웜기어','주황: 사각 너트와 위·아래 반원통 출력봉')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+'''<aside><b>반원통 출력봉 + -O- 나사축 받침</b><label>너트 위치 확인 <output id="sv">0</output> mm<input id="slide" type="range" min="-10" max="10" value="0" step="0.1"></label><button id="zero">중앙</button><label><input type="checkbox" id="ghost"> 너트 반투명</label><label><input type="checkbox" id="caseghost" checked> 케이스 반투명</label><label><input type="checkbox" id="open"> 위 덮개 열기</label><p>모터 몸통을 앞쪽으로 반전<br>기어는 뒤쪽 / 모터와 나사축 병렬<br>비대칭 뒤 케이스 폭 28.8mm<br>기존 폭 38mm에서 축소</p><p>사각 너트 12 × 12mm<br>출력봉 외경 11.4 / 내경 8.6mm<br>반원통 사이 틈 3mm<br>이동 범위 ±10mm</p><p>앞쪽 나사축 받침: -O- 형태<br>받침 구멍 Ø4.5 / 축 Ø4mm<br>양옆 연결 팔 두께 2mm<br>출력봉 틈이 연결 팔을 통과</p><small>동작 형상 검토용입니다. 덮개 체결과 출력봉 끝 연결부는 아직 미설계입니다.</small></aside>'''+s[b:]
s=s.replace('d=120,target=new T.Vector3(-8,0,6)','d=310,target=new T.Vector3(33,-2,7)')
a=s.index('function cylinder(');b=s.index("$('angle').onclick",a)
s=s[:a]+'''function move(){for(let name of ['frame','bearing-caps'])if(meshes[name]){meshes[name].material.transparent=true;meshes[name].material.opacity=$('caseghost').checked?.32:1;}if(meshes['bearing-caps'])meshes['bearing-caps'].position.z=$('open').checked?27:0;let v=+$('slide').value;$('sv').textContent=v.toFixed(1);if(meshes.nut){meshes.nut.position.x=v;meshes.nut.material.opacity=$('ghost').checked?.5:1;}for(let name of ['screw','large-gear'])if(meshes[name])meshes[name].rotation.x=-v*Math.PI;for(let name of ['motor-gear','motor-shaft'])if(meshes[name])meshes[name].rotation.x=v*Math.PI*3;render();}
Promise.all(['frame','bearing-caps','screw','nut','large-gear','motor-gear','motor','motor-shaft'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let rotate=['screw','large-gear','motor-gear','motor-shaft'].includes(name),y=name.startsWith('motor-')?-12:0;if(rotate)g.translate(0,-y,-10);let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef,0xf3ad60,0xc19aef,0xefa184,0xb7c3ce,0xb7c3ce][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:name==='nut',opacity:name==='nut'?.5:1}));if(rotate)m.position.set(0,y,10);meshes[name]=m;scene.add(m)})).then(()=>{move();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('slide').oninput=move;$('zero').onclick=()=>{$('slide').value=0;move()};$('ghost').onchange=move;$('caseghost').onchange=$('open').onchange=move;
'''+s[b:]
s=s.replace('<button id="side">옆에서</button>','<button id="side">옆에서</button><button id="gears">기어 확대</button>')
s=s.replace("$('angle').onclick=()=>{az=-1.2;el=.7;render()}","$('gears').onclick=()=>{target.set(-2.5,-5,10);d=85;az=-2.2;el=.85;$('open').checked=true;move()};$('angle').onclick=()=>{target.set(33,-2,7);d=310;az=-1.2;el=.7;render()}")
(out/'preview.html').write_text(s)
(out.parent/'model-viewer/current.json').write_text(json.dumps({'model':out.name,'note':'반전 모터 / 비대칭 케이스 / 반원통 출력봉'},ensure_ascii=False))
print('Built extending output; 9 travel positions clear',flush=True)
