from pathlib import Path
import trimesh,numpy as np,json,base64
out=Path(__file__).resolve().parent
old=out.parent/'disc-three-pockets'
spec=json.loads((old/'dimensions.json').read_text())
base=trimesh.load(old/'disc-70x2mm-three-pockets.stl')
posts=[]
for x,y in spec['centres_xy_mm']:
    post=trimesh.creation.cylinder(radius=1.5,height=4,sections=96)
    post.apply_translation([x,y,2])
    posts.append(post)
base=trimesh.boolean.union([base,*posts],engine='manifold')
assert base.is_watertight and base.is_winding_consistent and len(base.split())==1
assert np.allclose(base.extents,[70,70,4])
base.export(out/'disc-70mm-three-posts.stl')
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
meshes={'base':base}
for i,(x,y) in enumerate(spec['centres_xy_mm']):
    g=gear.copy();g.apply_translation([x,y,1]);meshes['gear'+str(i)]=g
    inter=trimesh.boolean.intersection([base,g],engine='manifold')
    assert len(inter.faces)==0 or abs(inter.volume)<1e-6
spec.update(post_diameter_mm=3,post_top_z_mm=4,post_height_above_pocket_floor_mm=3,
            gear_bottom_z_mm=1,gear_top_z_mm=3,post_above_gear_mm=1,gear_count=3,
            validated_static_interference_mm3=0)
(out/'dimensions.json').write_text(json.dumps(spec,indent=2))
data={}
for k,m in meshes.items():
    sm=m.simplify_quadric_decimation(face_count=6000) if len(m.faces)>6000 else m
    data[k]={key:base64.b64encode(np.asarray(val,dtype=typ).tobytes()).decode() for key,val,typ in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
s=(out/'viewer-template.html').read_text()
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/disc-three-gears.html')
target.write_text(s.replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
print('Watertight base; three gears; zero static interference;',target.stat().st_size,'viewer bytes')
