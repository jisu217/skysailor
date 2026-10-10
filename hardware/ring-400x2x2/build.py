from pathlib import Path
import math
import struct
from collections import Counter

out = Path(__file__).resolve().parent
segments = 2048
vertices = [(r*math.cos(2*math.pi*i/segments), r*math.sin(2*math.pi*i/segments), z)
            for r,z in [(200,0),(200,2),(198,0),(198,2)] for i in range(segments)]
faces = []
for i in range(segments):
    j = (i+1)%segments
    for a,b,c,d in [(i,j,segments+j,segments+i),
                    (2*segments+j,2*segments+i,3*segments+i,3*segments+j),
                    (segments+i,segments+j,3*segments+j,3*segments+i),
                    (j,i,2*segments+i,2*segments+j)]:
        faces.extend([(a,b,c),(a,c,d)])
edges = Counter(tuple(sorted((f[k],f[(k+1)%3]))) for f in faces for k in range(3))
assert all(count == 2 for count in edges.values())
volume = 0
with (out/'ring-400x2x2.stl').open('wb') as file:
    file.write(b'Ring OD400 ID396 H2 mm'.ljust(80,b'\0'))
    file.write(struct.pack('<I',len(faces)))
    for face in faces:
        a,b,c = [vertices[v] for v in face]
        u = [b[k]-a[k] for k in range(3)]
        v = [c[k]-a[k] for k in range(3)]
        normal = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        length = math.sqrt(sum(x*x for x in normal))
        normal = [x/length for x in normal]
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        file.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
assert abs(volume - math.pi*(200**2-198**2)*2) < .01
(out/'ring-400x2x2.scad').write_text('''// All dimensions in mm
outer_diameter = 400;
wall_thickness = 2;
height = 2;
$fn = 2048;
difference() {
    cylinder(d=outer_diameter, h=height);
    translate([0,0,-0.1])
        cylinder(d=outer_diameter-2*wall_thickness, h=height+0.2);
}
''')
print(f'Validated closed mesh: {len(faces)} triangles, volume {volume:.4f} mm^3, bounds 400 x 400 x 2 mm')
