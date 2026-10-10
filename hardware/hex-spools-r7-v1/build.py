from pathlib import Path
import trimesh,numpy as np,json,base64
out=Path(__file__).resolve().parent
base=trimesh.creation.cylinder(radius=27.5,height=2,sections=6)
base.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,0,1]));base.apply_translation([0,0,1])
def thread(length,clearance=0,wide=0):
 n=160;nz=int(length/.025)+1;zs=np.linspace(0,length,nz);t=np.arange(n)*2*np.pi/n;v=[]
 for z in zs:
  phase=(z-1.2*t/(2*np.pi)+.6)%1.2-.6
  r=1.5+np.clip((.45+wide-np.abs(phase))*1.667,0,.5)+clearance
  v.extend(np.column_stack([r*np.cos(t),r*np.sin(t),np.full(n,z)]))
 f=[]
 for k in range(nz-1):
  for i in range(n):
   j=(i+1)%n;a=k*n+i;b=k*n+j;c=(k+1)*n+j;d=(k+1)*n+i;f.extend([[a,b,c],[a,c,d]])
 v.extend([[0,0,0],[0,0,length]]);bot=len(v)-2;top=bot+1
 for i in range(n):
  j=(i+1)%n;f.extend([[bot,j,i],[top,(nz-1)*n+i,(nz-1)*n+j]])
 return trimesh.Trimesh(v,f,process=True)

supports=[];bores=[];topcuts=[];pilotcuts=[];clearcuts=[];topbumps=[]
screw=trimesh.load(out.parent/'printed-screw-v1/screw.stl')
screw.export(out/'printed-screw.stl')
top=base.copy();top.apply_translation([0,0,6])
gear=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
# Preserve tooth surfaces; fill the old bore and add coaxial journals.
def cylinder(r,h,z):
    m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
hub=cylinder(1.9,2,1)
lower=cylinder(1.5,3.2,-1.4)
upper=cylinder(1.5,8,5.8)
# Flat only above the upper plate: global z8.3 and above.
flat=trimesh.creation.box([5,5,6]);flat.apply_translation([3.5,0,8.3])
upper=trimesh.boolean.difference([upper,flat],engine='manifold')
gear=trimesh.boolean.union([gear,hub,lower,upper],engine='manifold')
assert gear.is_watertight and len(gear.split())==1
printing=gear.copy();printing.apply_translation([0,0,3]);printing.export(out/'gear-with-shaft.stl')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
# Separate spool: two 0.5 mm flanges and a 2 mm winding span.
spool=trimesh.boolean.union([cylinder(7,.75,.375),cylinder(3,3.3,2.25),cylinder(7,.75,4.125)],engine='manifold')
dhole=cylinder(1.6,7,2.25)
dflat=trimesh.creation.box([5,5,7]);dflat.apply_translation([3.6,0,2.25])
dhole=trimesh.boolean.difference([dhole,dflat],engine='manifold')
spool=trimesh.boolean.difference([spool,dhole],engine='manifold')
assert spool.is_watertight and len(spool.split())==1
spool.export(out/'spool-14mm-height-4.5mm.stl')
meshes={'base':base};reserved={}
for i,angle in enumerate([0,120,240]):
    rot=trimesh.transformations.rotation_matrix(np.deg2rad(angle),[0,0,1])
    sp=spool.copy();sp.apply_translation([0,17,8.3]);sp.apply_transform(rot);meshes[f'spool{i}']=sp
    g=gear.copy();g.apply_translation([0,17,3]);g.apply_transform(rot);meshes[f'gear{i}']=g
    w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,6.95],[0,1,0,4],[0,0,0,1]]));w.apply_transform(rot);meshes[f'worm{i}']=w
    m=trimesh.creation.cylinder(radius=3,height=15,sections=64);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([-11.5,6.95,4]);m.apply_transform(rot);meshes[f'motor{i}']=m
    # Gear rests on a 0.8 mm tall shoulder; its pin is one of the six posts.
    shoulder=trimesh.creation.cylinder(radius=2.8,height=1.2,sections=96)
    shoulder.apply_translation([0,17,2.4]);shoulder.apply_transform(rot);supports.append(shoulder)
    bore=cylinder(1.8,14,5);bore.apply_translation([0,17,0]);bore.apply_transform(rot);bores.append(bore)
    cut=trimesh.creation.cylinder(radius=3.15,height=15.4,sections=96);cut.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));cut.apply_translation([-11.5,6.95,4]);cut.apply_transform(rot);topcuts.append(cut)
    wc=trimesh.creation.cylinder(radius=3.2,height=6.4,sections=96);wc.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));wc.apply_translation([0,6.95,4]);wc.apply_transform(rot);topcuts.append(wc)
    a=np.deg2rad(150+angle);x,y=28*np.cos(a),28*np.sin(a)
    post=trimesh.creation.cylinder(radius=4,height=6,sections=192);post.apply_translation([x,y,3]);supports.append(post)
    reserve=trimesh.creation.cylinder(radius=4,height=4,sections=64);reserve.apply_translation([x,y,4]);reserved[f'post-space{i}']=reserve
    pilot=thread(7,.2,.08);pilot.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]));pilot.apply_translation([x,y,8.6]);pilotcuts.append(pilot)
    clearance=cylinder(2.25,3,7);clearance.apply_translation([x,y,0]);clearcuts.append(clearance)
    bump=cylinder(4,2,7);bump.apply_translation([x,y,0]);topbumps.append(bump)
    bolt=screw.copy();bolt.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]));bolt.apply_translation([x,y,10]);meshes[f'screw{i}']=bolt
