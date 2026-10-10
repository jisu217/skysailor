from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;root=out.parent
# Use the archived pre-pillar frame and restore its two diagonal arches.
base=trimesh.load(root/'ring-380-cross-t-webs-low/ring-380-cross-t-webs-low.stl',force='mesh')
# Take complete arches above the floor from the existing pillar-free model.
old=trimesh.load(root/'ring-380-center-ring-54-no-pillar/ring-380-center-ring-54-no-pillar.stl',force='mesh')
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
arches=trimesh.boolean.intersection([old,box([400,400,120],[0,0,62])],engine='manifold')
# This crop starts z=2, including a central ring wall; remove that old center region.
c=trimesh.creation.cylinder(radius=28,height=5,sections=256);c.apply_translation([0,0,2.5])
arches=trimesh.boolean.difference([arches,c],engine='manifold')
base=trimesh.boolean.union([base,arches],engine='manifold')
z=base.vertices[:,2].copy();base.vertices[:,2]=np.where(z<=2,z/2,z-1)
# Clear cross walls in the 11 mm central area above the 1 mm floor.
clear=trimesh.creation.cylinder(radius=5.5,height=3.1,sections=256);clear.apply_translation([0,0,2.55])
base=trimesh.boolean.difference([base,clear],engine='manifold')
floor=trimesh.creation.annulus(r_min=2.5,r_max=5.5,height=1,sections=256);floor.apply_translation([0,0,.5])
wall=trimesh.creation.annulus(r_min=4.5,r_max=5.5,height=2.05,sections=256);wall.apply_translation([0,0,1.975])
m=trimesh.boolean.union([base,floor,wall],engine='manifold')
hole=trimesh.creation.cylinder(radius=2.5,height=5,sections=256);hole.apply_translation([0,0,1])
m=trimesh.boolean.difference([m,hole],engine='manifold')
m.merge_vertices(digits_vertex=5);m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices();m.fill_holes()
assert m.is_watertight and m.is_volume and len(m.split())==1
m.export(out/'frame-seat-11-hole-5.stl')
s=(root/'ring-380-eight-ribs-pillar/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>중앙 원형 받침 Ø11 · 구멍 Ø5</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>바닥 1mm · 둘레 벽 두께 1mm / 높이 2mm · 중앙 기둥 및 받침 안 십자벽 제거</small><div style="margin-top:16px"><button id="closeup">받침대 확대</button></div>',s)
s=s.replace('ring-380-eight-ribs-pillar.stl','frame-seat-11-hole-5.stl')
s=s.replace("update();document.querySelector('#status')","document.querySelector('#closeup').onclick=()=>{target.set(0,0,1);d=50;az=-1.1;el=.9;update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(20,Math.min')
(out/'preview.html').write_text(s)
print('One watertight frame; central pillar removed; OD11/ID5 seat, 1mm floor, 1mm wall, 2mm wall height.')
