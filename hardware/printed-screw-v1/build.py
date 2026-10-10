from pathlib import Path
import numpy as np,trimesh,json,base64,gzip
out=Path(__file__).resolve().parent
# Custom coarse thread, not an ISO M4 thread. Z axis, 1.2 mm single-start lead.
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
def cyl(r,h,z,sections=160):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=sections);m.apply_translation([0,0,z]);return m
shaft=thread(6.6);shaft.apply_translation([0,0,1.4])
head=cyl(3.5,2,1,6)
screw=trimesh.boolean.union([head,shaft],engine='manifold')
# Female test piece: 8mm OD, 5mm thickness; radial clearance .2, flank relief .08.
cut=thread(8.4,.2,.08);cut.apply_translation([0,0,-1.2])
nut=trimesh.boolean.difference([cyl(4,5,2.5),cut],engine='manifold')
for name,m in [('screw',screw),('thread-test',nut)]:
 assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
 m.export(out/(name+'.stl'))
# Validate aligned thread engagement over a sample of screw rotation/advance.
for angle in np.linspace(0,2*np.pi,9):
 male=shaft.copy();male.apply_translation([0,0,-1.4]);male.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));male.apply_translation([0,0,1.2*angle/(2*np.pi)])
 inter=trimesh.boolean.intersection([male,nut],engine='manifold');assert not len(inter.faces) or abs(inter.volume)<1e-5
canonical={'screw':screw,'nut':nut}
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
for m in canonical.values():
 order=np.lexsort((np.arctan2(m.vertices[:,1],m.vertices[:,0]),np.round(m.vertices[:,2],6)));inv=np.empty_like(order);inv[order]=np.arange(len(order));v=m.vertices[order].copy();f=inv[m.faces];f=np.take_along_axis(f,(np.arange(3)[None,:]+f.argmin(axis=1)[:,None])%3,axis=1);f=f[np.lexsort((f[:,2],f[:,1],f[:,0]))];m.vertices=v;m.faces=f
D={name:{'v':pack(m.vertices),'f':pack(m.faces,True)} for name,m in canonical.items()}
target=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/printed-screw-v1.html');target.write_text((out/'viewer-template.html').read_text().replace('__DATA__',json.dumps(D)))
print('validated',target.stat().st_size)
(out/'dimensions.json').write_text(json.dumps(dict(thread_major_diameter_mm=4,thread_root_diameter_mm=3,pitch_mm=1.2,thread_length_above_head_mm=6,head_corner_diameter_mm=7,head_height_mm=2,test_piece_od_mm=8,test_piece_height_mm=5,radial_clearance_mm=.2,standard='custom, not ISO M4'),indent=2))
