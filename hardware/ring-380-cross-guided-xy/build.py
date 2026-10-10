from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;root=out.parent
base=trimesh.load(root/'ring-380-floor-1mm/frame.stl',force='mesh')
xpart=trimesh.load(root/'ring-380-xy-sliders/x-carriage-with-y-rail.stl',force='mesh');xpart.apply_translation([0,0,-4.7])
upper=trimesh.load(root/'ring-380-xy-sliders/y-slider.stl',force='mesh');upper.apply_translation([0,0,-5.9])
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Extract two contour shoes from the existing linked part.
linked=trimesh.load(root/'ring-380-floor-1mm/linked-slider-print.stl',force='mesh');linked.apply_translation([0,0,-1.2])
shoe=trimesh.boolean.intersection([linked,box([12,20,20],[25,0,0])],engine='manifold');shoe.apply_translation([-25,0,0]);shoe.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[0,0,1]))
parts=[]
# Place Y support shoes farther out to clear the moving X rail.
for y in [-55,55]:
 m=shoe.copy();m.apply_translation([0,y,0]);parts.append(m)
 for x in [-3.7,3.7]:parts.append(box([1,12,7],[x,y,-3.7]))
 parts.append(box([66,4,1],[0,y,-7.2]))
for x in [-32,32]:
 parts.append(box([2,114,1],[x,0,-7.2]))
 parts.append(box([2,4,4],[x,0,-9.2]))
# Second crossing rail: rectangular bar running along X.
parts.append(box([66,3,2],[0,0,-10.2]))
ypart=trimesh.boolean.union(parts,engine='manifold')
# Lower captive sleeve runs along X; linked to the upper Y sleeve.
sleeve=trimesh.boolean.difference([box([12,5.4,4.4],[0,0,-10.2]),box([12.2,3.4,2.4],[0,0,-10.2])],engine='manifold')
carrier=trimesh.boolean.union([upper,sleeve,box([1,5.4,2.4],[-5.5,0,-6.9]),box([1,5.4,2.4],[5.5,0,-6.9])],engine='manifold')
for m in [xpart,ypart,carrier]:assert m.is_volume and m.is_watertight
# Validate sampled simultaneous travel positions.
for dx in [-15,0,15]:
 for dy in [-15,0,15]:
  moving=[]
  for m,p in [(xpart,[dx,0,0]),(ypart,[0,dy,0]),(carrier,[dx,dy,0])]:
   q=m.copy();q.apply_translation(p);moving.append(q)
  for i,a in enumerate(moving):
   for b in [base]+moving[:i]:
    hit=trimesh.boolean.intersection([a,b],engine='manifold')
    assert hit.is_empty or abs(hit.volume)<1e-4,(dx,dy,i,hit.volume)
meshes=[base,xpart,ypart,carrier];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(root/'ring-380-xy-sliders/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>고정 +자 네 팔을 쓰는 XY 구조</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>주황 X 이동부 · 초록 Y 이동부 · 보라 중앙 받침 · 각 ±15mm · 간섭 회피를 위해 Y 지지 간격 110mm</small>',s)
s=re.sub(r'<a href="(?:x-carriage-with-y-rail|y-slider).stl".*?</a>','',s)
a=s.index('const moving=new T.Group()');b=s.index('scene.add(new T.HemisphereLight',a)
s=s[:a]+'const moving=new T.Group(),ymoving=new T.Group(),carrierGroup=new T.Group();scene.add(moving,ymoving,carrierGroup);let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;const part=new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0x95dc9e,0xc6a0f6][i],roughness:.4,flatShading:true}));[scene,moving,ymoving,carrierGroup][i].add(part)});
'''+s[b:]
s=s.replace('ymoving.position.y=Number(e.target.value);update()','ymoving.position.y=Number(e.target.value);carrierGroup.position.y=ymoving.position.y;update()').replace('moving.position.x=Number(e.target.value);update()','moving.position.x=Number(e.target.value);carrierGroup.position.x=moving.position.x;update()').replace('d=160;az','d=260;az')
(out/'preview.html').write_text(s)
print('Verified 9 XY combinations without mesh interference; concept preview ready.')
