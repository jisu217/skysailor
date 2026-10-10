from pathlib import Path
import json, base64
import numpy as np
import trimesh

out=Path(__file__).resolve().parent
plate=trimesh.creation.cylinder(radius=35,height=2,sections=256)
plate.apply_translation([0,0,1])
centres=[]
cutters=[]
for angle in [90,210,330]:
    t=np.deg2rad(angle)
    x,y=23*np.cos(t),23*np.sin(t)
    centres.append([float(x),float(y)])
    cutter=trimesh.creation.cylinder(radius=8.2,height=2,sections=192)
    cutter.apply_translation([x,y,2])
    cutters.append(cutter)
plate=trimesh.boolean.difference([plate,*cutters],engine='manifold')
assert plate.is_watertight and plate.is_winding_consistent and len(plate.split())==1
assert np.allclose(plate.extents,[70,70,2])
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
for x,y in centres:
    fitted=gear.copy()
    fitted.apply_translation([x,y,1])
    interference=trimesh.boolean.intersection([plate,fitted],engine='manifold')
    assert abs(interference.volume)<1e-5
plate.export(out/'disc-70x2mm-three-pockets.stl')
spec=dict(diameter_mm=70,thickness_mm=2,pocket_diameter_mm=16.4,pocket_depth_mm=1,
          floor_thickness_mm=1,centre_radius_mm=23,spacing_degrees=120,centres_xy_mm=centres,
          radial_clearance_mm=(16.4-float(gear.extents[0]))/2,watertight=True,gear_interference_mm3=0)
(out/'dimensions.json').write_text(json.dumps(spec,indent=2))
data={key:base64.b64encode(np.asarray(val,dtype=dtype).tobytes()).decode()
      for key,val,dtype in [('v',plate.vertices,'<f4'),('f',plate.faces,'<u4')]}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/disc-three-pockets.html')
target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
print(json.dumps(spec))
