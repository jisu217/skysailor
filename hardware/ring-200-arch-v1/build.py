from pathlib import Path
import math,json,re
import numpy as np
import trimesh
from shapely.geometry import Polygon
out=Path(__file__).resolve().parent
R=130.; outer_half=100.; inner_half=94.; thickness=2.; base_z=2.
co=math.sqrt(R*R-outer_half**2); ci=math.sqrt(R*R-inner_half**2)
def arc(half,c):
 t=np.linspace(-math.asin(half/R),math.asin(half/R),513)
 return np.column_stack((R*np.sin(t),R*np.cos(t)-c))
polygon=np.vstack((arc(outer_half,co),arc(inner_half,ci)[::-1]))
arch=trimesh.creation.extrude_polygon(Polygon(polygon),height=thickness,engine='earcut')
# Local x/y profile becomes world x/z; extrusion along -y.
arch.apply_transform(np.array([[1,0,0,0],[0,0,-1,thickness/2],[0,1,0,base_z],[0,0,0,1]]))
tilt_deg=15.
inset=4*math.tan(math.radians(tilt_deg))
profile=np.array([(94,0),(100,0),(100,2),(97.5,2),(97.5-inset,6),(95.5-inset,6),(95.5,2),(94,2),(94,0)])
base=trimesh.creation.revolve(profile,sections=1024)
assert base.is_watertight and base.is_volume
base.export(out/'ring-inward-15deg.stl')
assembly=trimesh.boolean.union([base,arch],engine='manifold')
for name,m in [('arch',arch),('ring-with-arch',assembly)]:
 assert m.is_watertight and m.is_volume and len(m.split())==1
 m.export(out/(name+'.stl'))
assert abs(assembly.bounds[1,2]-(base_z+R-co))<1e-4
scad=(out.parent/'ring-200-raised-194-v1/model.scad').read_text()
scad=scad.replace('// Dimensions in millimeters. Total height: 6 mm.','// Dimensions in millimeters. Arch stands on the ring top at z=2.')
scad=scad.replace('rotate_extrude() polygon([','wall_tilt=15; // inward angle from vertical, degrees\nwall_inset=wall_h*tan(wall_tilt);\nrotate_extrude() polygon([')
scad=scad.replace('[wall_od/2,base_t+wall_h]','[wall_od/2-wall_inset,base_t+wall_h]').replace('[wall_id/2,base_t+wall_h]','[wall_id/2-wall_inset,base_t+wall_h]')
scad+='''
R=130; outer_half=100; inner_half=94; arch_thickness=2;
co=sqrt(R*R-outer_half*outer_half);
ci=sqrt(R*R-inner_half*inner_half);
ao=asin(outer_half/R); ai=asin(inner_half/R);
outer_arc=[for(i=[0:512]) [R*sin(-ao+2*ao*i/512),R*cos(-ao+2*ao*i/512)-co]];
inner_arc=[for(i=[512:-1:0]) [R*sin(-ai+2*ai*i/512),R*cos(-ai+2*ai*i/512)-ci]];
translate([0,0,base_t]) rotate([90,0,0])
linear_extrude(height=arch_thickness,center=true)
polygon(concat(outer_arc,inner_arc));
'''
(out/'model.scad').write_text(scad)
html=(out.parent/'ring-200-raised-194-v1/preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=html.replace('200mm 링 + 원통','200mm 링 + 아치형 띠')
html=re.sub(r'<small>.*?</small>','<small>원 지름 260mm · 바깥 현 200mm · 안쪽 현 188mm · 앞뒤 두께 2mm · 원통 벽 안쪽 15°</small>',html)
html=re.sub(r'<details>.*?</details>',f'<details><summary>ⓘ</summary><p>반지름 130mm인 두 원호를 같은 현 높이에 배치했습니다. 두 원의 중심 높이는 다릅니다.<br>아치 높이 {R-co:.3f}mm · 꼭대기 띠 폭 {ci-co:.3f}mm.<br>링 윗면 z=2에서 시작 · 전체 높이 {base_z+R-co:.3f}mm.<br>원통 벽은 수직 기준 안쪽 15° 경사. 높이 4mm, 반지름 방향 두께 2mm.<br>윗단 외경 {195-2*inset:.3f}mm / 내경 {191-2*inset:.3f}mm.<br>경사진 원통과 아치를 합친 일체형입니다.</p></details>',html)
html=html.replace('ring-200-raised-195.stl','ring-with-arch.stl').replace('3+d*Math.sin(el)','24+d*Math.sin(el)').replace('camera.lookAt(0,0,3)','camera.lookAt(0,0,24)')
(out/'preview.html').write_text(html)
spec={'wall_inward_tilt_deg':tilt_deg,'wall_top_inset_mm':inset,'wall_top_outer_diameter_mm':195-2*inset,'wall_top_inner_diameter_mm':191-2*inset,'circle_diameter_mm':260,'outer_chord_mm':200,'inner_chord_mm':188,'extrusion_thickness_mm':2,'outer_circle_center_z_from_chord_mm':-co,'inner_circle_center_z_from_chord_mm':-ci,'arch_height_mm':R-co,'crown_band_width_mm':ci-co,'assembly_height_mm':base_z+R-co,'watertight':True,'connected_solids':len(assembly.split())}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
print(json.dumps(spec,indent=2))
