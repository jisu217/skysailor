from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-floor-1mm'
base=trimesh.load(src/'frame.stl',force='mesh')
xpart=trimesh.load(src/'linked-slider-print.stl',force='mesh');xpart.apply_translation([0,0,-1.2])
def box(size,pos):
 m=trimesh.creation.box(extents=size);m.apply_translation(pos);return m
# Inverted T rail: narrow vertical stem and lower flange, below X plate.
stem=box([1.6,50,3],[0,0,-2.2]) # -3.7..-0.7; overlaps X plate
flange=box([6,50,1],[0,0,-4.2]) # -4.7..-3.7
# Four triangular ribs at the upper stem-to-X-plate junction.
ribs=[]
for y in [-3,3]:
 for sign in [-1,1]:
  profile=[(sign*.78,-1.18),(sign*2.8,-1.18),(sign*.78,-2.5)]
  v=[(x,yy,z) for yy in [y-.5,y+.5] for x,z in profile]
  f=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
  m=trimesh.Trimesh(vertices=v,faces=f);m.fix_normals();ribs.append(m)
xpart=trimesh.boolean.union([xpart,stem,flange]+ribs,engine='manifold')
# Captured Y shoe: 1mm bottom and sides, upper lips around flange.
outer=box([8.4,12,3.4],[0,0,-4.2])
void=box([6.4,12.2,1.4],[0,0,-4.2])
slot=box([2,12.2,2],[0,0,-2.5])
ypart=trimesh.boolean.difference([outer,void,slot],engine='manifold')
for m in [base,xpart,ypart]:assert m.is_volume and m.is_watertight
# Check both travel extremes and center, including diagonal combinations.
for dx in [-15,0,15]:
 xx=xpart.copy();xx.apply_translation([dx,0,0])
 hit=trimesh.boolean.intersection([base,xx],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
 for dy in [-15,0,15]:
  yy=ypart.copy();yy.apply_translation([dx,dy,0])
  for fixed in [base,xx]:
   hit=trimesh.boolean.intersection([fixed,yy],engine='manifold');assert hit.is_empty or abs(hit.volume)<1e-5
for name,m in [('frame',base),('x-carriage-with-y-rail',xpart),('y-slider',ypart)]:
 p=m.copy();p.apply_translation([0,0,-p.bounds[0,2]]);p.export(out/(name+'.stl'))
meshes=[base,xpart,ypart];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>XY 슬라이더 배치</title>',s);s=re.sub(r'<h1>.*?</h1>','<h1>XY 슬라이더 배치</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>Y 레일 50mm · Y 슬라이더 길이 12mm / 두께 1mm · X/Y 이동 각 ±15mm · 유격 0.2mm</small>',s)
s=s.replace(' 이동 <input',' X <input').replace('</label></div>','</label><label> Y <input id="ytravel" type="range" min="-15" max="15" value="0" step="0.1"></label></div>')
s=s.replace('linked-slider-print.stl','x-carriage-with-y-rail.stl').replace('슬라이더 STL','X 이동부 STL').replace('</nav>','<a href="y-slider.stl" download>Y 슬라이더 STL</a></nav>')
a=s.index('const moving=new T.Group()');b=s.index('scene.add(new T.HemisphereLight',a)
s=s[:a]+'''const moving=new T.Group(),ymoving=new T.Group();scene.add(moving);moving.add(ymoving);let offset=0;const counts='''+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;const part=new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0xf0b66b,0x95dc9e][i],roughness:.4,flatShading:true}));if(i===0)scene.add(part);else if(i===1)moving.add(part);else ymoving.add(part)});
'''+s[b:]
s=s.replace("document.querySelector('#travel').oninput", "document.querySelector('#ytravel').oninput=e=>{ymoving.position.y=Number(e.target.value);update()};document.querySelector('#travel').oninput")
s=s.replace('target.set(moving.position.x,0,1);d=145;az=-1.1;el=.6','target.set(moving.position.x,0,-2);d=160;az=-1.1;el=-.5')
(out/'preview.html').write_text(s)
print(json.dumps({'total_PLA_g':assembly.volume*.00124,'verified':'No interference at 9 XY positions','Y_travel_mm':30}))
