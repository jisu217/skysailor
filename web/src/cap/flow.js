import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {capGeometry,rotationArrow,updateRotationArrow} from './geometry.js';
const $=id=>document.getElementById(id),host=$('flow-view');
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
const scene=new T.Scene();scene.background=new T.Color('#15222a');const camera=new T.PerspectiveCamera(42,1,.001,20);camera.up.set(0,0,1);const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;
const root=new T.Group();scene.add(root);scene.add(new T.HemisphereLight(0xe6fff5,0x3e4865,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(2,-3,5);scene.add(light);
const shell=new T.Mesh(capGeometry(),new T.MeshStandardMaterial({color:0x91d4bd,side:T.DoubleSide,roughness:.5,transparent:true,opacity:.8,depthWrite:false}));root.add(shell);
const torqueArrow=rotationArrow(0xd5a4ff,.19);root.add(torqueArrow.group);torqueArrow.group.visible=false;
const comMarker=new T.Mesh(new T.SphereGeometry(.004,12,8),new T.MeshBasicMaterial({color:0xff83bd,depthTest:false}));comMarker.renderOrder=20;root.add(comMarker);
function showTorque(){
 if(!metadata||!manifest)return;
 const inputs=['com-x','com-y','com-z'].map(id=>$(id));if(inputs.some(input=>input.value===''||!input.checkValidity()))return;
 const com=new T.Vector3(...inputs.map(input=>Number(input.value)/1000));
 const moment=row=>new T.Vector3(...row.torque_origin_body_Nm).sub(new T.Vector3().crossVectors(com,new T.Vector3(...row.force_body_N)));
 const vector=moment(metadata),max=Math.max(1e-12,...manifest.cases.map(row=>moment(row).length()));
 // Common scale across all saved angles at the selected COM, with no per-angle clipping.
 updateRotationArrow(torqueArrow,vector,com,vector.length()/max,$('show-torque').checked);
 comMarker.position.copy(com);comMarker.visible=$('show-torque').checked;
 const world=vector.clone().applyAxisAngle(new T.Vector3(0,1,0),metadata.angle*Math.PI/180);
 $('torque-readout').innerHTML=`무게중심 기준 토크 <strong>${(vector.length()*1000).toFixed(4)} mN·m</strong><br>세계 X / Y / Z: ${world.toArray().map(x=>(x*1000).toFixed(4)).join(' / ')} mN·m<br>보라색 호 길이 ∝ 토크 · 반지름 19cm 고정 · ${(max*1000).toFixed(4)} mN·m = 288° 호<br>7개 각도 공통 배율 (무게중심 변경 시 재설정) · 분홍 점: 무게중심<br>표시 중인 유동장과 같은 반복 ${metadata.iteration}의 표면 합산 토크입니다. 중력·회전 감쇠 토크는 0으로 가정합니다.`;
}
for(const id of ['show-torque','com-x','com-y','com-z'])$(id).oninput=showTorque;
const capacity=6000,material=new T.MeshBasicMaterial({color:0xffffff});
const stems=new T.InstancedMesh(new T.CylinderGeometry(.0008,.0008,1,5),material,capacity),heads=new T.InstancedMesh(new T.ConeGeometry(.003,1,7),material,capacity);
for(const mesh of [stems,heads]){mesh.count=0;mesh.frustumCulled=false;mesh.instanceMatrix.setUsage(T.DynamicDrawUsage);root.add(mesh);}
const marker=new T.Mesh(new T.SphereGeometry(.004,12,8),new T.MeshBasicMaterial({color:0xffff88,depthTest:false}));marker.renderOrder=20;marker.visible=false;root.add(marker);
const inflow=new T.ArrowHelper(new T.Vector3(0,0,1),new T.Vector3(-.38,0,-.35),.23,0x8fc6c8,.025,.015);scene.add(inflow);
const grid=new T.GridHelper(1.2,24,0x48636c,0x263b45);grid.rotation.x=Math.PI/2;grid.position.z=-.48;scene.add(grid);
function reset(){camera.position.set(.20,-1.8,.45);orbit.target.set(0,0,.03);orbit.update();}reset();$('reset').onclick=reset;
let manifest,centres,field,metadata,ids=[],token=0,selected=-1,loaded=false,surface=null;
const faceStems=new T.InstancedMesh(new T.CylinderGeometry(.00035,.00035,1,5),new T.MeshBasicMaterial(),5680);
const faceHeads=new T.InstancedMesh(new T.ConeGeometry(.0014,1,6),new T.MeshBasicMaterial(),5680);
for(const mesh of [faceStems,faceHeads]){root.add(mesh);mesh.visible=false;mesh.frustumCulled=false;}
function showSurface(){
 const visible=loaded&&Boolean(surface)&&$('surface-forces').checked;
 faceStems.visible=faceHeads.visible=visible;$('surface-readout').hidden=!visible;if(!visible)return;
 const helper=new T.Object3D(),direction=new T.Vector3(),origin=new T.Vector3(),color=new T.Color();
 // Fixed physical display gain, shared across all angles. No clipping or per-angle normalization.
 const gain=600;
 let maximum=0;
 for(let i=0;i<manifest.surface_count;i++){
  origin.fromArray(surface,i*8);direction.fromArray(surface,i*8+3);const magnitude=direction.length(),length=magnitude*gain;maximum=Math.max(maximum,magnitude);direction.normalize();
  const tip=Math.min(.006,length*.25),shaft=length-tip;helper.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),direction.lengthSq()?direction:new T.Vector3(0,1,0));helper.position.copy(origin).addScaledVector(direction,shaft/2);helper.scale.set(1,shaft,1);helper.updateMatrix();faceStems.setMatrixAt(i,helper.matrix);
  helper.position.copy(origin).addScaledVector(direction,shaft+tip/2);helper.scale.set(Math.min(1,length/.008),tip,Math.min(1,length/.008));helper.updateMatrix();faceHeads.setMatrixAt(i,helper.matrix);color.set(surface[i*8+6]>=0?'#ff9869':'#6aabff');faceStems.setColorAt(i,color);faceHeads.setColorAt(i,color);
 }
 for(const mesh of [faceStems,faceHeads]){mesh.count=manifest.surface_count;mesh.instanceMatrix.needsUpdate=true;mesh.instanceColor.needsUpdate=true;mesh.computeBoundingSphere();}
 $('surface-readout').textContent='면별 법선 힘'+`: ${manifest.surface_count.toLocaleString()}개 면 · 0.1 mN = 6 cm (모든 각도 고정 배율) · 최대 ${(maximum*1000).toFixed(4)} mN. 상대압력 × 면적의 압력 힘이며 점성 응력은 제외합니다. 면적이 큰 면은 같은 압력에서도 힘이 큽니다.`;
}
$('surface-forces').onchange=showSurface;
const cache=new Map(),obj=new T.Object3D(),v=new T.Vector3(),pos=new T.Vector3(),up=new T.Vector3(0,1,0),c=new T.Color();
function quantile(values,q){values.sort((a,b)=>a-b);return values[Math.floor((values.length-1)*q)]||1e-6;}
function selection(){if(selected<0){marker.visible=false;return;}const i=selected;marker.visible=true;marker.position.fromArray(centres,i*3);const velocity=Array.from(field.slice(i*4,i*4+3)),position=Array.from(centres.slice(i*3,i*3+3));$('selected').innerHTML=`<div><small>격자 #${i} · 기체 좌표 X / Y / Z</small><strong>${position.map(x=>(x*1000).toFixed(1)).join(' / ')} mm</strong></div><div><small>속력 / 속도 X / Y / Z</small><strong>${Math.hypot(...velocity).toFixed(3)} m/s</strong><small>${velocity.map(x=>x.toFixed(3)).join(' / ')} m/s</small></div><div><small>상대압력</small><strong>${field[i*4+3].toFixed(4)} Pa</strong></div>`;}
function renderField(){if(!field)return;const slice=Number($('slice').value)/1000,thickness=Number($('thickness').value)/1000,spacing=Number($('spacing').value)/1000,gain=Number($('gain').value),volume=$('mode').value==='volume';
 $('slice-value').textContent=(slice*1000).toFixed(0)+' mm';$('thickness-value').textContent=(thickness*1000).toFixed(0)+' mm';$('spacing-value').textContent=(spacing*1000).toFixed(0)+' mm';$('gain-value').textContent=gain.toFixed(1)+'×';$('slice').disabled=$('thickness').disabled=volume;
 // Keep an actual cell nearest each display voxel centre; never average across the shell.
 const bins=new Map();let eligible=0;
 for(let i=0;i<manifest.count;i++){const x=centres[3*i],y=centres[3*i+1],z=centres[3*i+2];if(Math.abs(x)>.42||Math.abs(y)>.32||z<-.32||z>.55||(!volume&&Math.abs(y-slice)>thickness/2))continue;eligible++;const bx=Math.floor(x/spacing),by=volume?Math.floor(y/spacing):0,bz=Math.floor(z/spacing),key=`${bx},${by},${bz}`,distance=(x-(bx+.5)*spacing)**2+(y-(volume?(by+.5)*spacing:slice))**2+(z-(bz+.5)*spacing)**2;if(!bins.has(key)||distance<bins.get(key).distance)bins.set(key,{i,distance});}
 let chosen=[...bins.values()].map(b=>b.i);if(chosen.length>capacity){const all=chosen;chosen=Array.from({length:capacity},(_,i)=>all[Math.floor(i*all.length/capacity)]);}ids=chosen;
 const pressure=$('color').value==='pressure';const limit=quantile(ids.map(i=>pressure?Math.abs(field[4*i+3]):Math.hypot(field[4*i],field[4*i+1],field[4*i+2])),.98);
 $('color-title').textContent=pressure?'상대압력 Pa · 표시 격자의 절댓값 98백분위 범위':'속력 m/s · 표시 격자의 98백분위 범위';
 $('color-bar').style.background=pressure?'linear-gradient(90deg,#2878df,#eeeeee,#e64532)':'linear-gradient(90deg,#263be0,#20cfbc,#f5db4f)';$('low').textContent=pressure?(-limit).toFixed(2):'0';$('middle').textContent=pressure?'0':(limit/2).toFixed(2);$('high').textContent=limit.toFixed(2);
 ids.forEach((i,j)=>{pos.fromArray(centres,i*3);v.fromArray(field,i*4);const speed=v.length(),length=Math.min(.1,speed*.02*gain),tip=Math.min(.012,length*.3),shaft=Math.max(0,length-tip);if(speed>0)v.divideScalar(speed);else v.set(0,1,0);obj.quaternion.setFromUnitVectors(up,v);obj.position.copy(pos).addScaledVector(v,shaft/2);obj.scale.set(1,shaft,1);obj.updateMatrix();stems.setMatrixAt(j,obj.matrix);obj.position.copy(pos).addScaledVector(v,shaft+tip/2);obj.scale.set(Math.min(1,length/.02),tip,Math.min(1,length/.02));obj.updateMatrix();heads.setMatrixAt(j,obj.matrix);const value=pressure?field[i*4+3]:speed;if(pressure){const t=Math.min(1,Math.abs(value)/limit);c.set('#eeeeee').lerp(new T.Color(value<0?'#2878df':'#e64532'),t);}else{const t=Math.min(1,value/limit);c.set(t<.5?'#263be0':'#20cfbc').lerp(new T.Color(t<.5?'#20cfbc':'#f5db4f'),t<.5?t*2:(t-.5)*2);}stems.setColorAt(j,c);heads.setColorAt(j,c);});
 for(const mesh of [stems,heads]){mesh.count=ids.length;mesh.instanceMatrix.needsUpdate=true;if(mesh.instanceColor)mesh.instanceColor.needsUpdate=true;mesh.computeBoundingSphere();}
 root.rotation.y=metadata.angle*Math.PI/180;showTorque();shell.visible=$('shell').checked;
 $('view-title').textContent=`기울기 ${metadata.angle}° · 풍속 ${metadata.speed} m/s · ${$('arrows').checked?ids.length.toLocaleString()+'개 화살표':'입자 단독 보기'}`;
 $('status').textContent=`영역 내 ${eligible.toLocaleString()}개 격자 중 ${ids.length.toLocaleString()}개 표시${ids.length===capacity?' · 최대 표시 개수 도달':''}`;
 $('data-info').textContent=`원본 ${manifest.count.toLocaleString()}개 격자 · 저장 반복 ${metadata.iteration} · 압력 원본 범위 ${metadata.pressure_min.toFixed(2)} ~ ${metadata.pressure_max.toFixed(2)} Pa · 최대 속력 ${metadata.max_speed.toFixed(2)} m/s. 1 m/s 화살표 길이 ${(gain*2).toFixed(1)}cm (최대 10cm).`;
 if(!ids.includes(selected))selected=ids.reduce((best,i)=>{const distance=k=>centres[3*k]**2+centres[3*k+1]**2+(centres[3*k+2]-.12)**2;return best<0||distance(i)<distance(best)?i:best;},-1);
 if(!ids.length){$('selected').textContent='이 단면에는 표시할 격자가 없습니다. 단면 두께나 위치를 바꿔보세요.';selected=-1;}selection();resetParticles();
}
async function loadAngle(){const seq=++token;loaded=false;faceStems.visible=faceHeads.visible=false;torqueArrow.group.visible=false;comMarker.visible=false;$('status').textContent='저장된 유동장을 읽고 있습니다…';stems.visible=heads.visible=false;marker.visible=false;try{const meta=manifest.cases.find(row=>row.angle===Number($('angle').value));if(!cache.has(meta.angle)){const response=await fetch('fields/'+meta.file);if(!response.ok)throw Error('속도·압력 파일을 읽지 못했습니다.');const values=new Float32Array(await response.arrayBuffer());if(values.length!==manifest.count*4)throw Error('격자 데이터 크기가 맞지 않습니다.');cache.set(meta.angle,values);}const surfaceResponse=await fetch('fields/'+meta.surface_file);if(!surfaceResponse.ok)throw Error('면별 압력 데이터를 읽지 못했습니다.');const surfaceValues=new Float32Array(await surfaceResponse.arrayBuffer());if(surfaceValues.length!==manifest.surface_count*8)throw Error('면별 데이터 크기 불일치');if(seq!==token)return;surface=surfaceValues;metadata=meta;field=cache.get(meta.angle);selected=-1;loaded=true;stems.visible=heads.visible=$('arrows').checked;renderField();showSurface();}catch(error){if(seq===token)$('status').textContent=error.message;}}
for(const id of ['mode','slice','thickness','spacing','gain','color','shell'])$(id).oninput=renderField;$('angle').onchange=()=>{if(manifest)loadAngle();};
const ray=new T.Raycaster();let down;
renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];});renderer.domElement.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4||(!stems.visible&&!faceStems.visible))return;const r=renderer.domElement.getBoundingClientRect();ray.setFromCamera(new T.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);const targets=[];if(stems.visible)targets.push(heads,stems);if(faceStems.visible)targets.push(faceHeads,faceStems);const hit=ray.intersectObjects(targets)[0];if(hit){if(hit.object===faceHeads||hit.object===faceStems){const i=hit.instanceId,values=Array.from(surface.slice(i*8,i*8+8));$('selected').innerHTML=`<div><small>껍질 면 #${i} · 압력 힘</small><strong>${(Math.hypot(...values.slice(3,6))*1000).toFixed(5)} mN</strong></div><div><small>상대압력 / 면적</small><strong>${values[6].toFixed(4)} Pa</strong><small>${(values[7]*1e6).toFixed(3)} mm²</small></div><div><small>힘 X / Y / Z · 기체 좌표</small><strong>${values.slice(3,6).map(x=>(x*1000).toFixed(5)).join(' / ')} mN</strong></div>`;marker.position.fromArray(surface,i*8);marker.visible=true;}else{selected=ids[hit.instanceId];selection();}}});
// Nearest actual CFD cell, independent of arrow display thinning.
let tree=null;
function buildTree(){const indices=[];for(let i=0;i<manifest.count;i++){if(Math.abs(centres[3*i])<.5&&Math.abs(centres[3*i+1])<.4&&centres[3*i+2]>-.4&&centres[3*i+2]<.65)indices.push(i);}function build(a,depth){if(!a.length)return null;const axis=depth%3;a.sort((i,j)=>centres[i*3+axis]-centres[j*3+axis]);const mid=a.length>>1;return {i:a[mid],axis,left:build(a.slice(0,mid),depth+1),right:build(a.slice(mid+1),depth+1)};}tree=build(indices,0);}
function nearest(x,y,z){const point=[x,y,z];let best=-1,distance=Infinity;function visit(node){if(!node)return;const i=node.i,d=(x-centres[i*3])**2+(y-centres[i*3+1])**2+(z-centres[i*3+2])**2;if(d<distance){best=i;distance=d;}const delta=point[node.axis]-centres[i*3+node.axis];visit(delta<0?node.left:node.right);if(delta*delta<distance)visit(delta<0?node.right:node.left);}visit(tree);return best;}
const particleCount=10000,particlePositions=new Float32Array(particleCount*3),ages=new Float32Array(particleCount),trailPositions=new Float32Array(particleCount*6);
const particleGeometry=new T.BufferGeometry();particleGeometry.setAttribute('position',new T.BufferAttribute(particlePositions,3));
const particles=new T.Points(particleGeometry,new T.PointsMaterial({color:0xfff0ba,size:.006,transparent:true,opacity:.95,depthWrite:false}));particles.frustumCulled=false;root.add(particles);
const trailGeometry=new T.BufferGeometry();trailGeometry.setAttribute('position',new T.BufferAttribute(trailPositions,3));const trails=new T.LineSegments(trailGeometry,new T.LineBasicMaterial({color:0xffe3a0,transparent:true,opacity:.65,depthWrite:false}));trails.frustumCulled=false;root.add(trails);
let particlePlaying=true,particleLast=performance.now(),particleAccumulator=0;
function spawnParticle(j){if(!ids.length)return;const cell=ids[Math.floor(Math.random()*ids.length)];for(let k=0;k<3;k++)particlePositions[j*3+k]=centres[cell*3+k];ages[j]=1+Math.random()*3;}
function resetParticles(){for(let j=0;j<particleCount;j++)spawnParticle(j);for(let j=0;j<particleCount;j++)for(let k=0;k<3;k++){trailPositions[j*6+k]=trailPositions[j*6+3+k]=particlePositions[j*3+k];}particleGeometry.attributes.position.needsUpdate=true;trailGeometry.attributes.position.needsUpdate=true;}
function crossesShell(x,y,z,nx,ny,nz){const dx=nx-x,dy=ny-y,dz=nz-z,a=dx*dx+dy*dy+dz*dz;if(a<1e-20)return false;const b=2*(x*dx+y*dy+(z+.09)*dz),c=x*x+y*y+(z+.09)**2-.1495**2,disc=b*b-4*a*c;if(disc<0)return false;for(const sign of [-1,1]){const t=(-b+sign*Math.sqrt(disc))/(2*a);if(t>=0&&t<=1&&z+t*dz>=-.001)return true;}return false;}
function animateParticles(now){const elapsed=Math.min(.08,(now-particleLast)/1000);particleLast=now;particles.visible=trails.visible=$('particles').checked&&Boolean(field)&&loaded&&ids.length>0;if(!particles.visible||!particlePlaying||!tree)return;particleAccumulator+=elapsed;if(particleAccumulator<1/30)return;const dt=particleAccumulator*Number($('particle-rate').value);particleAccumulator=0;const volume=$('mode').value==='volume',slice=Number($('slice').value)/1000,half=Number($('thickness').value)/2000;
 for(let j=0;j<particleCount;j++){let x=particlePositions[j*3],y=particlePositions[j*3+1],z=particlePositions[j*3+2];const cell=nearest(x,y,z);if(cell<0)continue;const ux=field[cell*4],uy=field[cell*4+1],uz=field[cell*4+2],nx=x+ux*dt,ny=y+uy*dt,nz=z+uz*dt;ages[j]-=dt;if(ages[j]<=0||Math.abs(nx)>.42||Math.abs(ny)>.32||nz<-.32||nz>.55||(!volume&&Math.abs(ny-slice)>half)||crossesShell(x,y,z,nx,ny,nz)){spawnParticle(j);for(let k=0;k<3;k++)trailPositions[j*6+k]=trailPositions[j*6+3+k]=particlePositions[j*3+k];continue;}particlePositions.set([nx,ny,nz],j*3);trailPositions.set([x,y,z,nx,ny,nz],j*6);}
 particleGeometry.attributes.position.needsUpdate=true;trailGeometry.attributes.position.needsUpdate=true;}
