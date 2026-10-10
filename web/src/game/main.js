import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id),view=$('view');
const settingsKey='skysailor.game.settings.v1';
const settingIds=['preset','rate','lineLength','payloadMass','duration','mechanism','driveSpeed','clickAdvance','railMass','supportMass','railDrop','railLinear','railTorque','railAngular','stepInterval','padSpeed','strategy','strategyQuality','domeDiameter','domeMass'];
// Storage can be disabled by browser policy; gameplay still works in that case.
try {
 const saved=JSON.parse(localStorage.getItem(settingsKey)||'{}');
 for(const id of settingIds){
  const el=$(id),value=saved?.[id];
  if(el.type==='checkbox'){if(typeof value==='boolean')el.checked=value;continue;}
  if(typeof value!=='string')continue;
  if(el.tagName==='SELECT'){
   if([...el.options].some(option=>option.value===value))el.value=value;
  }else if(value.trim()!==''&&Number.isFinite(Number(value))&&Number(value)>=Number(el.min)&&Number(value)<=Number(el.max))el.value=value;
 }
}catch{}
function saveSettings(){
 const saved={};
 for(const id of settingIds){const el=$(id);if(el.type==='checkbox'){saved[id]=el.checked;continue;}if(el.value.trim()===''||!el.validity.valid)return;saved[id]=el.value;}
 try{localStorage.setItem(settingsKey,JSON.stringify(saved));}catch{}
}
for(const id of settingIds)$(id).addEventListener('change',saveSettings);

