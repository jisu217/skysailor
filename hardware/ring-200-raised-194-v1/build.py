from pathlib import Path
import math, struct, json
from collections import Counter
out=Path(__file__).resolve().parent
# Counterclockwise radial section (radius, z), mm. One continuous solid.
profile=[(94,0),(100,0),(100,2),(97.5,2),(97.5,6),(95.5,6),(95.5,2),(94,2)]
n=1024
vertices=[(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for r,z in profile for i in range(n)]
faces=[]
for j in range(len(profile)):
 for i in range(n):
  a=j*n+i;b=j*n+(i+1)%n;c=((j+1)%len(profile))*n+(i+1)%n;d=((j+1)%len(profile))*n+i
  faces.extend([(a,b,c),(a,c,d)])
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
volume=0
with (out/'ring-200-raised-195.stl').open('wb') as f:
 f.write(b'Ring 200/188 x2 + 195/191 x4; millimeters'.ljust(80,b'\0'));f.write(struct.pack('<I',len(faces)))
 for face in faces:
  a,b,c=[vertices[k] for k in face];normal=cross(sub(b,a),sub(c,a));length=math.sqrt(sum(v*v for v in normal));normal=tuple(v/length for v in normal)
  f.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
  volume+=sum(x*y for x,y in zip(a,cross(b,c)))/6
edges=Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3))
assert all(v==2 for v in edges.values())
expected=math.pi*((100**2-94**2)*2+(97.5**2-95.5**2)*4)
assert abs(volume/expected-1)<0.00001
assert [max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3)]==[200,200,6]
(out/'model.scad').write_text('''// Dimensions in millimeters. Total height: 6 mm.
$fn = 1024;
base_od = 200; base_id = 188; base_t = 2;
wall_od = 195; wall_id = 191; wall_h = 4;
rotate_extrude() polygon([
 [base_id/2,0], [base_od/2,0], [base_od/2,base_t],
 [wall_od/2,base_t], [wall_od/2,base_t+wall_h],
 [wall_id/2,base_t+wall_h], [wall_id/2,base_t], [base_id/2,base_t]
]);
''')
html=(out.parent/'rail-open-frame-v1/assembly-preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':vertices,'faces':faces})+html[b:]
import re
html=re.sub(r'<title>.*?</title>','<title>200mm 링 + 원통</title>',html)
html=re.sub(r'<h1>.*?</h1>','<h1>200mm 링 + 원통</h1>',html)
html=re.sub(r'<small>.*?</small>','<small>아래 링 Ø200 / Ø188 × 2 mm · 위 원통 Ø195 / Ø191 × 4 mm</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>단위 mm. 중심을 맞춘 일체형 모델.<br>아래 링 z=0–2, 위 원통 z=2–6.<br>전체 높이 6mm · 원통 벽 두께 2mm.</p></details>',html)
html=html.replace('rim-X-frame.stl','ring-200-raised-195.stl').replace('el=-.48','el=.48').replace('18+d*Math.sin(el)','3+d*Math.sin(el)').replace('camera.lookAt(0,0,18)','camera.lookAt(0,0,3)')
(out/'preview.html').write_text(html)
print(json.dumps({'bounds_mm':[200,200,6],'watertight':True,'volume_mm3':volume,'triangles':len(faces)}))
