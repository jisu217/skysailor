from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-double-disc-taller-center'
base=trimesh.load(src/'frame.stl',force='mesh');moving=trimesh.load(src/'double-disc-assembled.stl',force='mesh')
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Trial rack grooves on +X half of upper disc, 0.5 mm deep, 2mm pitch.
cutters=[]
for x in np.arange(2,14,2):
 c=box([.7,11,.7],[0,0,0]);c.apply_transform(trimesh.transformations.rotation_matrix(math.radians(20),[0,0,1]));c.apply_translation([x,0,4.05]);cutters.append(c)
moving=trimesh.boolean.difference([moving]+cutters,engine='manifold')
assert moving.is_volume and moving.is_watertight
moving.export(out/'grooved-moving-discs.stl')
# Preview worm is an explicit conceptual helix, not a generated conjugate gear tooth.
meshes=[base,moving];assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('g.addGroup(0,'+str(len(base.faces)*3)+',0)','g.addGroup(0,'+str(len(base.faces)*3)+',0)')
s=re.sub(r'g.clearGroups\(\);g.addGroup\(.*?scene.add\(new T.Mesh\(g,\[.*?\]\)\);',f'''g.clearGroups();g.addGroup(0,{len(base.faces)*3},0);g.addGroup({len(base.faces)*3},{len(moving.faces)*3},1);scene.add(new T.Mesh(g,[new T.MeshStandardMaterial({{color:0x85c9de,roughness:.4,flatShading:true}}),new T.MeshStandardMaterial({{color:0xf0b66b,roughness:.4,flatShading:true}})]));''',s)
s=re.sub(r'<h1>.*?</h1>','<h1>X축 웜 + 615 모터 · 배치안</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>615 몸통 가정 Ø6 × 15mm · 웜 외경 약 4mm / 피치 2mm · 원판 홈 깊이 0.5mm · 치형 및 맞물림 미검증</small><div style="margin-top:16px"><button id="driveview">구동부 확대</button></div>',s)
extra='''
function cylX(r,len,x,z,color){const m=new T.Mesh(new T.CylinderGeometry(r,r,len,64),new T.MeshStandardMaterial({color,roughness:.45}));m.rotation.z=Math.PI/2;m.position.set(x,0,z);scene.add(m);return m}
// Fixed drive axis is horizontal along X, above the upper disc.
cylX(3,15,21,5.9,0x66768b);cylX(.5,6,12,5.9,0xd2d7dd);cylX(1.45,9,7,5.9,0xa0b0c3);
const helix=[];for(let i=0;i<=500;i++){const x=2.5+9*i/500,ang=(x-2.5)*Math.PI;helix.push(new T.Vector3(x,1.7*Math.cos(ang),5.9+1.7*Math.sin(ang)))}
const curve=new T.CatmullRomCurve3(helix);scene.add(new T.Mesh(new T.TubeGeometry(curve,500,.3,8,false),new T.MeshStandardMaterial({color:0xc7d5e5,roughness:.4})));
// Schematic mounting bracket lands outside the moving plate, on fixed frame.
function block(d,p){const m=new T.Mesh(new T.BoxGeometry(...d),new T.MeshStandardMaterial({color:0x8ab7b7}));m.position.set(...p);scene.add(m)}
block([6,10,1],[21,0,2.5]);block([3,2,4],[21,-4,4]);block([3,2,4],[21,4,4]);
'''
pos=s.index('scene.add(new T.HemisphereLight');s=s[:pos]+extra+s[pos:]
s=s.replace("update();document.querySelector('#status')","document.querySelector('#driveview').onclick=()=>{target.set(10,0,3);d=95;az=-1.1;el=.8;update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(25,Math.min')
s=re.sub(r'<a href=".*?</a>','',s)
(out/'preview.html').write_text(s)
print('Grooved disc validated; motor and worm are schematic visualization only.')
