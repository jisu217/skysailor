from pathlib import Path
import numpy as np, trimesh, json
out=Path(__file__).resolve().parent
# Spherical cap: outer diameter 240 mm, rise 40 mm, concentric 1 mm shell.
a,h,t=120.,40.,1.
R=(a*a+h*h)/(2*h); zc=h-R
N,M=256,96
v=[]; f=[]
for radius in [R,R-t]:
 start=len(v); v.append([0,0,zc+radius]); theta=np.arccos(-zc/radius)
 for j in range(1,M+1):
  q=theta*j/M
  for k in range(N):
   p=2*np.pi*k/N;v.append([radius*np.sin(q)*np.cos(p),radius*np.sin(q)*np.sin(p),zc+radius*np.cos(q)])
 for k in range(N):f.append([start,start+1+k,start+1+(k+1)%N])
 for j in range(M-1):
  b=start+1+j*N;c=b+N
  for k in range(N):
   l=(k+1)%N;f.extend([[b+k,c+k,c+l],[b+k,c+l,b+l]])
S=1+M*N
for i in range(N*(2*M-1),len(f)):f[i]=f[i][::-1]
b=1+(M-1)*N;c=S+b
for k in range(N):
 l=(k+1)%N; f.extend([[b+k,c+l,c+k],[b+k,b+l,c+l]])
m=trimesh.Trimesh(v,f,process=True);m.fix_normals();assert m.is_watertight and m.is_volume
m.export(out/'dome-240x40-shell1mm.stl')
(out/'mesh.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()}))
(out/'specs.json').write_text(json.dumps({'outer_diameter_mm':240,'outer_height_mm':40,'shell_normal_thickness_mm':1,'sphere_radius_mm':R,'triangles':len(m.faces),'watertight':bool(m.is_watertight),'volume_mm3':m.volume},indent=2))
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>레일 구조 · 얕은 돔</title><style>*{box-sizing:border-box}body{margin:0;background:#101722;color:#edf4fc;font:14px system-ui;overflow:hidden}#view{position:fixed;inset:0}header{position:fixed;top:20px;left:24px;z-index:2}h1{font-size:21px;margin:0 0 8px}small{color:#aabdd2}nav{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:3}button,summary,a{background:#243449;color:white;border:1px solid #52647a;border-radius:10px;padding:10px 16px;cursor:pointer;text-decoration:none}details{position:fixed;right:20px;top:20px;z-index:3;max-width:320px}summary{width:42px;padding:10px;text-align:center;list-style:none}details p{background:#243449;padding:16px;border-radius:10px;line-height:1.7}#status{position:fixed;bottom:80px;left:24px;color:#b7c9dc}canvas{display:block;touch-action:none}</style><div id="view"></div><header><h1>01 · 얕은 돔</h1><small>지름 240 mm · 높이 40 mm · 두께 1 mm</small></header><details><summary>ⓘ</summary><p>정확한 반구보다 낮은 구면 돔입니다. 아래는 열려 있고 두께는 구면에 수직으로 1mm입니다. 중앙축·레일은 다음 단계에서 추가합니다.<br>드래그: 회전 · 휠: 확대<br>이번 두께는 형상 검토용이며 출력 강도나 비행 성능을 검증한 값은 아닙니다. 3D 라이브러리를 불러오려면 인터넷 연결이 필요합니다.</p></details><nav><button data-v="angle">입체</button><button data-v="top">위</button><button data-v="side">옆</button><button data-v="bottom">아래</button><a href="dome-240x40-shell1mm.stl" download>STL</a></nav><div id="status">3D 불러오는 중…</div><script src="https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js"></script><script>const data=DATA;
if(!window.THREE){document.querySelector('#status').textContent='3D 라이브러리 로딩 실패. 인터넷 연결 후 다시 열어주세요.'}else{
const T=THREE,scene=new T.Scene(),camera=new T.PerspectiveCamera(38,innerWidth/innerHeight,.1,3000),renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);renderer.setClearColor(0x101722);document.querySelector('#view').appendChild(renderer.domElement);camera.up.set(0,0,1);
const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g.computeVertexNormals();scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,metalness:.12,roughness:.48,side:T.DoubleSide})));scene.add(new T.HemisphereLight(0xe2f4ff,0x546781,2));const light=new T.DirectionalLight(0xffffff,2.5);light.position.set(100,-150,230);scene.add(light);const fill=new T.DirectionalLight(0xc7e1ff,1.5);fill.position.set(-100,100,-120);scene.add(fill);
let az=-1.1,el=.48,d=430,drag=false,x=0,y=0;function update(){camera.position.set(d*Math.cos(el)*Math.cos(az),d*Math.cos(el)*Math.sin(az),18+d*Math.sin(el));camera.lookAt(0,0,18);renderer.render(scene,camera)}renderer.domElement.onpointerdown=e=>{drag=true;x=e.clientX;y=e.clientY;renderer.domElement.setPointerCapture(e.pointerId)};renderer.domElement.onpointermove=e=>{if(!drag)return;az-=(e.clientX-x)*.007;el=Math.max(-1.56,Math.min(1.56,el+(e.clientY-y)*.007));x=e.clientX;y=e.clientY;update()};renderer.domElement.onpointerup=()=>drag=false;renderer.domElement.onpointercancel=()=>drag=false;renderer.domElement.addEventListener('wheel',e=>{e.preventDefault();d=Math.max(140,Math.min(1000,d*Math.exp(e.deltaY*.001)));update()},{passive:false});document.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{az=-Math.PI/2;el={angle:.48,top:1.56,side:0,bottom:-1.56}[b.dataset.v];d=430;update()});onresize=()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);update()};update();document.querySelector('#status').textContent='드래그로 회전 · 휠로 확대';}
</script></html>'''
(out/'assembly-preview.html').write_text(html.replace('DATA',json.dumps({'vertices':np.round(m.vertices,5).tolist(),'faces':m.faces.tolist()})))
print((out/'specs.json').read_text())
