from pathlib import Path
import trimesh as t, numpy as np, json
out=Path(__file__).resolve().parent
old=t.load(out.parent/'615-worm-clearance-v2'/'worm.stl')
def cyl(r,h):
 m=t.creation.cylinder(r,h,sections=64);m.apply_transform(t.geometry.align_vectors([0,0,1],[1,0,0]));m.apply_translation([0,0,6]);return m
m=t.boolean.difference([t.boolean.union([old,cyl(.7,15)],engine='manifold'),cyl(.5,17)],engine='manifold')
assert m.is_volume and len(m.split())==1
assert np.allclose(m.bounds,old.bounds)
removed=t.boolean.difference([old,m],engine='manifold')
assert removed.is_empty or abs(removed.volume)<1e-5
assert t.boolean.intersection([m,cyl(.499,17)],engine='manifold').is_empty
m.export(out/'worm.stl')
p=m.copy();p.apply_transform(t.geometry.align_vectors([1,0,0],[0,0,1]));p.apply_translation([-p.centroid[0],-p.centroid[1],-p.bounds[0,2]]);p.export(out/'worm-bore-1.0mm-print.stl')
report={'motor_bore_diameter_mm':1.0,'outer_dimensions_mm':m.extents.tolist(),'watertight':bool(m.is_watertight),'outer_envelope_unchanged':True}
(out/'inspection.json').write_text(json.dumps(report,indent=2));print(report)
