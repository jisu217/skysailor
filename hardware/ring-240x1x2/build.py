from pathlib import Path
import math, struct
from collections import Counter
out = Path(__file__).resolve().parent
outer_diameter, wall_thickness, height = 240., 1., 2.
n = 1440
vertices = [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z)
            for r,z in [(120.,0.),(120.,height),(119.,0.),(119.,height)] for i in range(n)]
faces=[]
for i in range(n):
    j=(i+1)%n
    for a,b,c,d in [(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),
                    (n+i,n+j,3*n+j,3*n+i),(j,i,2*n+i,2*n+j)]:
        faces.extend([(a,b,c),(a,c,d)])
def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
edges=Counter((a,b) for f in faces for a,b in zip(f,f[1:]+f[:1]))
assert all(count==1 and edges[b,a]==1 for (a,b),count in edges.items())
volume=sum(sum(x*y for x,y in zip(vertices[a],cross(vertices[b],vertices[c]))) / 6 for a,b,c in faces)
assert abs(volume/(math.pi*(120**2-119**2)*height)-1)<0.00001
with (out/'ring-240x1x2.stl').open('wb') as f:
    f.write(b'Ring OD240 ID238 H2; units mm'.ljust(80,b'\0'))
    f.write(struct.pack('<I',len(faces)))
    for ids in faces:
        a,b,c=[vertices[i] for i in ids]
        normal=cross(tuple(y-x for x,y in zip(a,b)),tuple(y-x for x,y in zip(a,c)))
        norm=math.sqrt(sum(x*x for x in normal))
        f.write(struct.pack('<12fH',*(x/norm for x in normal),*a,*b,*c,0))
assert (out/'ring-240x1x2.stl').stat().st_size==84+50*len(faces)
print(f'Validated closed oriented mesh: {len(faces)} triangles, volume {volume:.3f} mm3; 240 x 240 x 2 mm')
