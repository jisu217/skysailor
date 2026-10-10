// Millimetres. Inward-facing L section.
outer_diameter = 240;
height = 2;
wall_thickness = 1;
base_width = 3;
base_thickness = 1;
$fn = 1440;
r = outer_diameter/2;
rotate_extrude() polygon(points=[
 [r,0], [r,height], [r-wall_thickness,height],
 [r-wall_thickness,base_thickness],
 [r-base_width,base_thickness], [r-base_width,0]
]);
