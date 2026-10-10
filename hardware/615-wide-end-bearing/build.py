from pathlib import Path
import trimesh as t, numpy as np,json,shutil
out=Path(__file__).resolve().parent;src=out.parent/'615-motor-worm-close'
def box(d,p):
 m=t.creation.box(d);m.apply_translation(p);return m
def cyl(r,h,p,axis='x'):
 m=t.creation.cylinder(r,h,sections=96)
 if axis=='x':m.apply_transform(t.geometry.align_vectors([0,0,1],[1,0,0]))
 m.apply_translation(p);return m
def U(ms):return t.boolean.union(ms,engine='manifold')
def D(a,*b):return t.boolean.difference([a,*b],engine='manifold')
# One-sided broad connecting plate. Upper and lower shells share the same side.
parts=[cyl(3.95,14,(-17,0,6)),cyl(2.5,4,(2.45,0,6)),
 box([28.95,4,3],[-9.525,-6.9,6]),box([14,3.7,3],[-17,-4.75,6]),
 box([2,6.5,3],[-11.5,-5.65,6]),
 box([4,6.9,3],[2.45,-5.45,6])]
whole=D(U(parts),cyl(3.15,17,(-17,0,6)),cyl(1.5,6,(2.45,0,6)))
body=t.boolean.intersection([whole,box([100,100,30],[0,0,-9])],engine='manifold')
cap=t.boolean.intersection([whole,box([100,100,30],[0,0,21])],engine='manifold')
for x in [-11.5,3.45]:
 body=U([body,cyl(.8,1.15,(x,-6.9,6.375),'z')])
 cap=D(cap,cyl(.85,1.3,(x,-6.9,6.45),'z'))
old=t.load(src/'worm.stl')
# Keep the thread unchanged; rebuild the thinner, longer journal and move its collar.
tooth=t.boolean.intersection([old,box([20,30,30],[-10.8,0,6])],engine='manifold')
worm=D(U([tooth,cyl(1.2,5.6,(1.9,0,6)),cyl(2.1,.4,(-.05,0,6))]),cyl(.5,20,(-2,0,6)))
assert abs(worm.bounds[1,0]-4.7)<1e-5
motor=cyl(3,15,(-16.5,0,6))
report={}
for name,m in {'body':body,'cap':cap,'worm':worm}.items():
 assert m.is_volume and len(m.split())==1,name
 m.export(out/f'{name}.stl');(out/f'{name}.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
 report[name]={'size_mm':m.extents.tolist(),'volume_mm3':m.volume}
for a,b,n in [(body,worm,'body_worm'),(cap,worm,'cap_worm'),(body,motor,'body_motor'),(cap,motor,'cap_motor'),(body,cap,'cap_body')]:
 hit=t.boolean.intersection([a,b],engine='manifold');v=0 if hit.is_empty else abs(hit.volume);assert v<1e-5,(n,v);report[n]=v
report['dimensions']={'sleeve_ID':6.3,'sleeve_wall':.8,'bearing_ID':3.0,'bearing_OD':5.0,'bearing_width_mm':4,'journal_OD':2.4,'radial_clearance':.3,'extension_mm':2,'collar_to_bearing_gap':.3,'pin_diameter':1.6,'socket_diameter':1.7,'identical_halves':False,'plate_length_mm':28.95,'plate_width_mm':4,'assembled_plate_thickness_mm':3,'connections':1}
(out/'inspection.json').write_text(json.dumps(report,indent=2))
p=worm.copy();p.apply_transform(t.geometry.align_vectors([1,0,0],[0,0,1]));p.apply_translation([-p.centroid[0],-p.centroid[1],-p.bounds[0,2]]);p.export(out/'worm-print.stl')
s=(src/'preview.html').read_text().replace('615 모터 + 웜기어','615 · 폭 4mm 끝단 받침')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+'''<aside><b>한쪽 연결판 · 위아래 조립</b><p>모터 홀더 내경 Ø6.3 / 벽 0.8mm<br>한쪽 연결판 폭 4mm / 길이 28.95mm<br>조립 두께 3mm (반쪽당 1.5mm)<br>끝단 원통 내경 Ø3.0 / 외경 Ø5.0mm<br>받침 폭 4mm (기존 2mm)<br>웜 지지축 Ø2.4mm / 끝쪽 2mm 연장<br>반경 유격 0.3mm<br>걸림턱–받침 간격 0.3mm</p><label><input id="capopen" type="checkbox"> 윗부분 열기</label><label><input id="transparent" type="checkbox"> 홀더 반투명</label><p>아래 반쪽에 모터와 웜을 놓고<br>위쪽 반쪽을 덮습니다.<br>연결판의 핀·구멍 2곳으로 맞춥니다.</p><small>형상 검토용입니다. 핀의 끼움 유지력과 모터의 축방향 고정은 조립 시험 후 보완합니다. 랙 가이드는 아직 포함하지 않았습니다.</small><p><a href="worm-print.stl" download>수정 웜 STL</a><a href="body.stl" download>아래 반쪽 STL</a><a href="cap.stl" download>위 반쪽 STL</a></p></aside>''' +s[b:]
a=s.index("fetch('worm.json')");b=s.index("$('angle').onclick",a)
s=s[:a]+'''Promise.all(['body','cap','worm'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:name==='body'}));meshes[name]=m;scene.add(m)})).then(()=>{render();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('capopen').onchange=()=>{if(meshes.cap)meshes.cap.position.z=$('capopen').checked?7:0;render()};$('transparent').onchange=()=>{if(meshes.body)meshes.body.material.opacity=$('transparent').checked?.3:1;render()};
''' +s[b:]
(out/'preview.html').write_text(s)
(out.parent/'model-viewer'/'current.json').write_text(json.dumps({'model':out.name,'note':'받침 폭 2→4mm / 축 Ø2.4 / 받침 내경 Ø3.0'},ensure_ascii=False))
print(json.dumps(report,indent=2))
