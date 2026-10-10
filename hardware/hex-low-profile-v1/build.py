from pathlib import Path
import numpy as np,trimesh,json,base64,gzip,itertools
out=Path(__file__).resolve().parent
src=out.parent/'generated-worm-pair-v1'
ns={'__file__':str(src/'viewer.py')}
exec((src/'viewer.py').read_text().split('assert len(low.split())')[0],ns)
base={k:v.copy() for k,v in ns['canonical'].items() if k!='upper-support'}
def box(size,pos):
 m=trimesh.creation.box(size);m.apply_translation(pos);return m
def cyl(r,h,pos,n=96):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=n);m.apply_translation(pos);return m
def place(m,i,R):
 m=m.copy();m.apply_translation([0,0,-1.2]);m.apply_transform(trimesh.transformations.rotation_matrix(5*np.pi/6,[0,0,1]));m.apply_translation([0,-R,0]);m.apply_transform(trimesh.transformations.rotation_matrix(i*2*np.pi/3,[0,0,1]));return m
def overlap(a,b):
 if np.any(a.bounds[1]<=b.bounds[0]+1e-7) or np.any(b.bounds[1]<=a.bounds[0]+1e-7):return 0.
 q=trimesh.boolean.intersection([a,b],engine='manifold');return abs(q.volume) if len(q.faces) else 0.
base['lower-support']=cyl(1.5,8.6,[0,0,3.9]) # Bare fixed axle, no lower pedestal ring
R=15
units=[{k:place(v,i,R) for k,v in base.items()} for i in range(3)]
# Hex plates encompass all component projections with >=2mm edge margin.
pts=np.vstack([m.vertices[:,:2] for u in units for m in u.values()])
normals=np.array([[np.cos(a),np.sin(a)] for a in np.arange(6)*np.pi/3+np.pi/6])
pts=np.vstack([pts]+[place(box([8,8,5.1],[-11.5,-8.5,.95]),i,R).vertices[:,:2] for i in range(3)])
rad=float(np.ceil((np.max(pts@normals.T)+2)/np.cos(np.pi/6)))
assert np.max(pts@normals.T) < rad*np.cos(np.pi/6)
bottom=cyl(rad,2,[0,0,-2.6],6);top=cyl(rad,2,[0,0,7.6],6)
lo=[bottom];hi=[top];columns=[]
for i,u in enumerate(units):
 lo.extend([u['lower-support'],u['bearing'],place(box([1.4,6,1.6],[7.2,-8.5,-.8]),i,R)])
 hi.append(place(cyl(2.5,.2,[0,0,7.7]),i,R))
 # Extend the existing 1.4 x 6mm worm bearing wall to the top plate.
 lo.append(place(box([1.4,6,.8],[7.2,-8.5,7.4]),i,R))
 # Rectangular locating tongue, seated in a blind pocket in the upper plate.
 lo.append(place(box([1.4,4,1],[7.2,-8.5,8.3]),i,R))
 hi[0]=trimesh.boolean.difference([hi[0],place(box([1.8,4.4,1.3],[7.2,-8.5,8.35]),i,R)],engine='manifold')
 # Open motor saddle; add a tie/adhesive for prototype retention.
 saddle=box([8,8,5.1],[-11.5,-8.5,.95])
 hole=ns['motor'].copy();hole.apply_scale([1.1,1.05,1.05]);hole.apply_translation([1.15,.425,-.175])
 saddle=trimesh.boolean.difference([saddle,hole],engine='manifold')
 lo.append(place(saddle,i,R))
# Central 3mm pillar spans the plate gap; locating peg enters a blind top socket.
lo.extend([cyl(1.5,8.2,[0,0,2.5]),cyl(1.0,1.0,[0,0,7.1])])
hi[0]=trimesh.boolean.difference([hi[0],cyl(1.2,1.3,[0,0,7.15])],engine='manifold')
bottom=trimesh.boolean.union(lo,engine='manifold');top=trimesh.boolean.union(hi,engine='manifold')
top=trimesh.boolean.difference([top]+[place(cyl(1.7,.8,[0,0,7.9]),i,R) for i in range(3)],engine='manifold')
assert overlap(bottom,top)<1e-6
checks=['upper and lower frames do not overlap; axle blind sockets retained']
for i,j in itertools.combinations(range(3),2):
 for ka,a in units[i].items():
  for kb,b in units[j].items():
   v=overlap(a,b);assert v<1e-6,(i,j,ka,kb,v)
