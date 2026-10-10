from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
def box(size,pos):
 m=trimesh.creation.box(extents=size);m.apply_translation(pos);return m
# Channel width 2.0 around 1.6 wall: 0.2 each side.
# Feet rest at floor z=2; channel ceiling z=4.2 leaves 0.2 above wall.
parts=[box([12,5.2,1.6],[0,0,5])]
for y in [-1.8,1.8]:parts.append(box([12,1.6,3.8],[0,y,3.9]))
unit=trimesh.boolean.union(parts,engine='manifold')
assert unit.is_volume and unit.is_watertight
printed=unit.copy();printed.apply_translation([0,0,-2]);printed.export(out/'u-slider-print.stl')
sliders=[]
for x in [-40,40]:
 m=unit.copy();m.apply_translation([x,0,0]);sliders.append(m)
 for dx in [-15,0,15]:
  test=m.copy();test.apply_translation([dx,0,0])
  hit=trimesh.boolean.intersection([base,test],engine='manifold')
  assert hit.is_empty or abs(hit.volume)<1e-5
meshes=[base]+sliders
assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>양쪽 X축 ㄷ자 슬라이더</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>양쪽 X축 ㄷ자 슬라이더</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>슬라이더 길이 12mm · 두께 1.6mm · 홈 폭 2mm · 좌우 / 위 유격 0.2mm · 양쪽 X=±40mm</small><div style="margin-top:16px"><button id="closeup">슬라이더 확대</button><label> 이동 <input id="travel" type="range" min="-15" max="15" value="0" step="0.1"></label></div>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','assembly.stl').replace('</nav>','<a href="u-slider-print.stl" download>슬라이더 STL</a></nav>')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='const moving=new T.Group();scene.add(moving);let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;const part=new T.Mesh(geom,new T.MeshStandardMaterial({color:i===0?0x85c9de:0xf0b66b,roughness:.4,flatShading:true}));if(i===0)scene.add(part);else moving.add(part)});'''
assert old in s;s=s.replace(old,new)
s=s.replace("update();document.querySelector('#status')","document.querySelector('#closeup').onclick=()=>{target.set(40+moving.position.x,0,4);d=55;az=-1.1;el=.6;update()};document.querySelector('#travel').oninput=e=>{moving.position.x=Number(e.target.value);update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(25,Math.min')
(out/'preview.html').write_text(s)
print('Two separate U sliders validated at +/-15mm travel; roller assembly omitted.')
