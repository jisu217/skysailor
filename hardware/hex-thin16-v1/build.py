from pathlib import Path
import numpy as np,trimesh,json,base64,gzip,itertools
out=Path(__file__).resolve().parent
src=out.parent/'generated-worm-pair-v1'
ns={'__file__':str(src/'viewer.py')}
exec((src/'viewer.py').read_text().split('assert len(low.split())')[0],ns)
base={k:v.copy() for k,v in ns['canonical'].items() if k!='upper-support'}
base['part']=trimesh.load(out.parent/'generated-thin16-v1/print-clearance-assembly.stl')
SCALE=1+.5/7.9119722843
base['worm']=trimesh.load(out.parent/'generated-thin16-v1/worm-with-journal.stl')
base['worm'].apply_transform(np.array([[0,0,1,-3*SCALE],[1,0,0,-9],[0,1,0,2.6],[0,0,0,1]]))
base['motor'].apply_translation([-3*(SCALE-1),-.5,-.9])
base['bearing'].apply_translation([7.2*(SCALE-1),-.5,-.9])
def box(size,pos):
 m=trimesh.creation.box(size);m.apply_translation(pos);return m
def cyl(r,h,pos,n=96):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=n);m.apply_translation(pos);return m
def place(m,i,R):
 m=m.copy();m.apply_translation([0,0,-1.2]);m.apply_transform(trimesh.transformations.rotation_matrix(5*np.pi/6,[0,0,1]));m.apply_translation([0,-R,0]);m.apply_transform(trimesh.transformations.rotation_matrix(i*2*np.pi/3,[0,0,1]));return m
def overlap(a,b):
 if np.any(a.bounds[1]<=b.bounds[0]+1e-7) or np.any(b.bounds[1]<=a.bounds[0]+1e-7):return 0.
 q=trimesh.boolean.intersection([a,b],engine='manifold');return abs(q.volume) if len(q.faces) else 0.
base['bearing']=trimesh.boolean.intersection([base['bearing'],box([80,80,40],[0,0,-15.2])],engine='manifold')
base['lower-support']=cyl(1.5,7.5,[0,0,3.35]) # Bare fixed axle, no lower pedestal ring
R=15
units=[{k:place(v,i,R) for k,v in base.items()} for i in range(3)]
# Hex plates encompass all component projections with >=2mm edge margin.
pts=np.vstack([m.vertices[:,:2] for u in units for m in u.values()])
pts=np.vstack([pts]+[place(box([8,8,5.1],[-11.5-3*(SCALE-1),-9,.95]),i,R).vertices[:,:2] for i in range(3)])
# Convex hull retains exact footprint; no mesh triangle reduction.
from scipy.spatial import ConvexHull
hull_pts=pts[ConvexHull(pts).vertices]
def needed_radius(degrees):
 normals=np.array([[np.cos(a),np.sin(a)] for a in np.arange(6)*np.pi/3+np.pi/6+np.deg2rad(degrees)])
 return float((np.max(hull_pts@normals.T)+2)/np.cos(np.pi/6))
