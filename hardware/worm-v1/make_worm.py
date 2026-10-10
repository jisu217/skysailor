from pathlib import Path
import json
import numpy as np
import trimesh
OUT=Path(__file__).resolve().parent
# Custom printable axial trapezoidal worm; not an off-the-shelf gear standard.
P=dict(bore_diameter_mm=1.2,root_diameter_mm=5.0,tip_diameter_mm=8.0,
       lead_mm=4.0,starts=1,hand='right',axial_flank_angle_deg=45,
       axial_crest_width_mm=0.5,thread_start_mm=3.0,thread_end_mm=15.0,
       overall_length_mm=18.0,plain_end_diameter_mm=5.0)
n=192
zs=np.linspace(0,18,361)
theta=np.arange(n)*2*np.pi/n
verts=[]
for z in zs:
    phase=(z-3-4*theta/(2*np.pi)+2)%4-2
    tooth=np.clip((1.75-np.abs(phase))/1.5,0,1)
    ramp=np.clip(min((z-3)/1.5,(15-z)/1.5),0,1)
    r=2.5+1.5*tooth*ramp
    verts.extend(np.column_stack((r*np.cos(theta),r*np.sin(theta),np.full(n,z))))
outer_count=len(verts)
for z in [0,18]:
    verts.extend(np.column_stack(((P["bore_diameter_mm"]/2)*np.cos(theta),(P["bore_diameter_mm"]/2)*np.sin(theta),np.full(n,z))))
faces=[]
for k in range(len(zs)-1):
    for i in range(n):
        j=(i+1)%n;a=k*n+i;b=k*n+j;c=(k+1)*n+j;d=(k+1)*n+i
        faces.extend([[a,b,c],[a,c,d]])
for i in range(n):
    j=(i+1)%n; ib=outer_count+i;jb=outer_count+j;it=ib+n;jt=jb+n
    faces.extend([[ib,it,jt],[ib,jt,jb]])
    faces.extend([[i,ib,jb],[i,jb,j]])
    a=(len(zs)-1)*n+i;b=(len(zs)-1)*n+j
    faces.extend([[a,b,jt],[a,jt,it]])
m=trimesh.Trimesh(vertices=verts,faces=faces,process=True)
assert m.is_watertight and m.is_winding_consistent and m.volume>0
assert len(m.split())==1
for z in [0.1,2,5,9,14,17.9]:
    loops=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1]).discrete
    assert any(np.max(np.abs(np.linalg.norm(p[:,:2],axis=1)-P["bore_diameter_mm"]/2))<.0001 for p in loops)
m.export(OUT/'worm-v1-bore-1.20mm.stl')
P.update(watertight=bool(m.is_watertight),volume_mm3=float(m.volume),bounds_mm=m.bounds.tolist(),stage='Print and stationary fit trial; wheel, supports and powered load testing pending')
(OUT/'dimensions.json').write_text(json.dumps(P,indent=2)+'\n')
np.savez_compressed(OUT/'preview-mesh.npz',vertices=m.vertices,faces=m.faces)
print(json.dumps(P,indent=2))
