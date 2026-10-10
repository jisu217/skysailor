from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-dual-motor-clips'
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
frame=trimesh.load(src/'fixed-frame-dual-racks.stl',force='mesh');moving=trimesh.load(src/'moving-discs-motor-clips.stl',force='mesh')
fixed=trimesh.boolean.intersection([frame,cyl(23.7,8,1)],engine='manifold')
upper=trimesh.boolean.intersection([moving,box([50,50,20],[0,0,12.2])],engine='manifold')
lower=trimesh.boolean.intersection([moving,box([50,50,20],[0,0,-11.2])],engine='manifold')
# Flat mating faces; no through-holes or motor-side protrusions.
pin=cyl(2.5,3.4,.5)
worm=trimesh.load(src/'worm-bore-1.20mm.stl',force='mesh')
# Put flat interior plate faces on the bed; clips face up.
lower.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
parts=[fixed,upper,lower,pin,worm,worm.copy()]
names=['fixed-ring-rack','upper-x-disc-clips','lower-y-disc-clips','glue-spacer-d5-l3p4','worm-x-bore1p2','worm-y-bore1p2']
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
s=re.sub(r'<h1>.*?</h1>','<h1>중앙 XY 구동 시험 · 평면 접착식</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>고정 링 1 · 이동판 2 · 접착용 원기둥 1 · 웜 2 / 원기둥 Ø5 × 3.4 / 관통 구멍 없음 / 판 사이 간격 3.4mm / 단위 mm</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="print-layout-six-parts.stl" download>전체 출력 배치 STL</a>'+''.join('<a href="'+n+'.stl" download>'+n+'</a>' for n in names)+'</nav>',s,flags=re.S)
s=s.replace('let az=-1.1,el=.48,d=820','let az=-1.1,el=1.0,d=190').replace('const target=new T.Vector3(0,0,48)','const target=new T.Vector3(68,29,3)')
(out/'preview.html').write_text(s)
(out/'parts.json').write_text(json.dumps(report,indent=2));print(json.dumps({'layout_bounds_mm':assembly.extents.tolist(),'parts':report}))
