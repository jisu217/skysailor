from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
def box(size,pos):
 m=trimesh.creation.box(extents=size);m.apply_translation(pos);return m
# One-millimetre contour shell around the T rail, clearance 0.2 mm.
outer=trimesh.boolean.union([box([12,8.4,4.4],[0,0,1]),box([12,4,3],[0,0,3.7])],engine='manifold')
voids=[box([12.2,6.4,2.4],[0,0,1]),box([12.2,2,4.4],[0,0,2])]
unit=trimesh.boolean.difference([outer]+voids,engine='manifold')
# External triangular ribs at the recessed shoulders, 1 mm thick along X.
ribs=[]
for x in [-5,5]:
 for sign in [-1,1]:
  profile=[(sign*1.98,3.18),(sign*3.2,3.18),(sign*1.98,4.4)]
  v=[(xx,y,z) for xx in [x-.5,x+.5] for y,z in profile]
  f=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
  rib=trimesh.Trimesh(vertices=v,faces=f);rib.fix_normals();ribs.append(rib)
unit=trimesh.boolean.union([unit]+ribs,engine='manifold')
assert unit.is_volume and unit.is_watertight
sliders=[]
for x in [-25,25]:
 m=unit.copy();m.apply_translation([x,0,0]);sliders.append(m)
# Lower connecting plate is also 1 mm thick; top z=-0.2.
sliders.append(box([62,8.4,1],[0,0,-.7]))
linked=trimesh.boolean.union(sliders,engine='manifold')
assert linked.is_volume and linked.is_watertight and len(linked.split())==1
for dx in [-15,0,15]:
 test=linked.copy();test.apply_translation([dx,0,0])
 hit=trimesh.boolean.intersection([base,test],engine='manifold')
 assert hit.is_empty or abs(hit.volume)<1e-5
printed=linked.copy();printed.apply_translation([0,0,1.2]);printed.export(out/'linked-slider-print.stl')
meshes=[base,linked]
assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>ㅗ자 밀착형 슬라이더 · 삼각 보강</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>ㅗ자 밀착형 슬라이더 · 삼각 보강</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>중심 간격 50mm · 쉘 / 아래판 두께 1mm · 유격 0.2mm · 삼각 보강 8개 · 이동 ±15mm</small><div style="margin-top:16px"><button id="closeup">슬라이더 확대</button><label> 이동 <input id="travel" type="range" min="-15" max="15" value="0" step="0.1"></label></div>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','assembly.stl').replace('</nav>','<a href="linked-slider-print.stl" download>슬라이더 STL</a></nav>')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='const moving=new T.Group();scene.add(moving);let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;const part=new T.Mesh(geom,new T.MeshStandardMaterial({color:i===0?0x85c9de:0xf0b66b,roughness:.4,flatShading:true}));if(i===0)scene.add(part);else moving.add(part)});'''
assert old in s;s=s.replace(old,new)
s=s.replace("update();document.querySelector('#status')","document.querySelector('#closeup').onclick=()=>{target.set(moving.position.x,0,1);d=145;az=-1.1;el=.6;update()};document.querySelector('#travel').oninput=e=>{moving.position.x=Number(e.target.value);update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(25,Math.min')
(out/'preview.html').write_text(s)
old=trimesh.load(out.parent/'ring-380-u-sliders-linked/linked-slider-print.stl',force='mesh')
print(json.dumps({'watertight':linked.is_watertight,'volume_mm3':linked.volume,'PLA_g':linked.volume/1000*1.24,'material_reduction_percent':100*(1-linked.volume/old.volume)}))
