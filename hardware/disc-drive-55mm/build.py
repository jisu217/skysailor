from pathlib import Path
import trimesh,numpy as np,json,base64
out=Path(__file__).resolve().parent
base=trimesh.load(out.parent/'disc-three-gears/disc-70mm-three-posts.stl')
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
meshes={};cuts=[]
def horizontal(radius,length,x,y,z):
    m=trimesh.creation.cylinder(radius=radius,height=length,sections=96)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]))
    m.apply_translation([x,y,z]);return m
for i,angle in enumerate([0,120,240]):
    rotation=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,0,1])
    g=gear.copy();g.apply_translation([0,23,1]);g.apply_transform(rotation);meshes[f'gear{i}']=g
    w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,12.95],[0,1,0,2],[0,0,0,1]]));w.apply_transform(rotation);meshes[f'worm{i}']=w
    motor=horizontal(3,15,-11.5,12.95,2);motor.apply_transform(rotation);meshes[f'motor{i}']=motor
    # Illustrative shaft only; actual motor shaft diameter/protrusion unmeasured.
    shaft=horizontal(.45,2,-3,12.95,2);shaft.apply_transform(rotation);meshes[f'shaft{i}']=shaft
    cut=trimesh.creation.box([23,6.8,6]);cut.apply_translation([-7.5,12.95,1]);cut.apply_transform(rotation);cuts.append(cut)
base=trimesh.boolean.difference([base,*cuts],engine='manifold')
limit=trimesh.creation.cylinder(radius=27.5,height=10,sections=256)
limit.apply_translation([0,0,2])
base=trimesh.boolean.intersection([base,limit],engine='manifold')
assert base.is_watertight and len(base.split())==1
base.export(out/'disc-55mm-drive-clearances.stl');meshes['base']=base
checks={}
names=[n for n in meshes if not n.startswith('shaft')]
for i,a in enumerate(names):
    for b in names[i+1:]:
        ma,mb=meshes[a],meshes[b]
        if np.any(ma.bounds[1]<mb.bounds[0]) or np.any(mb.bounds[1]<ma.bounds[0]):continue
        inter=trimesh.boolean.intersection([ma,mb],engine='manifold')
        v=float(inter.volume) if len(inter.faces) else 0
        checks[a+' / '+b]=v
        assert v<.001,(a,b,v)
data={}
for name,m in meshes.items():
    sm=m.simplify_quadric_decimation(face_count=2400) if len(m.faces)>2400 else m
    data[name]={k:base64.b64encode(np.asarray(v,dtype=t).tobytes()).decode() for k,v,t in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/disc-drive-55mm.html')
target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<1000000
(out/'dimensions.json').write_text(json.dumps(dict(plate_diameter_mm=55,plate_thickness_mm=2,gear_centre_radius_mm=23,worm_axis_z_mm=2,centre_distance_mm=10.05,motor_body_diameter_mm=6,motor_body_length_mm=15,motor_bottom_z_mm=-1,shaft_reference_only=True,mounts_pending=True,static_intersections_mm3=checks),indent=2))
print('Static clearances passed; viewer bytes:',target.stat().st_size)
