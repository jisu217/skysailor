from pathlib import Path
import json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-center-ring-54-no-pillar'
base=trimesh.load(source/'ring-380-center-ring-54-no-pillar.stl',force='mesh')
disc=trimesh.creation.cylinder(radius=14.5,height=2,sections=512)
disc.apply_translation([0,0,3.2])
lower=trimesh.creation.cylinder(radius=14.5,height=2,sections=512)
lower.apply_translation([0,0,-1.2])
post=trimesh.creation.cylinder(radius=2.5,height=2.6,sections=128)
post.apply_translation([0,0,1])
disc=trimesh.boolean.union([disc,lower,post],engine='manifold')
assert disc.is_watertight and disc.is_volume and len(disc.split())==1
assert np.allclose(disc.bounds,[[-14.5,-14.5,-2.2],[14.5,14.5,4.2]])
intersection=trimesh.boolean.intersection([base,disc],engine='manifold')
assert intersection.is_empty or abs(intersection.volume)<1e-6
base.export(out/'frame.stl')
disc.export(out/'double-disc-assembled.stl')
printed=disc.copy();printed.apply_translation([0,0,2.2]);printed.export(out/'double-disc-print.stl')
assembly=trimesh.util.concatenate([base,disc]);assembly.export(out/'assembly.stl')
assert len(assembly.split())==2
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>위아래 원판 Ø29mm · 중앙 기둥 Ø5mm</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>위아래 원판 Ø29mm · 중앙 기둥 Ø5mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>위아래 원판 Ø29mm / 두께 각 2mm · 양쪽 유격 각 0.2mm · 연결 기둥 Ø5mm</small>',s)
s=s.replace('ring-380-center-ring-54-no-pillar.stl','assembly.stl')
s=s.replace('STL 다운로드','조립 STL').replace('</nav>','<a href="double-disc-print.stl" download>연결 원판 STL</a></nav>')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new=f'''g.clearGroups();g.addGroup(0,{len(base.faces)*3},0);g.addGroup({len(base.faces)*3},{len(disc.faces)*3},1);scene.add(new T.Mesh(g,[new T.MeshStandardMaterial({{color:0x85c9de,roughness:.4,flatShading:true}}),new T.MeshStandardMaterial({{color:0xf0b66b,roughness:.4,flatShading:true}})]));'''
assert old in s;s=s.replace(old,new)
(out/'preview.html').write_text(s)
print(json.dumps({'disc_diameter_mm':29,'disc_thickness_mm':2,'vertical_gap_mm':.2,'separate_bodies':2,'disc_mass_PLA_g':disc.volume/1000*1.24}))
