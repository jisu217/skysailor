from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-center-seat-11'
base=trimesh.load(src/'frame-seat-11-hole-5.stl',force='mesh')
wall=trimesh.creation.annulus(r_min=4.5,r_max=5.5,height=8,sections=256);wall.apply_translation([0,0,5])
base=trimesh.boolean.union([base,wall],engine='manifold')
# Radial through-holes, one per cardinal position, near top of wall.
holes=[];anchors=[]
for a in np.arange(4)*math.pi/2:
 p=np.array([5*math.cos(a),5*math.sin(a),7.5]);direction=np.array([math.cos(a),math.sin(a),0])
 h=trimesh.creation.cylinder(radius=.6,height=5,sections=64)
 h.apply_transform(trimesh.geometry.align_vectors([0,0,1],direction));h.apply_translation(p);holes.append(h);anchors.append(p.tolist())
base=trimesh.boolean.difference([base]+holes,engine='manifold')
zc=1+math.sqrt(4**2-2.5**2)
ball=trimesh.creation.icosphere(subdivisions=4,radius=4);ball.apply_translation([0,0,zc])
rod=trimesh.creation.cylinder(radius=1.5,height=32,sections=96);rod.apply_translation([0,0,zc-16])
moving=trimesh.boolean.union([ball,rod],engine='manifold')
for m in [base,moving]:assert m.is_volume and m.is_watertight
base.export(out/'frame-raised-seat.stl');moving.export(out/'ball-and-rod.stl')
meshes=[base,moving];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>구 Ø8 · 막대 Ø3 · 꼭대기 연결선 4개</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>받침 외경 11mm · 벽 높이 8mm · 묶음 구멍 Ø1.2mm × 4 · 막대 길이 32mm · 노란 선은 실 배치 표시</small>',s)
s=s.replace('frame-seat-11-hole-5.stl','assembly.stl')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:i===0?0x85c9de:0xf0b66b,roughness:.45,flatShading:true}))) });
const anchors='''+json.dumps(anchors)+''';for(const p of anchors){const geo=new T.BufferGeometry().setFromPoints([new T.Vector3(...p),new T.Vector3(0,0,115.38)]);scene.add(new T.Line(geo,new T.LineBasicMaterial({color:0xffd166})))}
'''
assert old in s;s=s.replace(old,new).replace('target.set(0,0,1);d=50','target.set(0,0,-3);d=90')
(out/'preview.html').write_text(s)
print('Ball/rod and raised seat exported. Four radial holes and four conceptual top tie lines shown. No tilt/retainer verification yet.')
