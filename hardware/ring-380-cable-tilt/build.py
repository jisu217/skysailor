from pathlib import Path
import trimesh,json,re
out=Path(__file__).resolve().parent;root=out.parent
base=trimesh.load(root/'ring-380-floor-1mm/frame.stl',force='mesh')
s=(root/'ring-380-floor-1mm/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':base.vertices.tolist(),'faces':base.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<title>.*?</title>','<title>실 4개로 기울이는 구동부</title>',s)
s=re.sub(r'<h1>.*?</h1>','<h1>실 4개 · 2축 기울임</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>개념 배치 · 주황: 임시 구동부 · 노랑/초록: 실 · 회전 중심 아래 30mm에 구동부 중심 · 모터/장력장치 미설계</small>',s)
a=s.index('<div style="margin-top:16px');b=s.index('</div>',a)
s=s[:a]+'''<div style="margin-top:16px;line-height:2"><button id="closeup">기울임 장치 확대</button><br><label>좌우 <input id="roll" type="range" min="-20" max="20" value="0"><span id="rv">0°</span></label><br><label>앞뒤 <input id="pitch" type="range" min="-20" max="20" value="0"><span id="pv">0°</span></label><div id="shift"></div></div>'''+s[b+6:]
s=re.sub(r'<a href=".*?</a>','',s)
a=s.index('const moving=new T.Group()');b=s.index('scene.add(new T.HemisphereLight',a)
s=s[:a]+'''scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.5,flatShading:true})));
const fixed=new T.Group();scene.add(fixed);
const pivot=new T.Group();pivot.position.z=-12;scene.add(pivot);
const inner=new T.Group();pivot.add(inner);
function block(parent,size,pos,color){const m=new T.Mesh(new T.BoxGeometry(...size),new T.MeshStandardMaterial({color,roughness:.55}));m.position.set(...pos);parent.add(m);return m}
function rod(parent,a,b,r,color){const va=new T.Vector3(...a),vb=new T.Vector3(...b),delta=vb.clone().sub(va);const m=new T.Mesh(new T.CylinderGeometry(r,r,delta.length(),20),new T.MeshStandardMaterial({color,roughness:.5}));m.position.copy(va).add(vb).multiplyScalar(.5);m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),delta.normalize());parent.add(m);return m}
// Fixed fork from underside of the Y arm to outer gimbal pivots.
for(const sign of [-1,1]){block(fixed,[4,2,13],[0,sign*13,-6.5],0x769aaf);rod(fixed,[0,sign*10,-12],[0,sign*14,-12],1,0x526577)}
for(const sign of [-1,1]){block(pivot,[24,2,2],[0,sign*10,0],0xb2bbc7);block(pivot,[2,20,2],[sign*11,0,0],0xb2bbc7);rod(pivot,[sign*7,0,0],[sign*11,0,0],1,0x526577);block(inner,[16,2,2],[0,sign*7,0],0xd2d8de);block(inner,[2,12,2],[sign*7,0,0],0xd2d8de)}
rod(inner,[0,0,0],[0,0,-30],1.5,0xc6a0f6);
block(inner,[12,12,16],[0,0,-30],0xf0a64b);
// Cable attachment collar above the payload. Four tethers carry tension only.
block(inner,[12,12,2],[0,0,-20],0xc6a0f6);
const anchors=[[32,0,-1],[-32,0,-1],[0,32,-1],[0,-32,-1]];
const attachments=[[6,0,-20],[-6,0,-20],[0,6,-20],[0,-6,-20]];
const lines=anchors.map((p,i)=>{const geom=new T.BufferGeometry().setFromPoints([new T.Vector3(...p),new T.Vector3()]);const line=new T.Line(geom,new T.LineBasicMaterial({color:i<2?0xffd166:0x71e0a3}));scene.add(line);return line});
for(const p of anchors){rod(fixed,[p[0],p[1],-2],[p[0],p[1],3],.8,0x627b90)}
// Two generic motor/spool envelopes, no gearing or return-cable routing claimed.
block(fixed,[10,8,8],[32,0,8],0x536373);block(fixed,[8,10,8],[0,32,8],0x536373);
const cg=new T.Vector3();
function syncTilt(){pivot.rotation.y=Number(document.querySelector('#roll').value)*Math.PI/180;inner.rotation.x=Number(document.querySelector('#pitch').value)*Math.PI/180;scene.updateMatrixWorld(true);lines.forEach((line,i)=>{const end=inner.localToWorld(new T.Vector3(...attachments[i]));line.geometry.setFromPoints([new T.Vector3(...anchors[i]),end])});inner.localToWorld(cg.set(0,0,-30));document.querySelector('#rv').textContent=document.querySelector('#roll').value+'°';document.querySelector('#pv').textContent=document.querySelector('#pitch').value+'°';document.querySelector('#shift').textContent='仮 구동부 중심 이동: X '+cg.x.toFixed(1)+'mm / Y '+cg.y.toFixed(1)+'mm';}
'''+s[b:]
# Remove previous slider event bindings, retaining camera controls.
a=s.index("document.querySelector('#closeup').onclick=");b=s.index("update();document.querySelector('#status')",a)
s=s[:a]+'''document.querySelector('#closeup').onclick=()=>{target.set(0,0,-18);d=180;az=-1.1;el=-.4;update()};for(const id of ['roll','pitch'])document.querySelector('#'+id).oninput=()=>{syncTilt();update()};syncTilt();'''+s[b:]
s=s.replace('仮 구동부','임시 구동부')
(out/'preview.html').write_text(s)
print('Cable tilt concept preview generated; original frame preserved, XY assembly removed.')