base=trimesh.boolean.union([base,*supports],engine='manifold')
base=trimesh.boolean.difference([base,*bores,*topcuts,*pilotcuts],engine='manifold')
top=trimesh.boolean.union([top,*topbumps],engine='manifold')
top=trimesh.boolean.difference([top,*bores,*topcuts,*clearcuts],engine='manifold')
assert base.is_watertight and top.is_watertight and len(base.split())==1
pt=top.copy();pt.apply_translation([0,0,-6]);pt.export(out/'upper-plate-reference.stl')
base.export(out/'lower-plate-shaft-holes.stl');meshes['base']=base
# Check footprints against six exact hexagonal half-planes.
normals=np.column_stack((np.cos(np.deg2rad(np.arange(6)*60+120)),np.sin(np.deg2rad(np.arange(6)*60+120))))
checks={};parts={k:v for k,v in meshes.items() if k!='base' and not k.startswith('marker')};parts.update(reserved)
for name,m in parts.items():
    margin=float((27.5*np.cos(np.pi/6)-m.vertices[:,:2]@normals.T).min())
    checks[name+'_edge_margin_mm']=margin
    assert margin>=0 or name.startswith(('post-space','screw','spool')),(name,margin)
names=[name for name in parts if not name.startswith('screw')]
for i,a in enumerate(names):
    for b in names[i+1:]:
        ma,mb=parts[a],parts[b]
        if np.any(ma.bounds[1]<mb.bounds[0]) or np.any(mb.bounds[1]<ma.bounds[0]):continue
        inter=trimesh.boolean.intersection([ma,mb],engine='manifold')
        v=float(inter.volume) if len(inter.faces) else 0
        assert v<.001,(a,b,v)
for name,m in meshes.items():
    if name.startswith(('gear','spool','screw')):
        inter=trimesh.boolean.intersection([trimesh.util.concatenate([base,top]),m],engine='manifold')
        assert not len(inter.faces) or abs(inter.volume)<1e-6
# Lossless byte-shuffle + gzip; retain all original triangles and reuse identical parts.
import gzip
canonical={'base':base,'top':top,'gear':gear,'worm':worm,'spool':spool,'screw':screw}
canonical['motor']=trimesh.creation.cylinder(radius=3,height=15,sections=64)
def pack(array,delta=False):
    raw=(np.asarray(array,dtype='<i4') if delta else np.round(np.asarray(array)*10000).astype('<i4')).ravel()
    raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
    shuffled=raw.view('u1').reshape(-1,4).T.tobytes()
    return base64.b64encode(gzip.compress(shuffled)).decode()
# Reindex only, without deleting any triangle, for efficient lossless compression.
for m in canonical.values():
    order=np.lexsort((np.arctan2(m.vertices[:,1],m.vertices[:,0]),np.round(m.vertices[:,2],6)))
    inverse=np.empty_like(order);inverse[order]=np.arange(len(order))
    vertices=m.vertices[order].copy();faces=inverse[m.faces]
    faces=np.take_along_axis(faces,(np.arange(3)[None,:]+faces.argmin(axis=1)[:,None])%3,axis=1)
    faces=faces[np.lexsort((faces[:,2],faces[:,1],faces[:,0]))]
    m.vertices=vertices;m.faces=faces
data={name:{'v':pack(m.vertices),'f':pack(m.faces,True),'triangles':len(m.faces)} for name,m in canonical.items()}
print('Full resolution triangles:', {k:len(m.faces) for k,m in canonical.items()})
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/hex-spools-r7-v1.html')
target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(data)))
assert target.stat().st_size<5000000
(out/'dimensions.json').write_text(json.dumps(dict(spool_flange_diameter_mm=14,spool_barrel_diameter_mm=6,spool_winding_width_mm=3,spool_height_mm=4.5,spool_bottom_z_mm=8.3,spool_top_plate_gap_mm=.3,spool_d_bore_diameter_mm=3.2,spool_d_flat_x_mm=1.1,connection_posts=3,rotating_gear_shafts=3,shaft_diameter_mm=3,bearing_hole_mm=3.6,upper_plate_z_mm=[6,8],shaft_top_z_mm=12.8,connection_post_diameter_mm=8,screw_size="custom 4mm pitch1.2",upper_clearance_diameter_mm=4.5,thread_radial_clearance_mm=.2,thread_flank_relief_mm=.08,screw_file="printed-screw.stl",thread_status="Printed mating thread uses user-tested clearance",gear_pin_diameter_mm=3,post_top_z_mm=6,gear_shoulder_diameter_mm=5.6,gear_shoulder_top_z_mm=3,corner_span_mm=55,across_flats_mm=55*np.cos(np.pi/6),plate_thickness_mm=2,gear_centre_radius_mm=17,post_reserved_radius_mm=28,post_reserved_diameter_mm=8,worm_axis_z_mm=4,motor_plate_overlap_mm=1,stage='Rotating integral shafts, D ends above upper plate. Upper plate M2 screw holes provided; spool axial retention pending.',checks=checks),indent=2))
print('Footprints and mutual clearances passed.',checks,'Viewer bytes',target.stat().st_size)
