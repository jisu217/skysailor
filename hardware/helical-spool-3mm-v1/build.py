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
  t=outline[:,0]+z*np.tan(beta)/pitch;r=outline[:,1];v.extend(np.column_stack([r*np.cos(t),r*np.sin(t),np.full(L,z)]))
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
order=np.lexsort((np.arctan2(part.vertices[:,1],part.vertices[:,0]),np.round(part.vertices[:,2],6)));invmap=np.empty_like(order);invmap[order]=np.arange(len(order));v=part.vertices[order];f=invmap[part.faces];f=np.take_along_axis(f,(np.arange(3)[None,:]+f.argmin(axis=1)[:,None])%3,axis=1);f=f[np.lexsort((f[:,2],f[:,1],f[:,0]))]
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
fragment=(out/'viewer-template.html').read_text().replace('__DATA__',json.dumps({'part':{'v':pack(v),'f':pack(f,True)}}))
old=(out.parent/'hex-spools-r7-v1/assembly-preview.html').read_text();head=old[:old.index('<div id=')];(out/'assembly-preview.html').write_text(head+fragment+'</html>')
(out/'dimensions.json').write_text(json.dumps(dict(teeth=24,outer_diameter_mm=2*tip,transverse_module_mm=module,transverse_pressure_angle_deg=20,helix_angle_deg=20,gear_bands_z_mm=[[0,2],[5,7]],spool_guide_radius_mm=None,spool_core_radius_mm=3,spool_height_mm=3,body_height_mm=7,total_height_mm=13,triangles=len(part.faces),existing_worm_compatibility='not designed or validated'),indent=2))
print('Watertight full-resolution model:',len(part.faces),'triangles')
