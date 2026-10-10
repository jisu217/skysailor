from pathlib import Path
import trimesh,numpy as np,json,math,re
out=Path(__file__).resolve().parent;root=out.parent
L=214.7*math.asin(190/215)
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
def cylinder(r,h,p):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation(p);return m
strip=box([L,3,.6],[L/2,0,.3]);eye=cylinder(4,.32,[L,0,.16])
blank=trimesh.boolean.union([strip,eye],engine='manifold')
# Thin the entire circular eye, including the overlap with the strip.
blank=trimesh.boolean.difference([blank,cylinder(4,.5,[L,0,.57])],engine='manifold')
parts=[]
for angle in [0,45]:
 hole=box([3.4,3.4,1],[0,0,0]);hole.apply_transform(trimesh.transformations.rotation_matrix(math.radians(angle),[0,0,1]));hole.apply_translation([L,0,.3])
 rib=trimesh.boolean.difference([blank,hole],engine='manifold')
 assert rib.is_watertight and rib.is_volume and len(rib.split())==1
 rib.export(out/f'rib-eye-{angle}deg.stl')
 for j in range(4):
  i=(0 if angle==0 else 4)+j;m=rib.copy();m.apply_translation([8,8+i*10,0]);m.export(out/f'rib-{i+1:02d}.stl');parts.append(m)
# Lower square headed pin; head top is z=1.2, pin exposed length 3.76.
pin=trimesh.boolean.union([box([8,8,1.2],[0,0,.6]),box([3,3,3.86],[0,0,3.03])],engine='manifold')
# Upper cap, printed cavity facing up. Socket has .1 mm clearance per side.
cap=trimesh.boolean.difference([cylinder(4,2,[0,0,1]),box([3.2,3.2,1.5],[0,0,1.45])],engine='manifold')
for name,m in [('lower-square-pin',pin),('upper-square-cap',cap)]:
 assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/(name+'.stl'))
for m,p in [(pin,[20,92,0]),(cap,[34,92,0])]:
 q=m.copy();q.apply_translation(p);parts.append(q)
kit=trimesh.util.concatenate(parts);kit.export(out/'eight-ribs-and-connectors.stl')
s=(root/'rib-flat-eight-square-eye/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':kit.vertices.tolist(),'faces':kit.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>0° 리브 4개 + 45° 리브 4개 · 양면 결합핀</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>띠 두께 0.6mm · 원판 Ø8 / 두께 0.32mm · 구멍 3.4mm · 사각핀 3mm + 원형 소켓 캡 Ø8 · 8장 적층 2.56mm</small>',s)
s=s.replace('eight-ribs-print.stl','eight-ribs-and-connectors.stl').replace('single-rib-square-eye.stl','rib-eye-0deg.stl')
s=s.replace('</nav>','<a href="rib-eye-45deg.stl" download>45° 리브</a><a href="lower-square-pin.stl" download>아래 핀</a><a href="upper-square-cap.stl" download>위 캡</a></nav>')
(out/'preview.html').write_text(s)
print('Validated two rib variants and pin/cap. Disc 0.32mm; strip 0.6mm; kit bounds '+str(kit.extents))