$('arrows').onchange=()=>{stems.visible=heads.visible=loaded&&$('arrows').checked;document.querySelector('.color-key').hidden=!$('arrows').checked;if(metadata)$('view-title').textContent=`기울기 ${metadata.angle}° · 풍속 ${metadata.speed} m/s · ${$('arrows').checked?ids.length.toLocaleString()+'개 화살표':'입자 단독 보기'}`;};
$('pause').onclick=()=>{particlePlaying=!particlePlaying;$('pause').textContent=particlePlaying?'입자 일시정지':'입자 재생';};$('particle-rate').oninput=()=>{$('particle-rate-value').textContent=Number($('particle-rate').value).toFixed(1)+'×';};

new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();}).observe(host);function animate(now=performance.now()){animateParticles(now);orbit.update();renderer.render(scene,camera);requestAnimationFrame(animate);}animate();
async function init(){try{const response=await fetch('fields/manifest.json');if(!response.ok)throw Error('CFD 데이터 목록이 없습니다.');manifest=await response.json();const coords=await fetch('fields/'+manifest.centres);centres=new Float32Array(await coords.arrayBuffer());if(centres.length!==manifest.count*3)throw Error('격자 좌표 수가 맞지 않습니다.');buildTree();await loadAngle();}catch(error){$('status').textContent=error.message;}

}
init();
