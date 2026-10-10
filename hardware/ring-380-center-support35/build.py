from pathlib import Path
import trimesh,json,re
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-center-seat-11'
def cylinder(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=256);m.apply_translation([0,0,z]);return m
base=trimesh.load(src/'frame-seat-11-hole-5.stl',force='mesh')
base=trimesh.boolean.difference([base,cylinder(17.5,22,0)],engine='manifold')
lip=trimesh.creation.annulus(r_min=14.5,r_max=17.5,height=1,sections=256);lip.apply_translation([0,0,.5])
wall=trimesh.creation.annulus(r_min=16.5,r_max=17.5,height=2.2,sections=256);wall.apply_translation([0,0,1.9])
base=trimesh.boolean.union([base,lip,wall],engine='manifold')
assert base.is_volume and base.is_watertight and len(base.split())==1
base.export(out/'frame-support35-lip2.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':base.vertices.tolist(),'faces':base.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>중앙 원통 지지대 Ø35 · 안쪽 받침 링 2mm</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>원통 외경35 / 내경33 / 벽 두께1 / 바닥 위 높이2mm · 바닥 받침 링 돌출2 / 통과 구멍 Ø29 / 링 두께1mm · 실·구·아래 막대·아래판 제거</small>',s)
s=s.replace('frame-seat-11-hole-5.stl','frame-support35-lip2.stl')
(out/'preview.html').write_text(s)
(out/'specs.json').write_text(json.dumps({'outer_diameter':35,'wall_inner_diameter':33,'wall_thickness':1,'wall_height_above_floor':2,'lip_inward_projection':2,'lip_hole_diameter':29,'lip_thickness':1,'watertight':True,'components':1},indent=2))
print('Validated connected watertight frame; cylinder OD35 ID33, bottom lip hole29.')
