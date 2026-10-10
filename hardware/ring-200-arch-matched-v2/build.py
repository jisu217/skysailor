from pathlib import Path
import math,json,re
import numpy as np
import trimesh
out=Path(__file__).resolve().parent
R=130.; co=math.sqrt(R*R-100**2); wall_h=4.; wall_t=2.
z=np.linspace(0,wall_h,65)
r=np.sqrt(R*R-(co+z)**2)
# Wall thickness is radial (horizontal), as on the original cylinder.
profile=np.vstack(([[94,0],[100,0]],np.column_stack((r,2+z)),np.column_stack(((r-wall_t)[::-1],(2+z)[::-1])),[[94,2],[94,0]]))
base=trimesh.creation.revolve(profile,sections=1024)
arch=trimesh.load(out.parent/'ring-200-arch-v1/arch.stl',force='mesh')
assembly=trimesh.boolean.union([base,arch],engine='manifold')
for name,m in [('ring-curved-wall',base),('ring-with-arch',assembly)]:
 assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/(name+'.stl'))
assert np.allclose(assembly.extents,[200,200,2+R-co],atol=.02)
scad='''// Millimeters. Wall thickness is 2 mm in the radial direction.
$fn=1024;
R=130; base_t=2; base_ro=100; base_ri=94; wall_h=4; wall_t=2;
co=sqrt(R*R-base_ro*base_ro);
ci=sqrt(R*R-base_ri*base_ri);
function ro(h)=sqrt(R*R-(co+h)*(co+h));
outer_wall=[for(i=[0:64]) [ro(wall_h*i/64),base_t+wall_h*i/64]];
inner_wall=[for(i=[64:-1:0]) [ro(wall_h*i/64)-wall_t,base_t+wall_h*i/64]];
union(){
 rotate_extrude() polygon(concat([[base_ri,0],[base_ro,0]],outer_wall,inner_wall,[[base_ri,base_t]]));
 ao=asin(base_ro/R); ai=asin(base_ri/R);
 outer_arc=[for(i=[0:512]) [R*sin(-ao+2*ao*i/512),R*cos(-ao+2*ao*i/512)-co]];
 inner_arc=[for(i=[512:-1:0]) [R*sin(-ai+2*ai*i/512),R*cos(-ai+2*ai*i/512)-ci]];
 translate([0,0,base_t]) rotate([90,0,0]) linear_extrude(height=2,center=true) polygon(concat(outer_arc,inner_arc));
}
'''
(out/'model.scad').write_text(scad)
html=(out.parent/'ring-200-arch-v1/preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<small>.*?</small>','<small>아치에 맞춘 곡면 벽 · 아래 외경 200mm · 벽 높이 4mm · 반지름 방향 두께 2mm</small>',html)
html=re.sub(r'<details>.*?</details>',f'<details><summary>ⓘ</summary><p>벽 바깥면은 아치의 바깥 원호를 회전한 곡면입니다.<br>아래 외경 200mm / 내경 196mm.<br>위 외경 {2*r[-1]:.3f}mm / 내경 {2*(r[-1]-wall_t):.3f}mm.<br>벽 높이 4mm · 반지름 방향 두께 2mm.<br>링 내경 188mm · 전체 높이 {2+R-co:.3f}mm.<br>드래그 회전 · 휠 확대.</p></details>',html)
(out/'preview.html').write_text(html)
spec={'wall_bottom_od_mm':200,'wall_bottom_id_mm':196,'wall_top_od_mm':float(2*r[-1]),'wall_top_id_mm':float(2*(r[-1]-wall_t)),'wall_height_mm':4,'wall_radial_thickness_mm':2,'inward_angle_from_vertical_bottom_deg':math.degrees(math.atan(co/100)),'inward_angle_from_vertical_top_deg':math.degrees(math.atan((co+4)/r[-1])),'overall_height_mm':2+R-co,'watertight':True,'connected_solids':1}
(out/'specs.json').write_text(json.dumps(spec,indent=2))
print(json.dumps(spec,indent=2))
