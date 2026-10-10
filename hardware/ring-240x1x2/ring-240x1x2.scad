// All dimensions in millimetres. Diameter is the outside diameter.
outer_diameter = 240;
wall_thickness = 1;
height = 2;
$fn = 1440;
difference() {
    cylinder(d=outer_diameter, h=height);
    translate([0, 0, -0.01])
        cylinder(d=outer_diameter-2*wall_thickness, h=height+0.02);
}
