from pathlib import Path
import trimesh,numpy as np,json,base64,gzip
out=Path(__file__).resolve().parent
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
# Plain circular outer flanges; tooth grooves are in the inward-facing surfaces.
blank=trimesh.boolean.union([cyl(7.912,2,1),cyl(7.912,2,7),cyl(3,4.2,4),cyl(1.5,3.2,-1.4),cyl(1.5,3.2,9.4)],engine='manifold')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
c=6.5
placement=np.array([[0,0,1,-3],[1,0,0,-c],[0,1,0,4],[0,0,0,1]])
w=worm.copy();w.apply_transform(placement)
# Relief enlarged only in radial thread dimensions; retain the original visible worm.
cut=worm.copy();cut.vertices[:,:2]*=1.04;cut.apply_transform(placement)
cutters=[]
for angle in np.arange(24)*2*np.pi/24:
 m=cut.copy();m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));cutters.append(m)
part=trimesh.boolean.difference([blank,*cutters],engine='manifold')
assert part.is_watertight and part.is_winding_consistent and len(part.split())==1
inter=trimesh.boolean.intersection([part,w],engine='manifold');v=float(inter.volume) if len(inter.faces) else 0
assert v<1e-5
printing=part.copy();printing.apply_translation([0,0,3]);printing.export(out/'inner-groove-spool-concept.stl')
checks=[dict(axis_distance_mm=c,static_intersection_mm3=v)]
canonical={'part':part,'worm':w}
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
D={}
for name,m in canonical.items():
 order=np.lexsort((np.arctan2(m.vertices[:,1],m.vertices[:,0]),np.round(m.vertices[:,2],6)));inv=np.empty_like(order);inv[order]=np.arange(len(order));verts=m.vertices[order];faces=inv[m.faces];faces=np.take_along_axis(faces,(np.arange(3)[None,:]+faces.argmin(axis=1)[:,None])%3,axis=1);faces=faces[np.lexsort((faces[:,2],faces[:,1],faces[:,0]))]
 D[name]={'v':pack(verts),'f':pack(faces,True)}
fragment=(out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(D))
old=(out.parent/'hex-spools-r7-v1/assembly-preview.html').read_text();head=old[:old.index('<div id=')];(out/'assembly-preview.html').write_text(head+fragment+'</html>')
(out/'dimensions.json').write_text(json.dumps(dict(worm_diameter_mm=6,worm_length_mm=6,spool_inner_gap_mm=4,worm_axis_z_mm=4,axis_distance_mm=float(c),static_intersection_mm3=v,compatibility='Inner-face grooves copied from worm at 24 angular positions. Static placement only; conjugacy and continuous simultaneous engagement unverified.',tested_clearances=checks),indent=2))
print('Chosen centre distance',c,'static overlap',v)