const scene=new THREE.Scene();scene.background=new THREE.Color('#101c24');scene.fog=new THREE.Fog('#101c24',5,22);
const camera=new THREE.PerspectiveCamera(45,1,.005,80);camera.up.set(0,0,1);camera.position.set(1.0,-2.2,3.85);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));view.appendChild(renderer.domElement);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.target.set(0,0,3);orbit.enableDamping=true;orbit.minDistance=.3;orbit.maxDistance=12;
scene.add(new THREE.HemisphereLight(0xe6fff1,0x354854,3));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(2,-3,6);scene.add(light);
const grid=new THREE.GridHelper(60,300,0x5c8989,0x29404d);grid.rotation.x=Math.PI/2;scene.add(grid);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(60,60),new THREE.MeshStandardMaterial({color:0x152b33,roughness:1}));floor.position.z=-.01;scene.add(floor);
// Fixed world landmarks: decorative balloons do not affect the flight dynamics.
const balloonColors=[0xf0aeac,0xdebde9,0xf0d78b,0x8bcbd5,0xa3d6b3];
const balloonGeo=new THREE.SphereGeometry(1,20,16);
const knotGeo=new THREE.ConeGeometry(.013,.025,8);knotGeo.rotateX(Math.PI/2);
for(let i=0;i<28;i++){
 const angle=i*2.399963, radius=1.25+Math.floor(i/6)*2.4;
 const x=Math.cos(angle)*radius,y=Math.sin(angle)*radius;
 const height=1.1+((i*7)%13)*.24,size=.09+(i%3)*.015;
 const material=new THREE.MeshStandardMaterial({color:balloonColors[i%5],roughness:.35,metalness:.05});
 const balloon=new THREE.Mesh(balloonGeo,material);balloon.scale.set(size,size,size*1.25);balloon.position.set(x,y,height);scene.add(balloon);
 const knot=new THREE.Mesh(knotGeo,material);knot.position.set(x,y,height-size*1.25-.008);scene.add(knot);
 const cord=new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(x,y,.015),new THREE.Vector3(x+.035,y-.02,height*.5),new THREE.Vector3(x,y,height-size*1.25)]),new THREE.LineBasicMaterial({color:0x637b80,transparent:true,opacity:.45}));scene.add(cord);
}
const origin=new THREE.Mesh(new THREE.RingGeometry(.08,.09,48),new THREE.MeshBasicMaterial({color:0x8aaeff,side:THREE.DoubleSide}));origin.position.z=.002;scene.add(origin);
let offlineReplay=false,strategyCalculating=false;
let pendingRewind=false,manualSteps=0;
let pendingReset=false,sentControl=[0,0];
let tape=[],liveData=null,replayMode=false,replayPlaying=false,replayTime=0,lastAnimation=0;
let meshes=[],lines=[],frame=null,playing=false,busy=false,ended=false,target=[0,0],lastCenter=null,preset='calm',timer;
const keys=new Set(),quat=new THREE.Quaternion();
const marker=color=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.004,12,8),new THREE.MeshBasicMaterial({color,depthTest:false}));m.renderOrder=5;scene.add(m);return m;};
const actual=marker(0xef8de0),desired=marker(0xffdf7e);
// Solid world-space wind vector: 1 m/s = 0.15 m, without a length cap.
const windArrow=new THREE.Group(),windAxis=new THREE.Vector3(0,1,0);
const windMaterial=new THREE.MeshStandardMaterial({color:0x7aaeff,roughness:.3,metalness:.15,emissive:0x18345b});
const windShaft=new THREE.Mesh(new THREE.CylinderGeometry(.022,.022,.76,16),windMaterial);windShaft.position.y=.38;
const windHead=new THREE.Mesh(new THREE.ConeGeometry(.075,.24,24),windMaterial);windHead.position.y=.88;
windArrow.add(windShaft,windHead);scene.add(windArrow);
function build(gs){
 for(const m of [...meshes,...lines]){scene.remove(m);m.geometry.dispose();m.material.dispose();}meshes=[];lines=[];
 meshes=gs.map((g,i)=>{let geo;
  if(g.triangles){geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(g.triangles.flat(),3));geo.computeVertexNormals();}
  else if(g.type===6)geo=new THREE.BoxGeometry(2*g.size[0],2*g.size[1],2*g.size[2]);
  else if(g.type===5){geo=new THREE.CylinderGeometry(g.size[0],g.size[0],2*g.size[1],16);geo.rotateX(Math.PI/2);}
  else if(g.type===3){geo=new THREE.CapsuleGeometry(g.size[0],2*g.size[1],4,12);geo.rotateX(Math.PI/2);}
  else geo=new THREE.SphereGeometry(g.size[0],16,12);
  const color=['C','H','P'].includes(frame.mechanism)?new THREE.Color().setRGB(...g.color.slice(0,3)):(i===gs.length-1?0xd7b777:0x70e4b0);
  const m=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,side:THREE.DoubleSide,roughness:.6,transparent:['C','H','P'].includes(frame.mechanism)&&!!g.triangles,opacity:(['C','H','P'].includes(frame.mechanism)&&g.triangles)?0.65:1,depthWrite:!(['C','H','P'].includes(frame.mechanism)&&g.triangles)}));
  scene.add(m);return m;
 });
 lines=Array.from({length:frame.tips.length},()=>{const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);const l=new THREE.Line(g,new THREE.LineBasicMaterial({color:0xb4d4cd}));scene.add(l);return l;});
}
function show(data){frame=data.frame;vertices=Array.from({length:frame.tips.length},(_,i)=>[Math.cos(i*2*Math.PI/frame.tips.length),Math.sin(i*2*Math.PI/frame.tips.length)]);if(data.geometry)build(data.geometry);ended=data.ended;
 meshes.forEach((m,i)=>{m.position.fromArray(frame.position[i]);const q=frame.quaternion[i];m.quaternion.set(q[1],q[2],q[3],q[0]);});
 lines.forEach((l,i)=>{const p=l.geometry.attributes.position;p.setXYZ(0,...frame.tips[i]);p.setXYZ(1,...frame.anchor);p.needsUpdate=true;l.geometry.computeBoundingSphere();l.material.color.setHex(frame.line_slack[i]?0x805b46:0xb4d4cd);});
 actual.position.fromArray(frame.anchor);const q=frame.quaternion[0];quat.set(q[1],q[2],q[3],q[0]);desired.position.set(frame.target_xy[0],frame.target_xy[1],-frame.hang).applyQuaternion(quat).add(new THREE.Vector3(...frame.center));
 const center=new THREE.Vector3(...frame.center);if(lastCenter){const delta=center.clone().sub(lastCenter);camera.position.add(delta);orbit.target.add(delta);}else{orbit.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(1.0,-2.2,.85));}lastCenter=center;
 const w=new THREE.Vector3(...frame.wind),mag=w.length();windArrow.visible=mag>0;windArrow.position.copy(center).add(new THREE.Vector3(0,0,-.4));if(mag>0){windArrow.quaternion.setFromUnitVectors(windAxis,w.divideScalar(mag));windArrow.scale.setScalar(mag*.15);}
 $('windReadout').textContent=`바람 ${mag.toFixed(2)} m/s · 1 m/s = 화살표 15cm${mag===0?' · 무풍':''}`;
 $('stats').innerHTML=`비행 <b>${frame.t.toFixed(2)} s</b> · 높이 ${frame.height.toFixed(2)} m<br>하강 ${frame.speed.toFixed(2)} m/s · 기울기 ${frame.tilt.toFixed(1)}°<br>바람 (${frame.wind.map(v=>v.toFixed(1)).join(', ')}) m/s<br>목표 (${(frame.target_xy[0]*1000).toFixed(0)}, ${(frame.target_xy[1]*1000).toFixed(0)}) mm<br>줄: ${frame.line_slack.map((s,i)=>frame.mechanism!=='A'?`${Math.abs(frame.winch_speed[i]*1000).toFixed(1)} mm/s`:frame.winch_stalled[i]?'부하 제한':s?'느슨함':'당김').join(' / ')}`;
 if(frame.rail)$('stats').innerHTML=$('stats').innerHTML.replace(/<br>줄:.*$/,'')+`<br>레일 ${(frame.rail.angle*180/Math.PI).toFixed(1)}° · 추 ${(frame.rail.radius*1000).toFixed(1)} mm` ;
 if(replayMode){$('status').textContent='리플레이 · 기록된 물리 상태 재생';}
 else if(ended){playing=false;keys.clear();$('status').textContent=`${data.termination==='ground'?'지면 도달':'10초 종료'} · ${frame.t.toFixed(2)}초 · ${data.max_tilt>90?'뒤집힘 발생':'뒤집힘 없음'} — R로 재도전`;}
 else $('status').textContent=playing?'직접 조종 중 · 자동 제어 OFF':'준비 / 일시정지 · Space로 시작';
 $('play').textContent=(replayMode?replayPlaying:playing)?'일시정지 · Space':'재생 · Space';drawPad();}
const socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/game`);
socket.onopen=()=>{$('play').disabled=false;if(!new URLSearchParams(location.search).has('replay'))reset();};socket.onclose=()=>{playing=false;$('status').textContent='연결 끊김 · 페이지를 새로고침하세요.';$('play').disabled=true;};socket.onerror=()=>{$('status').textContent='서버 연결 실패';};
socket.onmessage=e=>{busy=false;if(pendingReset){pendingReset=false;reset();return;}const data=JSON.parse(e.data);if(data.error){playing=false;$('status').textContent=data.error;return;}if(data.log_id){$('currentLog').hidden=false;$('currentLog').href='/api/game/logs/'+encodeURIComponent(data.log_id);}if(data.rewound){replayMode=false;replayPlaying=false;playing=false;target=[0,0];sentControl=[...target];$('duration').value=String(data.move_seconds);saveSettings();tape=tape.filter(f=>f.frame.t<data.frame.t-1e-9);$('live').disabled=true;} $('rewind').disabled=!(data.rewind_available>1e-8);$('rewindInfo').textContent=`되돌릴 수 있는 시간 ${data.rewind_available.toFixed(2)}초 / 최대 2초`;liveData=data;tape.push({...data,control:[...sentControl]});$('seek').max=data.frame.t;$('seek').disabled=tape.length<2;$('replay').disabled=tape.length<2;if(!replayMode)show(data);if(pendingRewind){pendingRewind=false;$('rewind').click();}else if(manualSteps>0){advanceOne();}else schedule();};
function reset(){if(document.body.classList.contains('embedded')||strategyCalculating)return;offlineReplay=false;$('advance').disabled=false;if($('mechanism').value==='C'&&['railMass','supportMass','railDrop','railLinear','railTorque','railAngular'].some(id=>!$(id).reportValidity()))return;if(!$('driveSpeed').reportValidity()||!$('lineLength').reportValidity()||!$('payloadMass').reportValidity())return;if(socket.readyState!==1)return;if(busy){pendingReset=true;playing=false;return;}clearTimeout(timer);manualSteps=0;pendingRewind=false;replayMode=false;replayPlaying=false;tape=[];liveData=null;$('seek').value=0;$('seek').disabled=true;$('replay').disabled=true;$('live').disabled=true;playing=false;ended=false;target=[0,0];keys.clear();lastCenter=null;preset=$('preset').value;busy=true;sentControl=[0,0];socket.send(JSON.stringify({kind:'reset',preset,mechanism:$('mechanism').value,drive_speed_mm_s:Number($('driveSpeed').value),line_length_mm:Number($('lineLength').value),payload_mass_g:Number($('payloadMass').value),dome_diameter_mm:Number($('domeDiameter').value),dome_mass_g:Number($('domeMass').value),rail_mass_g:Number($('railMass').value),support_mass_g:Number($('supportMass').value),rail_drop_mm:Number($('railDrop').value),rail_linear_mm_s:Number($('railLinear').value),rail_torque_mnm:Number($('railTorque').value),rail_angular_deg_s:Number($('railAngular').value)}));$('source').textContent=preset==='measured'?'Falkenberg 50m 실측 원본 · 약 3.3m/s부터. 3m 지상 바람 예측 아님. 시작 즉시 강풍을 맞습니다.':'약풍부터 감각을 익혀보세요. R은 같은 초기 조건과 바람으로 다시 시작합니다.';}
function schedule(){clearTimeout(timer);if(playing&&!ended)timer=setTimeout(tick,20/Number($('rate').value));}
function tick(){if(!playing||busy||ended||socket.readyState!==1)return;const dx=Number(keys.has('d'))-Number(keys.has('a')),dy=Number(keys.has('w'))-Number(keys.has('s'));target[0]=Math.max(-1,Math.min(1,target[0]+dx*.04));target[1]=Math.max(-1,Math.min(1,target[1]+dy*.04));busy=true;sentControl=[...target];socket.send(JSON.stringify({kind:'step',x:target[0],y:target[1],move_seconds:0,input_mode:'velocity',velocity_mm_s:Number($('padSpeed').value)}));}
function toggle(){if(strategyCalculating)return;if(replayMode){if(replayTime>=tape.at(-1).frame.t)replayTime=0;replayPlaying=!replayPlaying;renderReplay();return;}if(!frame||ended)return;playing=!playing;keys.clear();$('play').textContent=playing?'일시정지 · Space':'시작 · Space';$('status').textContent=playing?'직접 조종 중 · 자동 제어 OFF':'일시정지';schedule();}
$('play').onclick=toggle;$('reset').onclick=reset;$('preset').onchange=reset;$('center').onclick=()=>{if(!replayMode){target=[0,0];drawPad();}};
window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)||e.repeat)return;const k=e.key.toLowerCase();if(['arrowleft','arrowright','a','d'].includes(k)){e.preventDefault();if(replayMode){replayPlaying=false;replayTime=Math.max(0,Math.min(tape.at(-1).frame.t,replayTime+(['arrowright','d'].includes(k)?stepInterval():-stepInterval())));renderReplay();}else if(k==='arrowleft'||k==='a')$('rewind').click();else advanceTenth();return;}if(k===' '){e.preventDefault();toggle();}if(k==='r')reset();if(k==='c')$('center').click();});
window.addEventListener('blur',()=>{keys.clear();if(playing)toggle();replayPlaying=false;});
let vertices=Array.from({length:3},(_,i)=>[Math.cos(i*2*Math.PI/3),Math.sin(i*2*Math.PI/3)]);
function project(p){if(frame?.mechanism==='C'){const norm=Math.hypot(...p);return p.map(v=>v/Math.max(1,norm));}const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);if(vertices.every((a,i)=>cross(a,vertices[(i+1)%vertices.length],p)>=0))return p;let best=null,d=Infinity;vertices.forEach((a,i)=>{const b=vertices[(i+1)%vertices.length],v=[b[0]-a[0],b[1]-a[1]],t=Math.max(0,Math.min(1,((p[0]-a[0])*v[0]+(p[1]-a[1])*v[1])/(v[0]*v[0]+v[1]*v[1]))),q=[a[0]+t*v[0],a[1]+t*v[1]],dd=(q[0]-p[0])**2+(q[1]-p[1])**2;if(dd<d){d=dd;best=q;}});return best;}
const pad=$('pad'),ctx=pad.getContext('2d');let dragging=false;
let padBasis=[1,0,0,-1],padEditable=true;
function updatePadBasis(){
 if(!frame)return;
 const q=frame.quaternion[0],body=new THREE.Quaternion(q[1],q[2],q[3],q[0]);
 const x=new THREE.Vector3(1,0,0).applyQuaternion(body),y=new THREE.Vector3(0,1,0).applyQuaternion(body);
 const right=new THREE.Vector3(1,0,0).applyQuaternion(camera.quaternion),up=new THREE.Vector3(0,1,0).applyQuaternion(camera.quaternion);
 padBasis=[x.dot(right),y.dot(right),-x.dot(up),-y.dot(up)];
 padEditable=Math.abs(padBasis[0]*padBasis[3]-padBasis[1]*padBasis[2])>.08;
}
const screen=p=>[150+95*(padBasis[0]*p[0]+padBasis[1]*p[1]),115+95*(padBasis[2]*p[0]+padBasis[3]*p[1])];
function pointer(e){if(strategyCalculating||replayMode||!padEditable)return false;const r=pad.getBoundingClientRect(),sx=((e.clientX-r.left)/r.width*300-150)/95,sy=((e.clientY-r.top)/r.height*230-115)/95;const [a,b,c,d]=padBasis,det=a*d-b*c;target=[(d*sx-b*sy)/det,(-c*sx+a*sy)/det];const norm=Math.hypot(...target);target=norm<.03?[0,0]:target.map(v=>v/Math.max(1,norm));drawPad();return true;}
pad.onpointerdown=e=>{if(replayMode)return;if($('clickAdvance').checked){if(busy||manualSteps>0)return;if(pointer(e))advanceTenth();return;}dragging=true;pad.setPointerCapture(e.pointerId);pointer(e);};pad.onpointermove=e=>{if(dragging)pointer(e);};pad.onpointerup=pad.onpointercancel=()=>{dragging=false;};
function drawPad(){updatePadBasis();ctx.clearRect(0,0,300,230);if(!padEditable){ctx.fillStyle='#ffe084';ctx.font='11px system-ui';ctx.fillText('옆면 시점 · 카메라를 돌려 조작하세요',12,220);}ctx.fillStyle='#ffe084';ctx.font='11px system-ui';ctx.fillText(`속도 지령 ${(Math.hypot(...target)*Number($('padSpeed').value)).toFixed(1)} mm/s`,12,18);ctx.lineWidth=1.5;ctx.strokeStyle='#507581';ctx.fillStyle='#142d37';ctx.beginPath();vertices.forEach((v,i)=>ctx[i?'lineTo':'moveTo'](...screen(v)));ctx.closePath();ctx.fill();ctx.stroke();const goal=screen(target);ctx.beginPath();ctx.moveTo(...screen([0,0]));ctx.lineTo(...goal);ctx.strokeStyle='#ffe084';ctx.stroke();if(frame?.rail){ctx.beginPath();for(let i=0;i<=64;i++){const a=i*Math.PI/32;ctx[i?'lineTo':'moveTo'](...screen([Math.cos(a),Math.sin(a)]));}ctx.strokeStyle='#8eaeba';ctx.stroke();const theta=frame.rail.angle;ctx.beginPath();ctx.moveTo(...screen([-Math.cos(theta),-Math.sin(theta)]));ctx.lineTo(...screen([Math.cos(theta),Math.sin(theta)]));ctx.strokeStyle='#f3aa50';ctx.lineWidth=4;ctx.stroke();ctx.lineWidth=1.5;}vertices.forEach((v,i)=>{const p=screen(v);ctx.strokeStyle='#ffe08488';ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...goal);ctx.stroke();ctx.fillStyle='#d8eee8';ctx.font='12px system-ui';ctx.fillText(String(i+1),p[0]+(i===0?8:-18),p[1]+4);});const dot=(p,color,r)=>{ctx.fillStyle=color;ctx.beginPath();ctx.arc(...screen(p),r,0,Math.PI*2);ctx.fill();};dot(target,'#ffe084',6);if(frame){dot(frame.target_xy.map(v=>v/(frame.control_radius||.12)),'#83eac0',4);dot(frame.payload_local.slice(0,2).map(v=>v/(frame.control_radius||.12)),'#ef8de0',4);if(frame.rail){const r=frame.rail;$('lengths').innerHTML=`레일 각도 ${(r.angle*180/Math.PI).toFixed(1)}° · 추 위치 ${(r.radius*1000).toFixed(1)} mm<br>회전 ${(r.angular_velocity*180/Math.PI).toFixed(1)}°/s · 직선 ${(r.linear_velocity*1000).toFixed(1)} mm/s<br>회전 토크 ${(r.torque*1000).toFixed(3)} mN·m · 축 기준 관성 ${r.axial_inertia.toExponential(2)} kg·m²`;return;}const lengths=vertices.map(v=>1000*Math.hypot(v[0]*.12-frame.target_xy[0],v[1]*.12-frame.target_xy[1],frame.hang));$('lengths').innerHTML='줄 &nbsp; 최종 목표 / 현재 실제 길이 (mm)<br>'+lengths.map((l,i)=>`${i+1} &nbsp; ${l.toFixed(1)} / ${(frame.line_actual[i]*1000).toFixed(1)}`).join(' &nbsp; · &nbsp; ');}}
function renderReplay(){if(!tape.length)return;let item=tape[0];for(const f of tape){if(f.frame.t>replayTime+1e-9)break;item=f;}target=[...item.control];show(item);$('seek').value=replayTime;$('replayTime').textContent=`다시보기 ${replayTime.toFixed(2)} / ${tape.at(-1).frame.t.toFixed(2)}초`;}
function enterReplay(){if(tape.length<2)return false;playing=false;clearTimeout(timer);keys.clear();replayMode=true;$('live').disabled=false;return true;}
$('replay').onclick=()=>{if(enterReplay()){replayTime=0;replayPlaying=true;renderReplay();}};
$('seek').oninput=()=>{if(enterReplay()){replayPlaying=false;replayTime=Number($('seek').value);renderReplay();}};
$('live').onclick=()=>{if(offlineReplay){reset();return;}replayMode=false;replayPlaying=false;playing=false;$('live').disabled=true;if(liveData){target=[...(tape.at(-1).control)];show(liveData);}$('replayTime').textContent=' 조종 복귀 · 마지막 물리 상태에서 일시정지';};
function resize(){camera.aspect=view.clientWidth/view.clientHeight;camera.updateProjectionMatrix();renderer.setSize(view.clientWidth,view.clientHeight);}window.addEventListener('resize',resize);resize();drawPad();function animate(now=0){requestAnimationFrame(animate);if(replayMode&&replayPlaying){replayTime=Math.min(tape.at(-1).frame.t,replayTime+Math.min(.1,(now-lastAnimation)/1000)*Number($('rate').value));if(replayTime>=tape.at(-1).frame.t)replayPlaying=false;renderReplay();}lastAnimation=now;orbit.update();drawPad();renderer.render(scene,camera);}animate();

async function refreshLogs(){
 const box=$('savedLogs');box.textContent='불러오는 중…';
 try{const response=await fetch('/api/game/logs');if(!response.ok)throw Error();const logs=await response.json();box.replaceChildren();for(const log of logs){const a=document.createElement('a');a.href='/api/game/logs/'+encodeURIComponent(log.id);a.textContent=log.id+' · '+(log.bytes/1024).toFixed(1)+' KB';a.style.cssText='display:block;overflow-wrap:anywhere;margin:8px 0;font-size:11px';box.appendChild(a);}if(!logs.length)box.textContent='저장된 로그가 없습니다.';}catch{box.textContent='목록을 불러오지 못했습니다. 다시 시도해주세요.'}
}
$('refreshLogs').onclick=refreshLogs;$('logHistory').ontoggle=()=>{if($('logHistory').open)refreshLogs();};

$('rewind').onclick=()=>{if(offlineReplay||strategyCalculating)return;manualSteps=0;if(!liveData||socket.readyState!==1)return;if(busy){pendingRewind=true;playing=false;clearTimeout(timer);return;}playing=false;replayPlaying=false;clearTimeout(timer);keys.clear();busy=true;socket.send(JSON.stringify({kind:'rewind',interval_s:stepInterval()}));};

function updateMechanism(){const rail=$('mechanism').value==='C',planar=$('mechanism').value!=='A';$('railSettings').hidden=!rail;$('driveSpeed').parentElement.hidden=rail;$('freeInfo').hidden=planar;$('lineLength').parentElement.hidden=planar;$('duration').parentElement.hidden=true;$('duration').disabled=true;$('lineLength').disabled=planar;$('mechanismInfo').textContent=rail?'회전 레일: 패드에서 이동 방향과 속도를 지정하세요. 회전 관성·모터 토크 한도와 추의 직선 속도 제한을 적용합니다.':planar?'평면 구속: 줄 속도 상한만 적용합니다. 가감속·힘 제한 없이 이동하며, 실제 줄 장력은 계산하지 않습니다. 기본 길이와 목표 이동 시간은 사용하지 않습니다.':'기존 자유 추 모델: 줄 탄성·모터 당김 힘 제한을 적용합니다.';}
$('mechanism').addEventListener('change',()=>{updateMechanism();reset();});updateMechanism();

function advanceOne(){const dt=Math.min(.02,manualSteps);manualSteps=Math.max(0,Number((manualSteps-dt).toFixed(3)));if(!liveData||ended||socket.readyState!==1){manualSteps=0;return;}busy=true;sentControl=[...target];socket.send(JSON.stringify({kind:'step',interval_s:dt,x:target[0],y:target[1],move_seconds:0,input_mode:'velocity',velocity_mm_s:Number($('padSpeed').value)}));}
function advanceTenth(){if(offlineReplay||strategyCalculating)return;if(!$('stepInterval').reportValidity()||!$('padSpeed').reportValidity())return;if(replayMode||!liveData||ended||socket.readyState!==1)return;playing=false;replayPlaying=false;clearTimeout(timer);keys.clear();manualSteps=Number((manualSteps+stepInterval()).toFixed(3));if(!busy){advanceOne();}}
$('advance').onclick=advanceTenth;

$('closeView').onclick=()=>{if(!frame)return;const center=new THREE.Vector3(...frame.center);orbit.target.copy(center).add(new THREE.Vector3(0,0,-frame.hang/2));camera.position.copy(orbit.target).add(new THREE.Vector3(.35,-.65,.22));orbit.update();};

function stepInterval(){const n=Number($('stepInterval').value);return Number.isFinite(n)&&n>=.01&&n<=2?Math.round(n*100)/100:.1;}
function updateStepLabels(){const t=stepInterval();$('advance').textContent=`${t}초 진행 · D / →`;$('rewind').textContent=`← / A · ${t}초 되돌리기`;$('clickStepLabel').textContent=`패드 클릭 시 ${t}초 진행`;}
$('stepInterval').addEventListener('change',updateStepLabels);$('stepInterval').addEventListener('input',()=>{updateStepLabels();saveSettings();});$('padSpeed').addEventListener('input',saveSettings);updateStepLabels();

const strategyJobKey='skysailor.strategy.job';
function strategyName(s){return s==='mpc'?'예측 제어 MPC v1':'추 중앙 고정';}
function setStrategyBusy(value){strategyCalculating=value;$('runStrategy').disabled=value;$('reset').disabled=value;$('mechanism').disabled=value;$('preset').disabled=value;}
async function apiJson(url,options){const r=await fetch(url,options);const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'요청을 처리하지 못했습니다. 설정값을 확인해주세요.');return d;}
async function loadStrategy(id){
 if(busy||strategyCalculating)throw Error('진행 중인 계산이 끝난 뒤 다시보기를 여세요.');
 const result=await apiJson('/api/game/strategies/'+id+'/result');
 playing=false;clearTimeout(timer);manualSteps=0;pendingRewind=false;keys.clear();offlineReplay=true;lastCenter=null;
 tape=result.frames.map((frame,i)=>({frame,geometry:i===0?result.geometry:undefined,control:[0,0],ended:i===result.frames.length-1,max_tilt:result.summary.max_tilt_deg,termination:result.summary.termination}));
 replayMode=true;replayPlaying=false;replayTime=0;$('seek').max=tape.at(-1).frame.t;$('seek').value=0;$('seek').disabled=false;$('replay').disabled=false;$('live').disabled=false;$('rewind').disabled=true;$('advance').disabled=true;
 $('rewindInfo').textContent='자동 비행 다시보기 · A/D 또는 시간 막대로 이동';
 $('currentLog').hidden=false;$('currentLog').href='/api/game/strategies/'+id+'/result';
 const s=result.summary,p=result.settings;
 $('strategySummary').textContent=`${(result.agent_name||strategyName(result.strategy))} · ${result.quality==='fine'?'정밀':'빠른'} 계산 / ${s.duration_s.toFixed(2)}초 (${s.termination==='ground'?'착지':'시간 한도'}) · 최대 기울기 ${s.max_tilt_deg.toFixed(1)}° · 평균 하강 ${s.mean_descent_m_s.toFixed(2)}m/s · 계산 ${s.wall_seconds.toFixed(1)}초. 추 ${p.payload_mass_g}g / 바람 ${p.wind_mode} / 직선 ${p.rail_linear_mm_s}mm/s`;
 $('source').textContent=`저장된 C 레일 비행 · 지름 ${result.frames[0].dome_diameter_mm||240}mm / 깊이 ${result.frames[0].dome_depth_mm||60}mm. 380mm 공기력은 잠정 환산입니다. 새 낙하로 직접 조종에 돌아갑니다.`;
 renderReplay();
}
async function refreshStrategies(){try{const rows=await apiJson('/api/game/strategies');const box=$('strategyHistory');box.replaceChildren();for(const r of rows){const b=document.createElement('button');b.textContent=`${r.diameter_mm||240}mm · ${r.agent_name||strategyName(r.strategy)} · ${r.quality==='fine'?'정밀':'빠른'} · ${r.summary.duration_s.toFixed(2)}초 다시보기`;b.onclick=()=>loadStrategy(r.id).catch(e=>$('strategyStatus').textContent=e.message);box.append(b);}if(!rows.length)box.textContent='저장된 결과 없음';}catch(e){$('strategyStatus').textContent=e.message;}}
async function watchStrategy(id){
 setStrategyBusy(true);
 try{const job=await apiJson('/api/game/strategies/'+id);
  if(job.status==='failed')throw Error(job.error||'계산 실패');
  if(job.status==='complete'){setStrategyBusy(false);try{localStorage.removeItem(strategyJobKey);}catch{}$('strategyStatus').textContent='계산 완료 · 재생 버튼으로 비행을 확인하세요.';await refreshStrategies();await loadStrategy(id);return;}
  $('strategyStatus').textContent=`계산 중 · 비행 ${job.time_s.toFixed(2)} / 최대 ${job.seconds}초 (착지하면 종료)`;
  setTimeout(()=>watchStrategy(id),1000);
 }catch(e){setStrategyBusy(false);$('strategyStatus').textContent=e.message;}
}
$('runStrategy').onclick=async()=>{
 if(busy){$('strategyStatus').textContent='현재 물리 계산이 끝난 뒤 다시 눌러주세요.';playing=false;clearTimeout(timer);return;}
 if($('mechanism').value!=='C'){$('strategyStatus').textContent='기체 모델을 C · 회전 레일 + 추로 선택해주세요.';return;}
 if(['domeMass','payloadMass','railMass','supportMass','railDrop','railLinear','railTorque','railAngular'].some(id=>!$(id).reportValidity()))return;
 playing=false;replayPlaying=false;clearTimeout(timer);manualSteps=0;keys.clear();setStrategyBusy(true);
 const parameters={variant:'B',mechanism:'C',seconds:10,height:3,tilt:5,seed:0,wind_mode:{calm:'constant',gust:'gust',measured:'measured'}[$('preset').value],wind_x:$('preset').value==='gust'?.2:0,payload_mass_g:Number($('payloadMass').value),dome_diameter_mm:Number($('domeDiameter').value),dome_mass_g:Number($('domeMass').value),rail_mass_g:Number($('railMass').value),support_mass_g:Number($('supportMass').value),rail_drop_mm:Number($('railDrop').value),rail_linear_mm_s:Number($('railLinear').value),rail_torque_mnm:Number($('railTorque').value),rail_angular_deg_s:Number($('railAngular').value)};
 try{const job=await apiJson('/api/game/strategies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({strategy:$('strategy').value,quality:$('strategyQuality').value,parameters})});try{localStorage.setItem(strategyJobKey,job.id);}catch{}watchStrategy(job.id);}catch(e){setStrategyBusy(false);$('strategyStatus').textContent=e.message;}
};
$('refreshStrategies').onclick=refreshStrategies;refreshStrategies();
try{const id=localStorage.getItem(strategyJobKey);if(id&&!new URLSearchParams(location.search).has('replay'))watchStrategy(id);}catch{}

$('domeDiameter').addEventListener('change',()=>{$('domeMass').value=$('domeDiameter').value==='380'?'25':'4.2';saveSettings();reset();});

const challengeReplay=new URLSearchParams(location.search).get('replay');if(challengeReplay&&/^[a-f0-9]{32}$/.test(challengeReplay))loadStrategy(challengeReplay).then(()=>{if(new URLSearchParams(location.search).has('embed'))$('replay').click()}).catch(e=>$('strategyStatus').textContent=e.message);

if(new URLSearchParams(location.search).has('embed')){document.body.append(document.querySelector('.replay'));document.body.append($('stats'));window.dispatchEvent(new Event('resize'));}
