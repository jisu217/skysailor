from pathlib import Path
import json, math, shutil
import numpy as np
import trimesh as t
out=Path(__file__).resolve().parent
src=out.parent/'615-worm-clearance-v2'
def box(size,at):
 m=t.creation.box(size);m.apply_translation(at);return m
def cyl(r,h,at):
 m=t.creation.cylinder(r,h,sections=64);m.apply_translation(at);return m
body=t.load(src/'body.stl')
ear=t.boolean.union([box([5,7,1.7],[-34.5,0,-1.15]),cyl(3.5,1.7,[-36,0,-1.15])],engine='manifold')
body=t.boolean.union([body,ear],engine='manifold')
body=t.boolean.difference([body,cyl(1.1,5,[-36,0,-1.15])],engine='manifold')
for name in ['body','cap','rack','worm']:
 m=body if name=='body' else t.load((out.parent/'615-worm-bore11' if name=='worm' else src)/f'{name}.stl')
 assert m.is_volume and len(m.split())==1
 m.export(out/f'{name}.stl')
 (out/f'{name}.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
R=14.5*math.cos(math.pi/6)+math.sqrt(61**2-(14.5*.5)**2)
h=(out.parent/'central-xy-three-actuators'/'preview.html').read_text()
h=h.replace('원판 XY · 3 액추에이터','원판 XY · 시험 완료 웜 액추에이터').replace('고정판·이동판 + 120° 액추에이터 3개','시험한 615 웜 액추에이터 × 3')
h=h.replace('끝단은 수직 핀 회전 관절','실제 시험 치형·스냅 몸통 / 양 끝 수직 핀 회전 관절')
h=h.replace('외부 고정점 반경 48mm',f'외부 고정점 반경 {R:.2f}mm<br>웜 지지축 Ø2.8 × 15mm<br>랙 스트로크 ±6mm / 뒤 연결 구멍 Ø2.2')
h=h.replace('배치·기구학 시각화입니다. 액추에이터는 가상 외형이며 실제 제품 규격, 하중, 마찰, 공차 검증은 아직 하지 않았습니다. 표는 모터 위치 명령이 아닌 양 끝 핀 사이 거리입니다.','시험한 액추에이터 형상을 사용합니다. 추가한 뒤쪽 연결 귀와 고정 받침은 조립 시험이 필요합니다. 표의 변화량은 랙 이동량이며, 위치 피드백은 별도입니다.')
h=h.replace('<th>변화</th>','<th>랙 이동</th>')
a=h.index('let anchors=[]');b=h.index('let az=',a)
h=h[:a]+f'''const anchorRadius={R}, pivotX=-36, actuatorZ=10;
let anchors=[],ends=[],units=[],colors=[0x90d5a5,0xf49b8f,0xa9b8ff];
for(let i=0;i<3;i++){{let a=i*2*Math.PI/3,fa=a+Math.PI/6,A=new T.Vector3(anchorRadius*Math.cos(fa),anchorRadius*Math.sin(fa),0);anchors.push(A);ends.push(new T.Vector3(14.5*Math.cos(a),14.5*Math.sin(a),0));
let p=new T.Mesh(new T.BoxGeometry(11,9,2),fixedMat);p.position.set(A.x,A.y,0);p.rotation.z=fa;scene.add(p);
bar(new T.Vector3(22.8*Math.cos(fa),22.8*Math.sin(fa),0),new T.Vector3(A.x,A.y,0),1.5,fixedMat);
cylinder(2.5,6.8,4.4,fixedMat,scene,A.x,A.y);cylinder(1,5,9,steel,scene,A.x,A.y);
let [hx,hy]=holes[i];disc(2.5,1.1,4.2,5.6,purple,moving).position.set(hx,hy,4.2);cylinder(1,10,9,steel,moving,hx,hy);
}}
async function loadUnits(){{let geometry={{}};for(let name of ['body','cap','rack','worm']){{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();if(name==='worm')g.translate(0,0,-6);geometry[name]=g;}}
for(let i=0;i<3;i++){{let group=new T.Group(),parts={{}};scene.add(group);for(let name of ['body','cap','rack','worm']){{let mat=new T.MeshStandardMaterial({{color:name==='worm'?0xb58ae4:name==='rack'?0xefb265:colors[i],roughness:.5,flatShading:true,transparent:name==='cap',opacity:name==='cap'?.48:1}}),m=new T.Mesh(geometry[name],mat);if(name==='worm')m.position.z=6;group.add(m);parts[name]=m;}}
let motor=new T.Mesh(new T.CylinderGeometry(3,3,15,48),steel);motor.rotation.z=Math.PI/2;motor.position.set(-16.5,0,6);group.add(motor);let shaft=new T.Mesh(new T.CylinderGeometry(.6,.6,3.5,32),steel);shaft.rotation.z=Math.PI/2;shaft.position.set(-7.25,0,6);group.add(shaft);units.push({{group,parts}});}}update(0,0);}}
''' +h[b:]
h=h.replace('d=215','d=360')
a=h.index('function update(');b=h.index('function stop()',a)
h=h[:a]+'''function update(x,y){let radius=Math.hypot(x,y);if(radius>5){x*=5/radius;y*=5/radius}$('x').value=x;$('y').value=y;$('xv').textContent=x.toFixed(1);$('yv').textContent=y.toFixed(1);moving.position.set(x,y,0);let rows=[];for(let i=0;i<3;i++){let A=anchors[i],B=ends[i].clone().add(new T.Vector3(x,y,0)),u=B.clone().sub(A).normalize(),L=A.distanceTo(B),s=L-61;if(units[i]){let {group,parts}=units[i];group.rotation.z=Math.atan2(u.y,u.x);group.position.set(A.x-pivotX*u.x,A.y-pivotX*u.y,actuatorZ);parts.rack.position.x=s;parts.worm.rotation.x=-s/2.5*2*Math.PI;}rows.push('<tr><td style="color:#'+colors[i].toString(16)+'">'+(i+1)+'</td><td>'+L.toFixed(2)+' mm</td><td>'+(s>=0?'+':'')+s.toFixed(2)+' mm</td></tr>')}$('lengths').innerHTML=rows.join('');render()}
''' + h[b:]
h=h.replace('update(0,0);\n</script>','loadUnits().catch(e=>{$("status").textContent="모델 로딩 실패: "+e.message});\n</script>')
(out/'preview.html').write_text(h)
report={'anchor_radius_mm':R,'neutral_pin_length_mm':61,'stroke_mm':[-6,6],'xy_radius_mm':5,'geometry_source':src.name,'samples':[]}
# Check full actual actuator meshes pairwise at center and eight workspace boundary points.
meshes={n:t.load(out/f'{n}.stl') for n in ['body','cap','rack','worm']}
for x,y in [(0,0)]+[(5*math.cos(a),5*math.sin(a)) for a in np.arange(8)*math.pi/4]:
 assemblies=[]; travels=[]
 for i in range(3):
  a=i*2*math.pi/3;A=np.array([R*math.cos(a+math.pi/6),R*math.sin(a+math.pi/6),0]);B=np.array([14.5*math.cos(a)+x,14.5*math.sin(a)+y,0]);u=(B-A)/np.linalg.norm(B-A);s=np.linalg.norm(B-A)-61;travels.append(s);assert abs(s)<=6
  mat=t.transformations.rotation_matrix(math.atan2(u[1],u[0]),[0,0,1]);mat[:3,3]=A+36*u+[0,0,10]
  parts=[]
  for n,m in meshes.items():
   m=m.copy()
   if n=='rack':m.apply_translation([s,0,0])
   if n=='worm':m.apply_transform(t.transformations.rotation_matrix(-s/2.5*2*math.pi,[1,0,0],point=[0,0,6]))
   m.apply_transform(mat);parts.append(m)
  assemblies.append(t.util.concatenate(parts))
 # Concatenated touching solids: test individual pairs only where bounding boxes overlap.
 for i in range(3):
  for j in range(i):
   for p in assemblies[i].split():
    for q in assemblies[j].split():
     if np.all(np.minimum(p.bounds[1],q.bounds[1])-np.maximum(p.bounds[0],q.bounds[0])>0):
      v=t.boolean.intersection([p,q],engine='manifold').volume
      assert abs(v)<1e-4,(x,y,i,j,v)
 report['samples'].append({'xy':[x,y],'rack_travel':travels})
report['validation']='Nine poses: separate actuators have no solid intersection; full stroke is within ±6. Support joints and load behavior require physical assembly testing.'
(out/'inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
