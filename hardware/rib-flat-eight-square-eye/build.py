from pathlib import Path
import trimesh,numpy as np,json,math,re
out=Path(__file__).resolve().parent;root=out.parent
length=214.7*math.asin(190/215)
# Strip runs from x=0 to x=length, with terminal disc centered at length.
strip=trimesh.creation.box(extents=[length,3,.6]);strip.apply_translation([length/2,0,.3])
eye=trimesh.creation.cylinder(radius=4,height=.6,sections=192);eye.apply_translation([length,0,.3])
blank=trimesh.boolean.union([strip,eye],engine='manifold')
hole=trimesh.creation.box(extents=[3.4,3.4,1]);hole.apply_translation([length,0,.3])
rib=trimesh.boolean.difference([blank,hole],engine='manifold')
assert rib.is_watertight and rib.is_volume and len(rib.split())==1
rib.export(out/'single-rib-square-eye.stl')
parts=[]
for i in range(8):
 m=rib.copy();m.apply_translation([8,8+i*10,0]);m.export(out/f'rib-{i+1:02d}.stl');parts.append(m)
kit=trimesh.util.concatenate(parts);kit.export(out/'eight-ribs-print.stl')
s=(root/'ring-380-eight-ribs-pillar/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':kit.vertices.tolist(),'faces':kit.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>평면 리브 8개 · 사각 구멍 결합판</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>띠 232.68 × 3 × 0.6mm · 끝 원판 Ø8 × 0.6mm · 구멍 3.4mm 정사각형 · 구멍 중심까지 232.68mm</small>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','eight-ribs-print.stl')
s=s.replace('new T.Vector3(0,0,48)','new T.Vector3(126,43,.3)').replace('target.set(0,0,48)','target.set(126,43,.3)').replace('d=820','d=420')
s=s.replace('new T.Vector3(0,0,1)','new T.Vector3(126,43,.3)').replace('target.set(0,0,1)','target.set(126,43,.3)')
s=s.replace('</nav>','<a href="single-rib-square-eye.stl" download>1개 STL</a></nav>')
(out/'preview.html').write_text(s)
spec={'strip_to_eye_center_mm':length,'full_part_length_mm':float(rib.extents[0]),'eye_diameter_mm':8,'square_hole_mm':3.4,'thickness_mm':.6,'kit_bounds_mm':kit.extents.tolist(),'PLA_total_g':kit.volume*.00124}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
