from pathlib import Path
import trimesh,numpy as np,json,base64,gzip
out=Path(__file__).resolve().parent
part=trimesh.load(out.parent/'trapezoid-helical-spool-v1/helical-spool.stl');part.apply_translation([0,0,-3])
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
checks=[]
# A placement study only; these independently designed teeth are not a conjugate pair.
for c in np.arange(9.0,10.81,.05):
 w=worm.copy();w.apply_transform(np.array([[0,0,1,-3],[1,0,0,-c],[0,1,0,3.5],[0,0,0,1]]))
 inter=trimesh.boolean.intersection([part,w],engine='manifold');v=float(inter.volume) if len(inter.faces) else 0
 checks.append([float(c),v])
 if v<1e-6:break
assert v<1e-6
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
(out/'dimensions.json').write_text(json.dumps(dict(worm_diameter_mm=6,worm_length_mm=6,worm_axis_z_mm=3.5,axis_distance_mm=float(c),static_intersection_mm3=v,compatibility='Placement only. Helical gear and existing worm are not a validated conjugate pair; no simultaneous-drive claim.',tested_clearances=checks),indent=2))
print('Chosen centre distance',c,'static overlap',v)
