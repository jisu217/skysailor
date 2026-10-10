from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-double-disc-taller-center'
base=trimesh.load(src/'frame.stl',force='mesh');moving=trimesh.load(src/'double-disc-assembled.stl',force='mesh')
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Motor body axis X, offset from disc center so worm points outward.
# Seat is 0.5 mm below the top surface at z=4.2.
pocket=box([15.4,6.4,.7],[-2,0,4.05])
moving=trimesh.boolean.difference([moving,pocket],engine='manifold')
assert moving.is_volume and moving.is_watertight
moving.export(out/'motor-pocket-moving-discs.stl')
# Preview worm is an explicit conceptual helix, not a generated conjugate gear tooth.
meshes=[base,moving];assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('g.addGroup(0,'+str(len(base.faces)*3)+',0)','g.addGroup(0,'+str(len(base.faces)*3)+',0)')
s=re.sub(r'g.clearGroups\(\);g.addGroup\(.*?scene.add\(new T.Mesh\(g,\[.*?\]\)\);',f'''g.clearGroups();g.addGroup(0,{len(base.faces)*3},0);g.addGroup({len(base.faces)*3},{len(moving.faces)*3},1);scene.add(new T.Mesh(g,[new T.MeshStandardMaterial({{color:0x85c9de,roughness:.4,flatShading:true}}),new T.MeshStandardMaterial({{color:0xf0b66b,roughness:.4,flatShading:true}})]));''',s)
s=re.sub(r'<h1>.*?</h1>','<h1>이동 원판 위 615 모터 + 웜</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>615 몸통 가정 Ø6 × 15mm · 웜 외경 약 4mm / 피치 2mm · 모터 자리 깊이 0.5mm · 고정 링 랙은 미설계</small><div style="margin-top:16px"><button id="driveview">구동부 확대</button></div>',s)
extra='''
function cylX(r,len,x,z,color){const m=new T.Mesh(new T.CylinderGeometry(r,r,len,64),new T.MeshStandardMaterial({color,roughness:.45}));m.rotation.z=Math.PI/2;m.position.set(x,0,z);scene.add(m);return m}
// Motor sits on the moving disc, body x=-9.5..5.5.
// Body bottom z=3.7, recessed 0.5 mm into upper disc.
cylX(3,15,-2,6.7,0x66768b);cylX(.5,5,7,6.7,0xd2d7dd);cylX(1.45,9,12,6.7,0xa0b0c3);
const helix=[];for(let i=0;i<=500;i++){const x=7.5+9*i/500,ang=(x-7.5)*Math.PI;helix.push(new T.Vector3(x,1.7*Math.cos(ang),6.7+1.7*Math.sin(ang)))}
const curve=new T.CatmullRomCurve3(helix);scene.add(new T.Mesh(new T.TubeGeometry(curve,500,.3,8,false),new T.MeshStandardMaterial({color:0xc7d5e5,roughness:.4})));
'''
pos=s.index('scene.add(new T.HemisphereLight');s=s[:pos]+extra+s[pos:]
s=s.replace("update();document.querySelector('#status')","document.querySelector('#driveview').onclick=()=>{target.set(3,0,4);d=95;az=-1.1;el=.8;update()};update();document.querySelector('#status')")
s=s.replace('Math.max(140,Math.min','Math.max(25,Math.min')
s=re.sub(r'<a href=".*?</a>','',s)
(out/'preview.html').write_text(s)
print('Motor pocket disc validated; motor and worm moved onto disc. Fixed rack remains undesigned.')
