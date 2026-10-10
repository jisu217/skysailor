from pathlib import Path
import trimesh,numpy as np,json,zipfile
out=Path(__file__).resolve().parent
src=out.parent/'generated-worm-pair-v1'
def box(size,pos):
 m=trimesh.creation.box(size);m.apply_translation(pos);return m
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
part=trimesh.load(src/'print-clearance-assembly.stl')
lower=trimesh.boolean.intersection([part,box([40,40,20],[0,0,-5])],engine='manifold')
upper=trimesh.boolean.intersection([part,box([40,40,20],[0,0,15])],engine='manifold')
# Unique D orientation around the unchanged 3.4mm axle bore.
male=trimesh.boolean.intersection([cyl(2.4,.95,5.425),box([20,20,4],[-7.85,0,5.5])],engine='manifold')
male=trimesh.boolean.difference([male,cyl(1.7,3,5.5)],engine='manifold')
lower=trimesh.boolean.union([lower,male],engine='manifold')
female=trimesh.boolean.intersection([cyl(2.5,1.1,5.5),box([20,20,4],[-7.75,0,5.5])],engine='manifold')
upper=trimesh.boolean.difference([upper,female],engine='manifold')
for name,m in [('lower',lower),('upper',upper)]:
 assert m.is_watertight and len(m.split())==1
 m.export(out/(name+'-assembled.stl'))
 q=m.copy()
 if name=='upper':q.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 q.apply_translation([0,0,-q.bounds[0,2]]);q.export(out/(name+'-print.stl'))
inter=trimesh.boolean.intersection([lower,upper],engine='manifold');assert not len(inter.faces) or abs(inter.volume)<1e-6
# Cutting the joint must leave every external tooth and its phase unchanged.
outer=trimesh.boolean.union([lower,upper],engine='manifold')
extra=trimesh.boolean.difference([outer,part],engine='manifold');assert not len(extra.faces) or abs(extra.volume)<1e-6
(out/'parameters.json').write_text(json.dumps({'split_z_mm':5.0,'male_radius_mm':2.4,'flat_x_mm':2.15,'engagement_mm':0.9,'socket_radial_clearance_mm':0.1,'socket_depth_clearance_mm':0.15,'axle_bore_mm':3.4,'male_flat_wall_mm':0.45,'retention':'adhesive on internal D joint; full winding core belongs to lower part','checks':['two closed single-body meshes','no joint overlap','no added external material; original tooth phases preserved']},indent=2))
core=trimesh.boolean.intersection([part,box([40,40,2.998],[0,0,3.5])],engine='manifold')
missing=trimesh.boolean.difference([core,lower],engine='manifold');assert not len(missing.faces) or abs(missing.volume)<1e-6
# Existing full-resolution viewer and worm layout.
ns={'__file__':str(src/'viewer.py')}
exec((src/'viewer.py').read_text().split('assert len(low.split())')[0],ns)
ns['canonical'].pop('part');ns['canonical']['lower-part']=lower;ns['canonical']['upper-part']=upper
ns['out']=out
s=(src/'viewer-template.html').read_text().replace('generated-worm-pair','spool-full-core-glue')
s=s.replace('운동으로 생성한 웜 치형 · 시험 설계','원통 일체형 스풀 · 위 기어 접착 결합').replace('24:1 동시 생성 · 축 간격 8.5 mm · 출력 여유 0.08 mm','축 구멍 Ø3.4 · 결합 길이 0.9mm · 옆면 여유 0.1mm')
s=s.replace(' <div class="text-small" data-status>',' <label><input type="checkbox" data-explode> 위 조각 벌려보기</label>\n <div class="text-small" data-status>')
s=s.replace('meshes.part.rotation.z=-degrees*Math.PI/180/24;',"meshes['lower-part'].rotation.z=-degrees*Math.PI/180/24;meshes['upper-part'].rotation.z=-degrees*Math.PI/180/24;")
s=s.replace(' const ambient='," root.querySelector('[data-explode]').onchange=e=>{meshes['upper-part'].position.z=e.target.checked?10:0;meshes['upper-support'].position.z=e.target.checked?10:0;render();};\n const ambient=")
(out/'viewer-template.html').write_text(s)
exec((src/'viewer.py').read_text().split('def pack(a,delta=False):')[1].join(['def pack(a,delta=False):','']),ns)
