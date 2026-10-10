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
# Motor sleeve open at both ends. Side rails clear the entire Ø9 tooth envelope.
parts=[cyl(4.15,14,(-17,0,6)),box([2,12.6,2.2],[1.45,0,4.9])]
for side in [-1,1]:
 parts += [box([14.5,1.4,1.6],[-4.8,side*5.6,5.2]),box([2,3.8,1.6],[-11,side*4.4,5.2])]
body=D(U(parts),cyl(3.15,17,(-17,0,6)),cyl(1.7,4,(1.45,0,6)))
# Removable upper saddle with two locating tongues, suitable for a glue/fit trial.
cap=D(box([2,12.6,2.4],[1.45,0,7.2]),cyl(1.7,4,(1.45,0,6)))
for y in [-4.6,4.6]:
 cap=U([cap,box([1.2,1.4,1.5],[1.45,y,5.3])])
 body=D(body,box([1.4,1.6,1.8],[1.45,y,5.2]))
worm=t.load(src/'worm.stl');motor=cyl(3,15,(-16.5,0,6))
report={}
for name,m in {'body':body,'cap':cap,'worm':worm}.items():
 assert m.is_volume and len(m.split())==1,name
 m.export(out/f'{name}.stl');(out/f'{name}.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
 report[name]={'size_mm':m.extents.tolist(),'volume_mm3':m.volume}
for a,b,n in [(body,worm,'body_worm'),(cap,worm,'cap_worm'),(body,motor,'body_motor'),(body,cap,'cap_body')]:
 hit=t.boolean.intersection([a,b],engine='manifold');v=0 if hit.is_empty else abs(hit.volume);assert v<1e-5,(n,v);report[n]=v
report['dimensions']={'sleeve_ID':6.3,'sleeve_wall':1,'bearing_ID':3.4,'journal_OD':2.8,'collar_to_bearing_gap':.3,'cap_tongue_clearance_per_side':.1}
(out/'inspection.json').write_text(json.dumps(report,indent=2))
shutil.copy2(src/'worm-print.stl',out/'worm-print.stl')
s=(src/'preview.html').read_text().replace('615 모터 + 웜기어','615 · 원통 홀더 + 양옆 지지대')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+'''<aside><b>원통 홀더 · 끝단 축 받침</b><p>모터 홀더 내경 Ø6.3 / 벽 1mm<br>양옆 지지대 두께 1.4mm<br>끝단 축 받침 Ø3.4mm<br>웜 지지축 Ø2.8mm<br>걸림턱–받침 간격 0.3mm</p><label><input id="capopen" type="checkbox"> 끝단 캡 열기</label><label><input id="transparent" type="checkbox"> 홀더 반투명</label><p>모터는 뒤에서 삽입합니다.<br>끝단 캡은 맞춤 돌기 2개로 끼웁니다.<br>웜 아래는 랙을 위해 비웠습니다.</p><small>형상 검토용입니다. 캡의 끼움과 모터의 축방향 고정은 조립 시험 후 보완합니다. 랙 가이드는 아직 포함하지 않았습니다.</small><p><a href="body.stl" download>홀더 STL</a><a href="cap.stl" download>캡 STL</a></p></aside>''' +s[b:]
a=s.index("fetch('worm.json')");b=s.index("$('angle').onclick",a)
s=s[:a]+'''Promise.all(['body','cap','worm'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:name==='body'}));meshes[name]=m;scene.add(m)})).then(()=>{render();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('capopen').onchange=()=>{if(meshes.cap)meshes.cap.position.z=$('capopen').checked?7:0;render()};$('transparent').onchange=()=>{if(meshes.body)meshes.body.material.opacity=$('transparent').checked?.3:1;render()};
''' +s[b:]
(out/'preview.html').write_text(s)
(out.parent/'model-viewer'/'current.json').write_text(json.dumps({'model':out.name,'note':'원통 모터 홀더 + 양옆 지지대 + 끝단 분리형 캡'},ensure_ascii=False))
print(json.dumps(report,indent=2))
