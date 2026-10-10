from pathlib import Path
import numpy as np,trimesh,json,base64,gzip
out=Path(__file__).resolve().parent
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
part=trimesh.load(out/'print-clearance-assembly.stl')
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
# Keep motor end bore 1.2mm; solid distal journal and thrust shoulder.
worm=trimesh.boolean.union([worm,cyl(2,.3,6.05),cyl(1.5,5.1,8.55)],engine='manifold')
assert worm.is_watertight and len(worm.split())==1
worm.export(out/'worm-with-journal.stl')
c=8.5
w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,-c],[0,1,0,3.5],[0,0,0,1]]))
# Independent bearing blocks shown as layout parts, not yet attached to a chassis.
bearing=trimesh.creation.box([1.4,6,7]);bearing.apply_translation([7.2,-c,3.5])
hole=cyl(1.7,4,0);hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));hole.apply_translation([7.2,-c,3.5])
bearing=trimesh.boolean.difference([bearing,hole],engine='manifold')
low=trimesh.creation.annulus(r_min=1.7,r_max=3.5,height=1,sections=192);low.apply_translation([0,0,-1.1])
high=low.copy();high.apply_translation([0,0,9.2])
# Fixed pillar joins the lower bearing and locates in a blind upper socket.
axle=cyl(1.5,9.8,3.3)
low=trimesh.boolean.union([low,axle,cyl(3.5,.3,-1.45)],engine='manifold')
upper_blank=cyl(3.5,1,8.1)
high=trimesh.boolean.difference([upper_blank,cyl(1.7,.8,7.9)],engine='manifold')
motor=cyl(3,15,0);motor.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));motor.apply_translation([-11.5,-c,3.5])
canonical={'part':part,'worm':w,'bearing':bearing,'lower-support':low,'upper-support':high,'motor':motor}
assert len(low.split())==1 and low.is_watertight
for name,m in [('worm-bearing',bearing),('lower-bearing',low),('upper-bearing',high)]:
 for rotating in [part,w]:
  inter=trimesh.boolean.intersection([rotating,m],engine='manifold');assert not len(inter.faces) or abs(inter.volume)<1e-6
 for_export=m.copy();for_export.apply_translation(-for_export.bounds[0]);for_export.export(out/(name+'.stl'))

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

print('Viewer created')
