// All dimensions in mm
outer_diameter = 400;
wall_thickness = 2;
height = 2;
$fn = 2048;
difference() {
    cylinder(d=outer_diameter, h=height);
    translate([0,0,-0.1])
        cylinder(d=outer_diameter-2*wall_thickness, h=height+0.2);
}
