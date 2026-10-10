import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id);
const scenes=[];let result=null,time=0,playing=false,busy=false;
import {capGeometry,rotationArrow,updateRotationArrow} from './geometry.js';
for(const id of ['world','detail']){
 const host=$(id),renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.appendChild(renderer.domElement);
 const scene=new T.Scene();scene.background=new T.Color('#15222a');const camera=new T.PerspectiveCamera(42,1,.001,100);camera.up.set(0,0,1);
 const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
 scene.add(new T.HemisphereLight(0xe6fff5,0x3e4865,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(2,-3,5);scene.add(light);
 const group=new T.Group();scene.add(group);
 group.add(new T.Mesh(capGeometry(),new T.MeshStandardMaterial({color:0x91d4bd,metalness:.12,roughness:.45,side:T.DoubleSide})));
 const ring=new T.LineLoop(new T.BufferGeometry().setFromPoints(Array.from({length:96},(_,i)=>new T.Vector3(.12*Math.cos(i*Math.PI/48),.12*Math.sin(i*Math.PI/48),0))),new T.LineBasicMaterial({color:0xd7fff2}));group.add(ring);
 const ballast=new T.Mesh(new T.SphereGeometry(.008,24,16),new T.MeshStandardMaterial({color:0xf3bc76,metalness:.6,roughness:.25}));group.add(ballast);
 const support=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(0,0,.03),new T.Vector3()]),new T.LineBasicMaterial({color:0x8c9fa2}));group.add(support);
 const com=new T.Mesh(new T.SphereGeometry(.004,16,12),new T.MeshBasicMaterial({color:0xff83bd,depthTest:false}));com.renderOrder=5;group.add(com);
 const force=new T.ArrowHelper(new T.Vector3(0,0,1),new T.Vector3(),.1,0x61e5ee,.015,.008);scene.add(force);
 const extraArrows={};
 for(const [name,color] of [['gravity',0xff967f],['net',0xf3db83]]){extraArrows[name]=new T.ArrowHelper(new T.Vector3(0,0,1),new T.Vector3(),.1,color);scene.add(extraArrows[name]);}
 for(const arrow of [force,...Object.values(extraArrows)]){for(const part of [arrow.line,arrow.cone]){part.material.depthTest=false;part.material.transparent=true;part.material.opacity=.95;part.renderOrder=10;}}
 const rotations={};
 for(const [name,color,radius] of [['torque_aero',0xc9a0ff,.14],['torque_damping',0xff9ac5,.16],['torque',0xffffff,.18],['angular_velocity',0x93b7ff,.20]]){rotations[name]=rotationArrow(color,radius);scene.add(rotations[name].group);}
 const grid=new T.GridHelper(8,40,0x577782,0x2d434e);grid.rotation.x=Math.PI/2;scene.add(grid);
 const track=new T.Line(new T.BufferGeometry(),new T.LineBasicMaterial({color:0x8bcbba,transparent:true,opacity:.65}));scene.add(track);
 const item={id,host,scene,camera,controls,renderer,group,com,ballast,support,force,...extraArrows,rotations,grid,track,lastCenter:new T.Vector3()};scenes.push(item);
 new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(host);
}
function resetCamera(){
 const h=result?.parameters.height||3;
 for(const s of scenes){const c=s.id==='world'?new T.Vector3(0,0,h/2):s.group.position.clone();s.controls.target.copy(c);s.camera.position.copy(c).add(s.id==='world'?new T.Vector3(h*.5,-h*1.7,h*.45):new T.Vector3(.38,-.48,.22));s.lastCenter.copy(s.group.position);s.controls.update();}
}
function frameAt(t){
 const fs=result.frames;let low=0,high=fs.length-1;while(low<high){const mid=Math.ceil((low+high)/2);if(fs[mid].t<=t)low=mid;else high=mid-1;}
 const a=fs[low],b=fs[Math.min(low+1,fs.length-1)],mix=b.t>a.t?(t-a.t)/(b.t-a.t):0;return {a,b,mix};
}
function display(){
 if(!result)return;const {a,b,mix}=frameAt(time);const lerp=(k)=>new T.Vector3(...a[k]).lerp(new T.Vector3(...b[k]),mix);
 const q=new T.Quaternion(a.quaternion[1],a.quaternion[2],a.quaternion[3],a.quaternion[0]).slerp(new T.Quaternion(b.quaternion[1],b.quaternion[2],b.quaternion[3],b.quaternion[0]),mix);
 for(const s of scenes){s.group.position.copy(lerp('position'));s.group.quaternion.copy(q);
  if(s.id==='detail'){const delta=s.group.position.clone().sub(s.lastCenter);s.camera.position.add(delta);s.controls.target.add(delta);s.lastCenter.copy(s.group.position);}
  const f=lerp('force'),g=new T.Vector3(0,0,-(result.parameters.shell_g+result.parameters.ballast_g)/1000*9.81),net=f.clone().add(g);
  const scale=Math.min(1.5,.25/Math.max(f.length(),g.length(),net.length(),1e-9));
  for(const [name,vector,toggle] of [['force',f,'show-aero'],['gravity',g,'show-gravity'],['net',net,'show-net']]){
   const arrow=s[name],length=vector.length()*scale;arrow.visible=s.id==='detail'&&$(toggle).checked&&length>1e-7;arrow.position.copy(lerp('com'));
   if(length>1e-7){arrow.setDirection(vector.clone().normalize());arrow.setLength(length,Math.min(.014,length*.25),Math.min(.007,length*.12));}
  }
  for(const [name,toggle] of [['torque_aero','show-torque-aero'],['torque_damping','show-torque-damping'],['torque','show-torque'],['angular_velocity','show-spin']]){
   const vector=lerp(name);updateRotationArrow(s.rotations[name],vector,lerp('com'),name==='angular_velocity'?.7:vector.length()/result.torqueDisplayMax,s.id==='detail'&&$(toggle).checked);
  }
  if(s.id==='detail'){
   $('torque-values').textContent=`토크 mN·m: 공기 ${ (lerp('torque_aero').length()*1000).toFixed(3)} · 감쇠 ${(lerp('torque_damping').length()*1000).toFixed(3)} · 총 ${(lerp('torque').length()*1000).toFixed(3)}`;
   $('spin-values').textContent=`각속도 ${(lerp('angular_velocity').length()*180/Math.PI).toFixed(1)}°/s · 중력 토크 0`;
   $('torque-scale').textContent=`토크 호 길이: 288° = ${(result.torqueDisplayMax*1000).toFixed(3)} mN·m · 궤적 전체 고정 배율`;
  }
  if(s.id==='detail'){$('force-values').textContent=`공기력 ${(f.length()*1000).toFixed(1)} · 중력 ${(g.length()*1000).toFixed(1)} · 합력 ${(net.length()*1000).toFixed(1)} mN`;$('force-scale').textContent=`무게중심 기준 · 100mN = ${(scale*10).toFixed(1)}cm · 합력 = 공기력 + 중력`;}

 }
 const interp=k=>a[k]+(b[k]-a[k])*mix;
 $('height').textContent=lerp('com').z.toFixed(2)+' m';$('speed').textContent=interp('speed').toFixed(2)+' m/s';$('tilt').textContent=interp('tilt').toFixed(1)+'°';
 const p=lerp('com'),first=result.frames[0].com;$('distance').textContent=Math.hypot(p.x-first[0],p.y-first[1]).toFixed(2)+' m';$('clock').textContent=time.toFixed(2)+' s';$('seek').value=time;drawChart();
}
function drawChart(){
 if(!result)return;const canvas=$('chart'),w=canvas.clientWidth,h=130;canvas.width=w*devicePixelRatio;canvas.height=h*devicePixelRatio;const ctx=canvas.getContext('2d');ctx.scale(devicePixelRatio,devicePixelRatio);
 const fs=result.frames,d=result.summary.duration,hmax=Math.max(...fs.map(f=>f.com[2]),.1);const left=8,right=w-12,top=25,bottom=110;
 ctx.font='11px system-ui';ctx.fillStyle='#90d8ba';ctx.fillText('높이  '+hmax.toFixed(1)+' → 0 m',left,13);ctx.fillStyle='#e8b887';ctx.fillText('기울기  0 → 180°',Math.max(150,w/2),13);
 for(const [color,fn] of [['#90d8ba',f=>f.com[2]/hmax],['#e8b887',f=>f.tilt/180]]){ctx.strokeStyle=color;ctx.beginPath();fs.forEach((f,i)=>{const x=left+f.t/d*(right-left),y=bottom-fn(f)*(bottom-top);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();}
 ctx.strokeStyle='#bacbd1';const x=left+time/d*(right-left);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();ctx.fillStyle='#9bacb5';ctx.fillText('0 s',left,127);ctx.fillText(d.toFixed(2)+' s',right-40,127);
}
async function run(){
 if(busy||!$('form').reportValidity())return;busy=true;playing=false;$('run').disabled=true;$('status').textContent='낙하 궤적을 계산하고 있습니다…';
 try{const parameters=Object.fromEntries([...new FormData($('form'))].map(([k,v])=>[k,Number(v)]));const response=await fetch('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(parameters)});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));result=data;result.torqueDisplayMax=Math.max(1e-9,...data.frames.flatMap(f=>['torque_aero','torque_damping','torque'].map(k=>Math.hypot(...f[k]))));window.capResult=data;time=0;
 for(const s of scenes){s.ballast.position.set(...data.ballast_body);s.com.position.set(parameters.com_x_mm/1000,parameters.com_y_mm/1000,parameters.com_z_mm/1000);s.support.geometry.dispose();s.support.geometry=new T.BufferGeometry().setFromPoints([new T.Vector3(0,0,.03),new T.Vector3(...data.ballast_body)]);s.track.geometry.dispose();s.track.geometry=new T.BufferGeometry().setFromPoints(data.frames.map(f=>new T.Vector3(...f.com)));s.track.visible=s.id==='world';}
 $('seek').max=data.summary.duration;$('status').textContent='계산 완료 · 입력을 바꾼 뒤 다시 실행하세요.';$('summary').textContent=`${data.summary.duration.toFixed(2)}초 · ${data.summary.termination==='ground'?'지면 도달 — 충돌 전 종료':'설정 시간 종료'} · 총 질량 ${(parameters.shell_g+parameters.ballast_g).toFixed(1)}g · 감쇠 ${data.rotation_damping.enabled?"켜짐":"꺼짐"} · 최대 각속도 ${data.summary.peak_spin_deg_s.toFixed(0)}°/s`;
 $('warning').hidden=data.summary.peak_rotation_ratio<.2;$('warning').textContent=data.rotation_damping.enabled?'회전 감쇠는 60° 부근 시험값을 다른 자세에 확장한 근사입니다. 회전이 큰 구간의 궤적과 뒤집힘은 정성적으로 보세요.':'회전 감쇠를 끈 정적 모델입니다. 빠른 뒤집힘의 속도와 횟수는 정성적으로 보세요.';
 display();resetCamera();playing=true;$('play').textContent='일시정지';
 }catch(e){$('status').textContent='실행 실패: '+e.message;}finally{busy=false;$('run').disabled=false;}
}
for(const id of ['show-aero','show-gravity','show-net','show-torque-aero','show-torque-damping','show-torque','show-spin'])$(id).onchange=display;
$('form').elements.rotation_damping.onchange=run;
$('form').onsubmit=e=>{e.preventDefault();run();};$('play').onclick=()=>{if(!result)return;if(time>=result.summary.duration)time=0;playing=!playing;$('play').textContent=playing?'일시정지':'재생';};$('seek').oninput=()=>{playing=false;time=Number($('seek').value);$('play').textContent='재생';display();};$('resetCamera').onclick=resetCamera;
document.querySelectorAll('[data-com]').forEach(b=>b.onclick=()=>{b.dataset.com.split(',').forEach((v,i)=>$('form').elements[['com_x_mm','com_y_mm','com_z_mm'][i]].value=v);run();});
$('download').onclick=()=>{if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='cap-drop.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
for(const [key,value] of new URLSearchParams(location.search)){const input=$('form').elements[key];if(input&&Number.isFinite(Number(value)))input.value=value;}
let last=performance.now();function animate(now){const dt=Math.min((now-last)/1000,.1);last=now;if(result&&playing){time=Math.min(time+dt*Number($('rate').value),result.summary.duration);if(time>=result.summary.duration){playing=false;$('play').textContent='다시 재생';}display();}for(const s of scenes){s.controls.update();s.renderer.render(s.scene,s.camera);}requestAnimationFrame(animate);}resetCamera();requestAnimationFrame(animate);run();
