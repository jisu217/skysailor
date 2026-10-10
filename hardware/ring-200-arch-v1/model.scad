// Dimensions in millimeters. Arch stands on the ring top at z=2.
$fn = 1024;
base_od = 200; base_id = 188; base_t = 2;
wall_od = 195; wall_id = 191; wall_h = 4;
wall_tilt=15; // inward angle from vertical, degrees
wall_inset=wall_h*tan(wall_tilt);
rotate_extrude() polygon([
 [base_id/2,0], [base_od/2,0], [base_od/2,base_t],
 [wall_od/2,base_t], [wall_od/2-wall_inset,base_t+wall_h],
 [wall_id/2-wall_inset,base_t+wall_h], [wall_id/2,base_t], [base_id/2,base_t]
]);

R=130; outer_half=100; inner_half=94; arch_thickness=2;
co=sqrt(R*R-outer_half*outer_half);
ci=sqrt(R*R-inner_half*inner_half);
ao=asin(outer_half/R); ai=asin(inner_half/R);
outer_arc=[for(i=[0:512]) [R*sin(-ao+2*ao*i/512),R*cos(-ao+2*ao*i/512)-co]];
inner_arc=[for(i=[512:-1:0]) [R*sin(-ai+2*ai*i/512),R*cos(-ai+2*ai*i/512)-ci]];
translate([0,0,base_t]) rotate([90,0,0])
linear_extrude(height=arch_thickness,center=true)
polygon(concat(outer_arc,inner_arc));
