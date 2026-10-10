from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-dual-motor-clips'
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
frame=trimesh.load(src/'fixed-frame-dual-racks.stl',force='mesh');moving=trimesh.load(src/'moving-discs-motor-clips.stl',force='mesh')
# Enlarge outside profile while keeping the bore exactly 1.2mm.
w9=trimesh.load(src/'worm-bore-1.20mm.stl',force='mesh')
w9=trimesh.boolean.union([w9,cyl(.8,8,4)],engine='manifold')
w9.vertices[:,:2]*=9/8
w9=trimesh.boolean.difference([w9,cyl(.6,10,4)],engine='manifold')
assert w9.is_volume and w9.is_watertight
w9.export(out/'worm9-bore1p2.stl')
wx=w9.copy();wx.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1,0,0]));wx.apply_translation([5.7,0,5.5])
flip=np.array([[0,1,0,0],[1,0,0,0],[0,0,-1,1],[0,0,0,1.]])
def below(m):
 c=m.copy();c.apply_transform(flip);return c
fixed=trimesh.creation.annulus(r_min=7.7,r_max=23.7,height=3,sections=256);fixed.apply_translation([0,0,.5])
wall=trimesh.creation.annulus(r_min=22.7,r_max=23.7,height=3.05,sections=256);wall.apply_translation([0,0,3.475]);fixed=trimesh.boolean.union([fixed,wall],engine='manifold')
def pose(dx,dy):
 c=wx.copy();c.apply_transform(trimesh.transformations.rotation_matrix(2*np.pi*dx/2.5-dy/4.25,[1,0,0],point=[0,0,5.5]));c.apply_translation([dx,dy,0]);return c
cutters=[]
for dy in np.linspace(-5,5,41):
 for dx in [0,2.5,5]:
  c=pose(dx,dy);c.vertices[:,1]=dy+(c.vertices[:,1]-dy)*1.04;c.vertices[:,2]=5.5+(c.vertices[:,2]-5.5)*1.04
  cutters.extend([c,below(c)])
fixed=trimesh.boolean.difference([fixed]+cutters,engine='manifold')
assert fixed.is_volume and fixed.is_watertight
print('Both fixed rack faces regenerated for 9mm worm.',flush=True)
# Increase U opening and cylindrical worm clearance to 9.4mm.
clear=trimesh.creation.cylinder(radius=4.7,height=8.4,sections=128);clear.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1,0,0]));clear.apply_translation([9.7,0,5.5])
front=box([15,9.4,2.4],[13,0,3.2])
moving=trimesh.boolean.difference([moving,clear,front,below(clear),below(front)],engine='manifold')
checks=[]
for dx,dy in [(0,0),(5,0),(0,5),(2.5,2.5),(3.5,3.5),(0,-5)]:
 h=trimesh.boolean.intersection([fixed,pose(dx,dy)],engine='manifold');v=0 if h.is_empty else abs(h.volume);assert v<.001;checks.append([dx,dy,v])
for w in [wx,below(wx)]:
 h=trimesh.boolean.intersection([moving,w],engine='manifold');assert h.is_empty or abs(h.volume)<.001
(out/'worm9-checks.json').write_text(json.dumps(checks))
upper=trimesh.boolean.intersection([moving,box([50,50,20],[0,0,12.2])],engine='manifold')
lower=trimesh.boolean.intersection([moving,box([50,50,20],[0,0,-11.2])],engine='manifold')
upper=trimesh.boolean.difference([upper,cyl(1.6,20,0)],engine='manifold');lower=trimesh.boolean.difference([lower,cyl(1.6,20,0)],engine='manifold')
# Four rounded windows; retain 3mm rim, motor bed and 3mm cross tie.
from shapely.geometry import Point,box as rect
from shapely.ops import triangulate
before_volume=float(upper.volume+lower.volume)
windows=[]
for sx in [-1,1]:
 for sy in [-1,1]:
  poly=Point(0,0).buffer(14.5,resolution=96).intersection(rect(1.5 if sx>0 else -16,5.3 if sy>0 else -16,16 if sx>0 else -1.5,16 if sy>0 else -5.3))
  poly=poly.buffer(-.8).buffer(.8,resolution=16)
  triangles=[t for t in triangulate(poly) if poly.covers(t)]
  vertices=[];faces=[]
  for t in triangles:
   v=list(t.exterior.coords)[:3];j=len(vertices);vertices.extend(v);faces.append([j,j+1,j+2])
  vv,idx=np.unique(np.round(np.array(vertices),9),axis=0,return_inverse=True)
  cut=trimesh.creation.extrude_triangulation(vv,idx[np.array(faces)],12)
  cut.merge_vertices();cut.apply_translation([0,0,-1]);windows.append(cut)
