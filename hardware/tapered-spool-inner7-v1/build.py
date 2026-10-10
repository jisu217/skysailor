from pathlib import Path
import numpy as np,trimesh,json,base64,gzip
out=Path(__file__).resolve().parent
N=24;tip=15.823944568634033/2;module=2*tip/(N+2);pitch=N*module/2;root=pitch-1.25*module;alpha=np.deg2rad(20);rb=pitch*np.cos(alpha);beta=np.deg2rad(20)
def inv(a):return np.tan(a)-a
def half(r):return np.pi/(2*N)+inv(alpha)-inv(np.arccos(rb/r))
outline=[]
for i in range(N):
 c=i*2*np.pi/N;hb=half(rb);ht=half(tip)
 points=[(-np.pi/N,root),(-hb,root)]
 points +=[(-half(r),r) for r in np.linspace(rb,tip,20)]
 points +=[(a,tip) for a in np.linspace(-ht,ht,8)[1:]]
 points +=[(half(r),r) for r in np.linspace(tip,rb,20)[1:]]
 points +=[(hb,root)]
 outline.extend([(c+a,r) for a,r in points])
outline=np.asarray(outline);L=len(outline)
def band(z0,z1):
 zs=np.linspace(z0,z1,41);v=[]
 for z in zs:
  t=outline[:,0]+z*np.tan(beta)/pitch;scale=1-(1-7/tip)*((z-z0)/(z1-z0) if z0==0 else (z1-z)/(z1-z0));r=outline[:,1]*scale;v.extend(np.column_stack([r*np.cos(t),r*np.sin(t),np.full(L,z)]))
 f=[]
 for k in range(len(zs)-1):
  for i in range(L):
   j=(i+1)%L;a=k*L+i;b=k*L+j;c=(k+1)*L+j;d=(k+1)*L+i;f.extend([[a,b,c],[a,c,d]])
 bot=len(v);v.extend([[0,0,z0],[0,0,z1]])
 for i in range(L):
  j=(i+1)%L;f.extend([[bot,j,i],[bot+1,(len(zs)-1)*L+i,(len(zs)-1)*L+j]])
 m=trimesh.Trimesh(v,f,process=True);assert m.is_watertight;return m
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
# No guide flanges: the central barrel directly joins both gear bands.
part=trimesh.boolean.union([band(0,2),band(5,7),cyl(3,3.2,3.5),cyl(1.5,3.2,-1.4),cyl(1.5,3.2,8.4)],engine='manifold')
assert part.is_watertight and part.is_winding_consistent and len(part.split())==1
printing=part.copy();printing.apply_translation([0,0,3]);printing.export(out/'helical-spool.stl')
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
(out/'dimensions.json').write_text(json.dumps(dict(outer_face_radius_mm=float(tip),inner_face_radius_mm=7,gear_thickness_mm=2,spool_gap_mm=3,worm_diameter_mm=6,worm_length_mm=6,worm_axis_z_mm=3.5,axis_distance_mm=float(c),static_intersection_mm3=v,compatibility='Placement only. Helical gear and existing worm are not a validated conjugate pair; no simultaneous-drive claim.',tested_clearances=checks),indent=2))
print('Chosen centre distance',c,'static overlap',v)
