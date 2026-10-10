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
for x in [-22,3.45]:
 body=U([body,cyl(.8,1.15,(x,-6.9,6.375),'z')])
 cap=D(cap,cyl(.85,1.3,(x,-6.9,6.45),'z'))
old=t.load(src/'worm.stl')
# Keep the thread unchanged; rebuild the thinner, longer journal and move its collar.
tooth=t.boolean.intersection([old,box([20,30,30],[-10.8,0,6])],engine='manifold')
worm=D(U([tooth,cyl(1.2,5.6,(1.9,0,6)),cyl(2.1,.4,(-.05,0,6))]),cyl(.5,20,(-2,0,6)))
assert abs(worm.bounds[1,0]-4.7)<1e-5
motor=cyl(3,15,(-16.5,0,6))

# Long slot in both plate halves. Two followers remain inside throughout ±5mm travel.
slot=U([box([18,1.8,10],[-10,-6.9,6]),cyl(.9,10,(-19,-6.9,6),'z'),cyl(.9,10,(-1,-6.9,6),'z')])
body=D(body,slot);cap=D(cap,slot)
def mirror_y(m):
 n=m.copy();mat=np.eye(4);mat[1,1]=-1;n.apply_transform(mat);return n
body=U([body,mirror_y(body)]);cap=U([cap,mirror_y(cap)])
# Conjugate helical cavity with 0.18mm radial tooth clearance.
# A minimum radius 4.15 clears the Ø7.9 motor sleeve by 0.2mm per side.
def cavity():
 x=np.linspace(-28,10,913);th=np.arange(96)*2*np.pi/96
 X,TH=np.meshgrid(x,th,indexing='ij');q=np.abs((TH/(2*np.pi)-(X+4.8)/2.5+.5)%1-.5)
 r=np.maximum(4.15,3.4+np.clip((.38-q)/.28,0,1)*1.1+.18)
 v=np.column_stack([X.ravel(),(r*np.cos(TH)).ravel(),(6+r*np.sin(TH)).ravel()]);f=[];nx=len(x);nt=len(th)
 for i in range(nx-1):
  for j in range(nt):
   a=i*nt+j;b=i*nt+(j+1)%nt;c=(i+1)*nt+j;d=(i+1)*nt+(j+1)%nt;f.extend([[a,b,c],[b,d,c]])
 v=np.vstack([v,[x[0],0,6],[x[-1],0,6]])
 for j in range(nt):f.extend([[nx*nt,(j+1)%nt,j],[nx*nt+1,(nx-1)*nt+j,(nx-1)*nt+(j+1)%nt]])
 m=t.Trimesh(v,f,process=True);m.fix_normals();return m
sleeve=D(cyl(5.7,28,(-11,0,6)),box([40,20,3.5],[-11,-10,6]),box([40,20,3.5],[-11,10,6]))
# Full-length guide flanges remove the unsupported mid-length bracket during axial printing.
guide=[sleeve]
for side in [-1,1]:
 guide += [box([28,5.9,1],[-11,side*6.95,8.25]),box([28,5.9,1],[-11,side*6.95,3.75]),box([28,1.4,5.5],[-11,side*9.6,6])]
 for x in [-13,-7]:guide.append(cyl(.7,4.6,(x,side*6.9,6),'z'))
slider=D(U(guide),cavity())
upper=t.boolean.intersection([slider,box([100,100,30],[0,0,21])],engine='manifold')
lower=t.boolean.intersection([slider,box([100,100,30],[0,0,-9])],engine='manifold')
# Four registration pins at the outside guide seam, clear of both sliding plates.
for side in [-1,1]:
 for x in [-22,0]:
  lower=U([lower,cyl(.4,.95,(x,side*9.6,6.275),'z')])
  upper=D(upper,cyl(.5,1.2,(x,side*9.6,6.4),'z'))
slider=t.util.concatenate([lower,upper])
hit=t.boolean.intersection([lower,upper],engine='manifold')
assert hit.is_empty or abs(hit.volume)<.001
# Closing the upper nut vertically is clear at the central phase.
for lift in [.2,1,3,8]:
 u=upper.copy();u.apply_translation([0,0,lift])
 for fixed in [body,cap,worm,motor,lower]:
  hit=t.boolean.intersection([u,fixed],engine='manifold')
  assert hit.is_empty or abs(hit.volume)<.001,('nut insertion',lift)
# Remove sub-micron boolean slivers before float32 STL export, retaining printed geometry.
import manifold3d as md
def clean(m):
 solid=md.Manifold(md.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)))
 mesh=solid.simplify(.00001).to_mesh64()
 return t.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=True)