upper=trimesh.boolean.difference([upper]+windows,engine='manifold')
transform=np.array([[0,1,0,0],[1,0,0,0],[0,0,-1,1],[0,0,0,1.]])
low_windows=[]
for cut in windows:
 c=cut.copy();c.apply_transform(transform);low_windows.append(c)
lower=trimesh.boolean.difference([lower]+low_windows,engine='manifold')
after_volume=float(upper.volume+lower.volume)
(out/'weight-reduction.json').write_text(json.dumps({'before_mm3':before_volume,'after_mm3':after_volume,'saved_percent':100*(before_volume-after_volume)/before_volume},indent=2))
print('Moving plate volume reduction: '+str(100*(before_volume-after_volume)/before_volume)+'%',flush=True)
# Separate stepped joining pin: shoulders set 3.4mm between plate inner faces.
pin=trimesh.boolean.union([cyl(2.5,3.4,.5),cyl(1.5,7.4,.5)],engine='manifold')
# Match the existing motor pocket: radius3.2, nominal motor radius3.
def motor_pocket(axis,center):
 m=trimesh.creation.cylinder(radius=3.2,height=15.4,sections=192)
 m.apply_transform(trimesh.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return m
pin=trimesh.boolean.difference([pin,motor_pocket([1,0,0],[-2,0,5.5]),motor_pocket([0,1,0],[0,-2,-4.5])],engine='manifold')
assert pin.is_watertight and pin.is_volume and len(pin.split())==1
for cutter in [motor_pocket([1,0,0],[-2,0,5.5]),motor_pocket([0,1,0],[0,-2,-4.5])]:
 hit=trimesh.boolean.intersection([pin,cutter],engine='manifold')
 assert hit.is_empty or abs(hit.volume)<1e-5
worm=w9.copy()
# Put flat interior plate faces on the bed; clips face up.
lower.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
parts=[fixed,upper,lower,pin,worm,worm.copy()]
names=['fixed-ring-rack','upper-x-disc-clips','lower-y-disc-clips','motor-relieved-stepped-pin','worm-x-bore1p2','worm-y-bore1p2']
positions=[(27,27),(74,23),(115,23),(62,53),(78,53),(92,53)]
packed=[];report=[]
for m,name,(x,y) in zip(parts,names,positions):
 assert m.is_volume and m.is_watertight and len(m.split())==1,(name,len(m.split()))
 m.apply_translation([0,0,-m.bounds[0,2]]);m.export(out/(name+'.stl'))
 p=m.copy();p.apply_translation([x,y,0]);packed.append(p)
 report.append({'part':name,'dimensions_mm':m.extents.tolist(),'volume_mm3':float(m.volume)})
assembly=trimesh.util.concatenate(packed);assembly.export(out/'print-layout-six-parts.stl')
scene=trimesh.Scene()
for p,n in zip(packed,names):scene.add_geometry(p,node_name=n,geom_name=n)
# STL parts remain separate files for slicer orientation and support control.
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for m in packed])+';counts',s)
s=s.replace('[0x85c9de,0xf0b66b,0xb3c6dd,0xb3c6dd][i]','[0x85c9de,0xf0b66b,0x9fd8b0,0xc7a1dd,0xb3c6dd,0xb3c6dd][i]')
s=re.sub(r'cyl[XY]\(3,15.*?;','',s);s=re.sub(r'cyl[XY]\(\.6,3.*?;','',s)
s=re.sub(r'<h1>.*?</h1>','<h1>Ø9 웜 · 경량 이동판 시험 출력</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>고정 링 1 · 이동판 2 · 모터 간섭 절개 단차핀 1 · 웜 Ø9 × 길이8 / 축 구멍 Ø1.2 / 연결핀 Ø5–Ø3 / 이동판 구멍 Ø3.2 / 판 사이 간격 3.4mm / 외곽 테두리 3mm / 연결대 3mm / 단위 mm</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="print-layout-six-parts.stl" download>전체 출력 배치 STL</a>'+''.join('<a href="'+n+'.stl" download>'+n+'</a>' for n in names)+'</nav>',s,flags=re.S)
s=s.replace('let az=-1.1,el=.48,d=820','let az=-1.1,el=1.0,d=190').replace('const target=new T.Vector3(0,0,48)','const target=new T.Vector3(68,29,3)')
(out/'preview.html').write_text(s)
(out/'parts.json').write_text(json.dumps(report,indent=2));print(json.dumps({'layout_bounds_mm':assembly.extents.tolist(),'parts':report}))
