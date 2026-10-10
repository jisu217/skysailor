import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {capGeometry,rotationArrow,updateRotationArrow} from './geometry.js';
const $=id=>document.getElementById(id);
for(const [key,label,value,min,max,step] of [['tilt','기울기 °',30,0,180,1],['azimuth','기울이는 방향 °',0,-180,180,1],['airspeed','상대풍속 m/s',1.6,0,15,.1]]){
 const row=document.createElement('div');row.className='slider-row';row.innerHTML=`<label>${label}<input type="number" name="${key}" value="${value}" min="${min}" max="${max}" step="${step}" required></label><input type="range" aria-label="${label} 슬라이더" id="${key}-slider" value="${value}" min="${min}" max="${max}" step="${step}">`;$('sliders').append(row);
 row.querySelector('input[type=range]').oninput=e=>{$('pose-form').elements[key].value=e.target.value;update();};row.querySelector('input[type=number]').oninput=e=>{$(key+'-slider').value=e.target.value;update();};
}
for(const [key,label,value,min,max] of [['shell_g','껍질 질량 g',4,.5,100],['ballast_g','무게추 질량 g',6,.5,100],['com_x_mm','무게중심 X mm',0,-100,100],['com_y_mm','무게중심 Y mm',0,-100,100],['com_z_mm','무게중심 Z mm',-40,-200,60]]){const labelNode=document.createElement('label');labelNode.innerHTML=`${label}<input type="number" name="${key}" value="${value}" min="${min}" max="${max}" step="any" required>`;if(key.startsWith('com_')){labelNode.querySelector('input').removeAttribute('min');labelNode.querySelector('input').removeAttribute('max');}$('numbers').append(labelNode);labelNode.querySelector('input').oninput=update;}
$('pose-form').onsubmit=e=>e.preventDefault();
const host=$('pose-view'),renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
const scene=new T.Scene();scene.background=new T.Color('#15222a');const camera=new T.PerspectiveCamera(42,1,.001,100);camera.up.set(0,0,1);const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;
function resetCamera(){camera.position.set(.48,-.68,.34);orbit.target.set(0,0,0);orbit.update();}resetCamera();$('camera').onclick=resetCamera;
scene.add(new T.HemisphereLight(0xe6fff5,0x3e4865,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(2,-3,5);scene.add(light);
const body=new T.Group();scene.add(body);body.add(new T.Mesh(capGeometry(),new T.MeshStandardMaterial({color:0x91d4bd,side:T.DoubleSide,roughness:.45,metalness:.12})));
body.add(new T.LineLoop(new T.BufferGeometry().setFromPoints(Array.from({length:96},(_,i)=>new T.Vector3(.12*Math.cos(i*Math.PI/48),.12*Math.sin(i*Math.PI/48),0))),new T.LineBasicMaterial({color:0xd7fff2})));
const com=new T.Mesh(new T.SphereGeometry(.004,16,12),new T.MeshBasicMaterial({color:0xff83bd,depthTest:false}));com.renderOrder=15;scene.add(com);
const grid=new T.GridHelper(.8,16,0x577782,0x2d434e);grid.rotation.x=Math.PI/2;grid.position.z=-.26;scene.add(grid);
for(const x of [-.23,.23]){const airflow=new T.ArrowHelper(new T.Vector3(0,0,1),new T.Vector3(x,.08,-.2),.30,0x52727e,.015,.008);scene.add(airflow);}
const colors={force:0x61e5ee,gravity:0xff967f,net:0xf3db83},arrows={};for(const [key,color] of Object.entries(colors)){const arrow=new T.ArrowHelper(new T.Vector3(0,0,1),new T.Vector3(),.1,color);for(const part of [arrow.line,arrow.cone]){part.material.depthTest=false;part.renderOrder=10;}scene.add(arrow);arrows[key]=arrow;}
const torque=rotationArrow(0xc9a0ff,.19);scene.add(torque.group);
let data=null,sequence=0;
function display(){if(!data)return;const vectors=Object.fromEntries(['force','gravity','net','torque','com'].map(k=>[k,new T.Vector3(...data[k])]));com.position.copy(vectors.com);const scale=Math.min(1.5,.28/Math.max(...Object.keys(arrows).map(k=>vectors[k].length()),1e-9));
 for(const [key,arrow] of Object.entries(arrows)){const v=vectors[key],length=v.length()*scale;arrow.visible=$('show-'+key).checked&&length>1e-8;arrow.position.copy(vectors.com);if(length>1e-8){arrow.setDirection(v.clone().normalize());arrow.setLength(length,Math.min(.018,length*.22),Math.min(.009,length*.12));}}
 updateRotationArrow(torque,vectors.torque,vectors.com,.78,$('show-torque').checked);
 $('scale').textContent=`힘 화살표 공통 배율: 100mN = ${(scale*10).toFixed(1)}cm`;
 $('readouts').innerHTML=[['force','공기력','#61e5ee','mN'],['gravity','중력','#ff967f','mN'],['net','합력','#f3db83','mN'],['torque','토크','#c9a0ff','mN·m']].map(([key,label,color,unit])=>`<div><small style="color:${color}">${label}</small><strong>${(vectors[key].length()*1000).toFixed(3)} <small>${unit}</small></strong><span class="vector">세계 X / Y / Z<br>${data[key].map(v=>(v*1000).toFixed(3)).join(' / ')}</span></div>`).join('');
 $('effect').textContent=`기울기 ${data.parameters.tilt}° · 상대풍속 ${data.parameters.airspeed} m/s · 위쪽 순힘 ${(data.net[2]*1000).toFixed(2)} mN (양수 ↑ / 음수 ↓). 토크 화살표는 회전을 유도하는 방향이며, 현재 회전 방향은 아닙니다.`;
}
async function update(){const id=++sequence;if(!$('pose-form').checkValidity()){$('status').textContent='입력 범위를 확인해주세요.';return;}const parameters=Object.fromEntries(new FormData($('pose-form')).entries());for(const key in parameters)parameters[key]=Number(parameters[key]);$('status').textContent='하중 계산 중…';try{const response=await fetch('/api/pose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(parameters)});const result=await response.json();if(id!==sequence)return;if(!response.ok)throw Error('하중 계산에 실패했습니다. 입력값을 확인해주세요.');data={...result,parameters};body.quaternion.setFromAxisAngle(new T.Vector3(0,0,1),T.MathUtils.degToRad(parameters.azimuth)).multiply(new T.Quaternion().setFromAxisAngle(new T.Vector3(0,1,0),T.MathUtils.degToRad(parameters.tilt)));display();$('status').textContent='자세를 바꾸면 즉시 다시 계산합니다.';}catch(error){if(id===sequence)$('status').textContent=error.message;}}
for(const key of ['force','gravity','net','torque'])$('show-'+key).onchange=display;
document.querySelectorAll('[data-angle]').forEach(button=>button.onclick=()=>{$('pose-form').elements.tilt.value=button.dataset.angle;$('tilt-slider').value=button.dataset.angle;update();});
new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();}).observe(host);
function animate(){orbit.update();renderer.render(scene,camera);requestAnimationFrame(animate);}animate();update();