body,cap,worm,upper,lower=[clean(m) for m in [body,cap,worm,upper,lower]]
parts={'body':body,'cap':cap,'worm':worm,'nut-upper':upper,'nut-lower':lower}
for name,m in parts.items():
 assert m.is_volume and len(m.split())==1,(name,len(m.split()))
 m.export(out/f'{name}.stl');check=t.load(out/f'{name}.stl');assert check.is_watertight and check.is_volume,(name,'STL round trip');(out/f'{name}.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
report={'guide_sides':2,'guide_followers':4,'guide_flange_length_mm':28,'travel_mm':[-5,5],'slot_width_mm':1.8,'follower_diameter_mm':1.4,'plate_face_clearance_mm':.25,'nut_minimum_ID_mm':8.3,'nut_OD_mm':11.4,'nominal_radial_engagement_mm':.35,'nut_length_mm':28,'nut_alignment_pin_mm':.8,'nut_alignment_socket_mm':1.0,'assembly':'split halves, locating pins and adhesive; upper nut closing checked at four heights','checks':[]}
for s in [-5,-3.75,-2.5,0,.7,1.25,2.5,3.75,5]:
 moving=slider.copy();moving.apply_translation([s,0,0]);w=worm.copy();w.apply_transform(t.transformations.rotation_matrix(-s/2.5*2*np.pi,[1,0,0],point=[0,0,6]))
 row={'travel_mm':s}
 for name,m in [('body',body),('cap',cap),('worm',w),('motor',motor)]:
  hit=t.boolean.intersection([moving,m],engine='manifold');v=0 if hit.is_empty else abs(float(hit.volume));row[name]=v;assert v<.001,row
 report['checks'].append(row)
(out/'inspection.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
s=(out.parent/'615-wide-end-bearing'/'preview.html').read_text().replace('615 · 폭 4mm 끝단 받침','615 · 양쪽 연결판·양쪽 가이드')
a=s.index('<aside>');b=s.index('</aside>',a)+len('</aside>')
s=s[:a]+"""<aside><b>양쪽 슬롯 가이드 · 총 이동 10mm</b><label>이동 <output id="sv">0.0</output> mm<input id="slide" type="range" min="-5" max="5" step="0.1" value="0"></label><button id="zero">중앙</button><label><input id="nutopen" type="checkbox"> 너트 윗부분 열기</label><label><input id="nutghost" type="checkbox" checked> 너트 반투명</label><p>주황: 움직이는 긴 너트<br>청록: 고정 홀더·슬롯판<br>보라: 회전 웜</p><p>너트 길이 28mm / 외경 Ø11.4<br>최소 내경 Ø8.3mm<br>모터 홀더 외경 Ø7.9mm<br>웜과 반경 맞물림 약 0.35mm<br>양쪽 슬롯 폭 1.8 / 안내핀 Ø1.4mm × 4<br>가이드 턱 전체 길이 28mm<br>판 위아래 여유 각 0.25mm</p><small>너트 맞춤 핀 4곳: Ø0.8 / 구멍 Ø1.0mm. 상하 너트를 끼운 뒤 접착하는 시험 구조입니다. 접착제는 고정판에 닿지 않게 해야 합니다. 얕은 맞물림의 구동력과 마찰은 실물 시험이 필요합니다.</small><p><a href="print-kit/615-dual-guide-print-layout.3mf" download>출력 배치 3MF</a><a href="615-dual-guide-print-kit.zip" download>전체 ZIP</a></p></aside>"""+s[b:]
a=s.index("Promise.all(['body'");b=s.index("$('angle').onclick",a)
s=s[:a]+"""function move(){let v=+$('slide').value;$('sv').textContent=v.toFixed(1);for(let n of ['nut-upper','nut-lower'])if(meshes[n]){meshes[n].position.x=v;meshes[n].material.opacity=$('nutghost').checked?.5:1;}if(meshes['nut-upper'])meshes['nut-upper'].position.z=$('nutopen').checked?10:0;if(meshes.worm)meshes.worm.rotation.x=-v/2.5*2*Math.PI;render()}
Promise.all(['body','cap','worm','nut-upper','nut-lower'].map(async(name,i)=>{let data=await(await fetch(name+'.json')).json(),g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();if(name==='worm')g.translate(0,0,-6);let m=new T.Mesh(g,new T.MeshStandardMaterial({color:[0x65b7d4,0x86d5d0,0xc19aef,0xf3ad60,0xe5a454][i],roughness:.5,flatShading:true,side:T.DoubleSide,transparent:i>2}));if(name==='worm')m.position.z=6;meshes[name]=m;scene.add(m)})).then(()=>{move();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
$('slide').oninput=move;$('zero').onclick=()=>{$('slide').value=0;move()};$('nutopen').onchange=$('nutghost').onchange=move;
"""+s[b:]
(out/'preview.html').write_text(s)
(out.parent/'model-viewer'/'current.json').write_text(json.dumps({'model':out.name,'note':'양쪽 연결판·양쪽 슬롯 / 전체 길이 가이드 / ±5mm'},ensure_ascii=False))
