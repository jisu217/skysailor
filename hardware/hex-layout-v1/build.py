from pathlib import Path
import trimesh,numpy as np,json,base64
out=Path(__file__).resolve().parent
base=trimesh.creation.cylinder(radius=27.5,height=2,sections=6)
base.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,0,1]));base.apply_translation([0,0,1])
base.export(out/'hex-55mm-plain-plate.stl')
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
meshes={'base':base};reserved={}
for i,angle in enumerate([0,120,240]):
    rot=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,0,1])
    g=gear.copy();g.apply_translation([0,17,3]);g.apply_transform(rot);meshes[f'gear{i}']=g
    w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,6.95],[0,1,0,4],[0,0,0,1]]));w.apply_transform(rot);meshes[f'worm{i}']=w
    m=trimesh.creation.cylinder(radius=3,height=15,sections=64);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([-11.5,6.95,4]);m.apply_transform(rot);meshes[f'motor{i}']=m
    a=np.deg2rad(150+angle);x,y=24*np.cos(a),24*np.sin(a)
    mark=trimesh.creation.annulus(r_min=1.7,r_max=2,height=.08,sections=64);mark.apply_translation([x,y,2.04]);meshes[f'marker{i}']=mark
    reserve=trimesh.creation.cylinder(radius=2,height=4,sections=64);reserve.apply_translation([x,y,4]);reserved[f'post-space{i}']=reserve
# Check footprints against six exact hexagonal half-planes.
normals=np.column_stack((np.cos(np.deg2rad(np.arange(6)*60+120)),np.sin(np.deg2rad(np.arange(6)*60+120))))
checks={};parts={k:v for k,v in meshes.items() if k!='base' and not k.startswith('marker')};parts.update(reserved)
for name,m in parts.items():
    margin=float((27.5*np.cos(np.pi/6)-m.vertices[:,:2]@normals.T).min())
    checks[name+'_edge_margin_mm']=margin
    assert margin>=0,(name,margin)
names=list(parts)
for i,a in enumerate(names):
    for b in names[i+1:]:
        ma,mb=parts[a],parts[b]
        if np.any(ma.bounds[1]<mb.bounds[0]) or np.any(mb.bounds[1]<ma.bounds[0]):continue
        inter=trimesh.boolean.intersection([ma,mb],engine='manifold')
        v=float(inter.volume) if len(inter.faces) else 0
        assert v<.001,(a,b,v)
data={}
for name,m in meshes.items():
    sm=m.simplify_quadric_decimation(face_count=2200) if len(m.faces)>2200 else m
    data[name]={k:base64.b64encode(np.asarray(v,dtype=t).tobytes()).decode() for k,v,t in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/hex-layout-v1.html')
target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
(out/'dimensions.json').write_text(json.dumps(dict(corner_span_mm=55,across_flats_mm=55*np.cos(np.pi/6),plate_thickness_mm=2,gear_centre_radius_mm=17,post_reserved_radius_mm=24,post_reserved_diameter_mm=4,worm_axis_z_mm=4,motor_plate_overlap_mm=1,stage='Layout only: no pockets, posts, shafts or upper plate. Motor/worm plate intersections intentionally await recess design.',checks=checks),indent=2))
print('Footprints and mutual clearances passed.',checks,'Viewer bytes',target.stat().st_size)
