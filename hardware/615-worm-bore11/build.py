from pathlib import Path
import trimesh as t, numpy as np, json
out=Path(__file__).resolve().parent
src=out.parent/'615-worm-clearance-v2'
old=t.load(src/'worm.stl')
def cyl(r,h):
 m=t.creation.cylinder(r,h,sections=64);m.apply_transform(t.geometry.align_vectors([0,0,1],[1,0,0]));m.apply_translation([0,0,6]);return m
filled=t.boolean.union([old,cyl(.7,15)],engine='manifold')
m=t.boolean.difference([filled,cyl(.55,17)],engine='manifold')
assert m.is_volume and len(m.split())==1
assert np.allclose(m.bounds,old.bounds)
# Material is only added within the original bore; the outer envelope is unchanged.
removed=t.boolean.difference([old,m],engine='manifold')
assert removed.is_empty or abs(removed.volume)<1e-5
assert t.boolean.intersection([m,cyl(.549,17)],engine='manifold').is_empty
m.export(out/'worm.stl')
data=json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':'))
(out/'worm.json').write_text(data)
p=m.copy();p.apply_transform(t.geometry.align_vectors([1,0,0],[0,0,1]));p.apply_translation([-p.centroid[0],-p.centroid[1],-p.bounds[0,2]]);p.export(out/'worm-bore-1.1mm-print.stl')
(out/'inspection.json').write_text(json.dumps({'motor_bore_diameter_mm':1.1,'previous_mm':1.2,'outer_dimensions_mm':m.extents.tolist(),'watertight':bool(m.is_watertight),'outer_envelope_unchanged':True},indent=2))
# The integrated model uses the new worm; keep other parts unchanged.
assembly=out.parent/'central-xy-tested-actuators'
m.export(assembly/'worm.stl');(assembly/'worm.json').write_text(data)
f=assembly/'build.py';s=f.read_text();s=s.replace("t.load(src/f'{name}.stl')", "t.load((out.parent/'615-worm-bore11' if name=='worm' else src)/f'{name}.stl')");f.write_text(s)
f=assembly/'preview.html';s=f.read_text().replace('웜 지지축 Ø2.8 × 15mm','웜 지지축 Ø2.8 × 15mm<br>모터 축 구멍 Ø1.1mm');f.write_text(s)
print((out/'inspection.json').read_text())
