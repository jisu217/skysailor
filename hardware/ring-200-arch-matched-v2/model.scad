// Millimeters. Wall thickness is 2 mm in the radial direction.
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