angles=np.arange(0,60,.1)
angle_deg=float(min(angles,key=needed_radius))
rad=float(np.ceil(needed_radius(angle_deg)*10)/10)
normals=np.array([[np.cos(a),np.sin(a)] for a in np.arange(6)*np.pi/3+np.pi/6+np.deg2rad(angle_deg)])
assert rad*np.cos(np.pi/6)-np.max(pts@normals.T)>=2-1e-6
bottom=cyl(rad,2,[0,0,-1.6],6);top=cyl(rad,2,[0,0,4.6],6)
for plate in [bottom,top]:plate.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(angle_deg),[0,0,1]))
print({'gear_tip_radius_mm':8.4119722843,'worm_lead_mm':1.875*SCALE,'gear_worm_axis_distance_mm':9,'upper_motor_saddle_length_mm':0,'motor_bore_diameter_mm':6.1,'plate_rotation_deg':angle_deg,'corner_diameter_mm':rad*2},flush=True)
# 0.4mm-deep recesses in plates only; retain separate integrated thrust lands.
pocket_radius=8.4119722843+.4
bottom=trimesh.boolean.difference([bottom]+[place(cyl(pocket_radius,.9,[0,0,.25]),i,R) for i in range(3)],engine='manifold')
top=trimesh.boolean.difference([top]+[place(cyl(pocket_radius,.9,[0,0,5.15]),i,R) for i in range(3)],engine='manifold')
lo=[bottom];hi=[top];columns=[]
for i,u in enumerate(units):
 lo.extend([u['lower-support'],u['bearing']])
 lo.append(place(trimesh.creation.annulus(r_min=1.7,r_max=2.5,height=.2,sections=192),i,R))
 lo[-1].apply_translation([0,0,-.1])
 hi.append(place(trimesh.creation.annulus(r_min=1.7,r_max=2.5,height=.2,sections=192),i,R))
 hi[-1].apply_translation([0,0,5.5])
 # Extend the existing 1.4 x 6mm worm bearing wall to the top plate.
 # Bearing wall now ends at lowered upper plate.
 # Rectangular locating tongue, seated in a blind pocket in the upper plate.
 lo.append(place(box([1.4,4,2.3],[7.2*SCALE,-9,5.95]),i,R))
 hi[0]=trimesh.boolean.difference([hi[0],place(box([1.8,4.4,4],[7.2*SCALE,-9,5.8]),i,R)],engine='manifold')
 # Motor cylinder grooves cut directly into each plate, no saddle blocks.
 hole=trimesh.creation.cylinder(radius=3.05,height=17,sections=192);hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));hole.apply_translation([-11.5-3*(SCALE-1),-9,2.6])
 lo[0]=trimesh.boolean.difference([lo[0],place(hole,i,R)],engine='manifold')
 hi[0]=trimesh.boolean.difference([hi[0],place(hole,i,R)],engine='manifold')
 # Swept clearance for rotating worm teeth entering the plate plane.
 worm_relief=trimesh.creation.cylinder(radius=3.15,height=6*SCALE+.4,sections=192);worm_relief.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));worm_relief.apply_translation([0,-9,2.6])
 lo[0]=trimesh.boolean.difference([lo[0],place(worm_relief,i,R)],engine='manifold')
 hi[0]=trimesh.boolean.difference([hi[0],place(worm_relief,i,R)],engine='manifold')

# Central 3mm pillar spans the plate gap; locating peg enters a blind top socket.
lo.extend([cyl(1.5,4.2,[0,0,1.5]),cyl(1.0,2.3,[0,0,4.75])])
hi[0]=trimesh.boolean.difference([hi[0],cyl(1.2,4,[0,0,4.6])],engine='manifold')
bottom=trimesh.boolean.union(lo,engine='manifold');top=trimesh.boolean.union(hi,engine='manifold')
top=trimesh.boolean.difference([top]+[place(cyl(1.7,5,[0,0,5.7]),i,R) for i in range(3)],engine='manifold')
joint_inter=trimesh.boolean.intersection([bottom,top],engine='manifold')
print('frame intersection',joint_inter.volume,joint_inter.bounds,flush=True)
assert overlap(bottom,top)<1e-5 # Coincident housing faces: float32 Boolean tolerance
checks=['housing seam overlap below 1e-5 mm3 float32 tolerance; upper sockets through']
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
 w=base['worm'].copy();w.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(deg),[1,0,0],[0,-9,2.6]));w=place(w,0,R)
 for m in [p,w]:
  for housing in [bottom,top]:assert overlap(m,housing)<1e-6
checks.append('12 sampled rotation poses clear housing; 120-degree symmetry')
for name,m in [('lower-frame',bottom),('upper-frame',top)]:
 assert m.is_watertight and len(m.split())==1,(name,len(m.split()))
 q=m.copy();q.apply_translation([0,0,-q.bounds[0,2]]);q.export(out/(name+'.stl'))
 check=trimesh.load(out/(name+'.stl'));check.process(validate=True);assert check.is_watertight and len(check.split())==1;check.export(out/(name+'.stl'))