checks.append('all cross-unit solid intersections zero')
for i,u in enumerate(units):
 for k in ['part','worm','motor']:
  for name,m in [('bottom',bottom),('top',top)]:
   v=overlap(u[k],m);assert v<1e-6,(i,k,name,v)
checks.append('rotors and motor housings clear both plates and integrated supports at initial pose')
# Sample prescribed rotation against housing for one unit; symmetry covers others.
for deg in np.arange(0,360,30):
 p=base['part'].copy();p.apply_transform(trimesh.transformations.rotation_matrix(-np.deg2rad(deg)/24,[0,0,1]));p=place(p,0,R)
 w=base['worm'].copy();w.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(deg),[1,0,0],[0,-8.5,3.5]));w=place(w,0,R)
 for m in [p,w]:
  for housing in [bottom,top]:assert overlap(m,housing)<1e-6
checks.append('12 sampled rotation poses clear housing; 120-degree symmetry')
for name,m in [('lower-frame',bottom),('upper-frame',top)]:
 assert m.is_watertight and len(m.split())==1,(name,len(m.split()))
 q=m.copy();q.apply_translation([0,0,-q.bounds[0,2]]);q.export(out/(name+'.stl'))
D={}
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
meshes={'bottom':bottom,'top':top}
for i,u in enumerate(units):
 for k in ['part','worm','motor']:meshes[f'{k}-{i}']=u[k]
for name,m in meshes.items():D[name]={'v':pack(m.vertices),'f':pack(m.faces,True)}
s=(src/'viewer-template.html').read_text().replace('generated-worm-pair','hex-low-profile')
s=s.replace('운동으로 생성한 웜 치형 · 시험 설계','하부 받침 링 제거 · 전체 높이 1.2mm 축소').replace('24:1 동시 생성 · 축 간격 8.5 mm · 출력 여유 0.08 mm',f'120° 배치 · 꼭짓점 간 {rad*2:.0f} mm · 판 두께 2 mm')
a=s.index(' <label class="form-label">');b=s.index(' <div class="text-small" data-status>',a)
s=s[:a]+' <label><input data-hide-top type="checkbox"> 위판 숨기기</label>\n'+s[b:]
a=s.index(' meshes.worm.geometry.translate');b=s.index(' const ambient=',a)
s=s[:a]+" root.querySelector('[data-hide-top]').onchange=e=>{meshes.top.visible=!e.target.checked;render();};\n"+s[b:]
s=s.replace('distance=75','distance=135').replace('Math.min(90','Math.min(220').replace("name==='base'","name==='bottom'").replace("name==='worm'","name.startsWith('worm')")
s=s.replace('__DATA__',json.dumps(D))
old=(src/'assembly-preview.html').read_text();head=old[:old.index('<div id=')];(out/'assembly-preview.html').write_text(head+s+'</html>')
(out/'checks.json').write_text(json.dumps({'hex_corner_diameter_mm':rad*2,'hex_across_flats_mm':rad*np.sqrt(3),'spool_center_radius_mm':R,'outer_post_count':0,'center_post_diameter_mm':3,'center_peg_diameter_mm':2,'edge_margin_min_mm':float(rad*np.cos(np.pi/6)-np.max(pts@normals.T)),'plate_thickness_mm':2,'worm_support_tongue_mm':[1.4,4,1],'worm_support_pocket_mm':[1.8,4.4,1.2],'plate_inside_gap_mm':8.2,'overall_height_mm':12.2,'drive_drop_mm':1.2,'lower_spool_contact_z_mm':-1.6,'motor_bottom_to_plate_mm':0.9,'upper_ring_outer_diameter_mm':5,'upper_ring_height_mm':0.2,'spool_axial_clearance_top_mm':0.2,'axle_socket_diameter_mm':3.4,'checks':checks},indent=2))
print((out/'checks.json').read_text())
