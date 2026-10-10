from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-eight-ribs-pillar'
base=trimesh.load(source/'ring-380-eight-ribs-pillar.stl',force='mesh')
# Wheels rest on z=2 floor; R5 gives axle center z=7.
parts=[]
for y in [-1.9,1.9]:
 wheel=trimesh.creation.cylinder(radius=5,height=1.4,sections=192)
 wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
 wheel.apply_translation([40,y,7]);parts.append(wheel)
axle=trimesh.creation.cylinder(radius=2,height=5.2,sections=96)
axle.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));axle.apply_translation([40,0,7]);parts.append(axle)
unit=trimesh.boolean.union(parts,engine='manifold')
assert unit.is_volume and unit.is_watertight and len(unit.split())==1
hit=trimesh.boolean.intersection([base,unit],engine='manifold')
assert hit.is_empty or abs(hit.volume)<1e-6
unit.export(out/'roller-pair-assembled.stl');base.export(out/'frame.stl')
assembly=trimesh.util.concatenate([base,unit]);assembly.export(out/'assembly.stl')
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>X축 롤러 한 쌍 · R5mm</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>X축 롤러 한 쌍 · R5mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>반지름 5mm / 지름 10mm · 롤러 폭 1.4mm · 연결 축 Ø4mm · 중앙에서 X=40mm</small><div style="margin-top:16px"><button id="closeup">롤러 확대</button></div>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','assembly.stl')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new=f'''g.clearGroups();g.addGroup(0,{len(base.faces)*3},0);g.addGroup({len(base.faces)*3},{len(unit.faces)*3},1);scene.add(new T.Mesh(g,[new T.MeshStandardMaterial({{color:0x85c9de,roughness:.4,flatShading:true}}),new T.MeshStandardMaterial({{color:0xf0b66b,roughness:.4,flatShading:true}})]));'''
assert old in s;s=s.replace(old,new)
s=s.replace("update();document.querySelector('#status')","document.querySelector('#closeup').onclick=()=>{target.set(40,0,6);d=65;az=-1.1;el=.6;update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(25,Math.min')
(out/'preview.html').write_text(s)
print('Two R5 rollers joined by diameter 4mm axle; no frame interference. Old carriage omitted.')