D={}
def pack(a,delta=False):
 raw=np.asarray(a,dtype='<i4' if delta else '<f4').ravel()
 if delta:raw=np.diff(raw,prepend=np.int32(0)).astype('<i4')
 return base64.b64encode(gzip.compress(raw.view('u1').reshape(-1,4).T.tobytes())).decode()
meshes={'bottom':bottom,'top':top}
for i,u in enumerate(units):
 for k in ['part','worm','motor']:meshes[f'{k}-{i}']=u[k]
for name,m in meshes.items():D[name]={'v':pack(m.vertices),'f':pack(m.faces,True)}
s=(src/'viewer-template.html').read_text().replace('generated-worm-pair','hex-thin16')
s=s.replace('운동으로 생성한 웜 치형 · 시험 설계','기어 1.6mm · 양쪽 접촉 링 0.2mm').replace('24:1 동시 생성 · 축 간격 8.5 mm · 출력 여유 0.08 mm',f'120° 배치 · 꼭짓점 간 {rad*2:.1f} mm · 판 두께 2 mm')
a=s.index(' <label class="form-label">');b=s.index(' <div class="text-small" data-status>',a)
s=s[:a]+' <label><input data-hide-top type="checkbox"> 위판 숨기기</label>\n'+s[b:]
a=s.index(' meshes.worm.geometry.translate');b=s.index(' const ambient=',a)
s=s[:a]+" root.querySelector('[data-hide-top]').onchange=e=>{meshes.top.visible=!e.target.checked;render();};\n"+s[b:]
s=s.replace('distance=75','distance=135').replace('Math.min(90','Math.min(220').replace("name==='base'","name==='bottom'").replace("name==='worm'","name.startsWith('worm')")
s=s.replace('__DATA__',json.dumps(D))
old=(src/'assembly-preview.html').read_text();head=old[:old.index('<div id=')];(out/'assembly-preview.html').write_text(head+s+'</html>')
(out/'checks.json').write_text(json.dumps({'gear_tip_radius_mm':8.4119722843,'worm_lead_mm':1.875*SCALE,'gear_worm_axis_distance_mm':9,'upper_motor_saddle_length_mm':0,'motor_bore_diameter_mm':6.1,'plate_rotation_deg':angle_deg,'angle_search_step_deg':0.1,'hex_corner_diameter_mm':rad*2,'hex_across_flats_mm':rad*np.sqrt(3),'spool_center_radius_mm':R,'outer_post_count':0,'center_post_diameter_mm':3,'center_peg_diameter_mm':2,'edge_margin_min_mm':float(rad*np.cos(np.pi/6)-np.max(pts@normals.T)),'plate_thickness_mm':2,'worm_support_tongue_mm':[1.4,4,2.3],'worm_support_through_slot_mm':[1.8,4.4],'plate_inside_gap_mm':4.2,'gear_thickness_mm':1.6,'gear_pocket_depth_mm':0.8,'gear_pocket_diameter_mm':2*pocket_radius,'plate_floor_mm':1.2,'overall_height_mm':8.2,'including_pegs_height_mm':8.5,'drive_drop_mm':1.2,'lower_spool_contact_z_mm':-1.2,'motor_bottom_to_plate_mm':-1.0,'lower_motor_groove_depth_mm':1.05,'upper_motor_groove_depth_mm':0.85,'upper_ring_outer_diameter_mm':5,'upper_ring_height_mm':0.2,'lower_ring_height_mm':0.2,'spool_axial_clearance_top_mm':0.2,'axle_socket_diameter_mm':3.4,'checks':checks},indent=2))
print((out/'checks.json').read_text())

import runpy
runpy.run_path(str(out.parent/'revision-workbench-v1/fullscreen.py'))['apply'](out/'assembly-preview.html')
