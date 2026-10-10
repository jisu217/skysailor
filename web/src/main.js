import {rotationArrow,updateRotationArrow} from './cap/geometry.js';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

const $ = id => document.getElementById(id);
const notes = {
  dome:['B · 세 줄 윈치 제어','원점 위치 제어는 지면 기준 전체 질량중심의 X/Y를 (0, 0)m로 유도합니다. 수평 위치 오차와 속도로 목표 기울기를 계산하고(최대 15°), 세 줄로 자세를 바꿉니다. 파란 지면 고리는 목표점입니다. 아래 삼각형은 돔에 대한 무게추 목표로, 지면 목표와 다릅니다. 횡이동을 위한 기울기로 낙하시간이 짧아질 수 있고 정확한 원점 도달은 보장하지 않습니다.\n\n지름 24 cm, 높이 6 cm의 돔과 자유롭게 움직이는 제어기를 세 줄이 연결합니다. 기본 줄 길이는 중앙 위치에서의 사선 거리입니다. 초기 수직 간격은 √(줄 길이² − 120²) mm입니다.\n\n삼각형의 목표 위치를 세 줄의 목표 길이로 변환합니다. 노란 고리는 목표 위치, 분홍 점은 실제 위치입니다. 목표 높이는 초기 높이지만 실제 제어기의 높이·회전·흔들림을 고정하지 않습니다. 느슨해진 줄은 힘을 전달하지 않으며 제어기를 밀 수 없습니다.\n\n줄 감김·풀림 속도는 각 줄의 무하중 길이가 실제로 변하는 최대 속도입니다. 줄은 탄성과 감쇠를 가지므로 펼쳐진 기하학적 거리는 풀린 길이와 다를 수 있습니다. 하중으로 감기가 제한되면 설정 속도보다 느려집니다.\n\n낙하시간 튜닝 PD는 3m·줄 약 170mm·40mm/s 조건에서 낙하시간을 늘리도록 계수를 탐색한 공기력 보상 PD입니다. 초기 기울기 25° 이하에 적용하며, 초과 시 기존 PD 계수를 사용합니다. 모든 조건에서 더 낫거나 최적임을 보장하지 않습니다. 기존 공기력 보상 PD도 선택해 비교할 수 있습니다.\n\nP·PD·공기력 보상 PD는 50 Hz로 목표를 갱신합니다. 예측 가속·제동은 실제 줄 상태를 복사해 0.3초 앞의 후보를 비교합니다. 삼각형 클릭은 수동 모드로 전환합니다. 예전 평면 이동기구와 다른 물리 모델이므로 이전 성능 수치를 그대로 적용할 수 없습니다.\n\n공기력과 토크는 깊이 6cm 돔의 예비 CFD 표를 보간하며, 60° 회전 시험의 감쇠 근사를 적용합니다. 미수렴 자료이므로 결과는 탐색용입니다. 실제 센서, 줄의 질량·처짐·꼬임, 모터 회전 관성·전기 모델은 포함하지 않습니다.'],
  winch:['세 줄의 실제 감김·풀림','길이: 릴에서 풀려나온 줄의 무하중 길이. 감김 속도: +는 감기, −는 풀기, 0은 정지. 장력: 줄이 두 물체를 당기는 힘입니다. 행에 마우스를 올리면 실제 두 연결점 거리와 목표 길이를 볼 수 있습니다. 모든 값은 재생 시점의 기록입니다.\n\n회색/주황 점선은 느슨한 줄의 연결 관계를 표시하며 실제 처짐 형상은 아닙니다. 각 줄은 강성 30 N/m, 감쇠 0.025 N·s/m의 인장 전용 모델입니다. 감기 방향의 가용 당김 힘은 줄당 0.08 N으로 가정하고, 초과 부하에서는 감김을 줄이거나 멈춥니다. 외력 때문에 장력이 이 값을 넘을 수 있으며 장력 자체를 잘라내지는 않습니다. 풀기와 정지 상태에는 이상적인 속도 제어·브레이크를 가정합니다.\n\nCSV에는 각 줄의 목표 길이, 풀린 길이, 실제 거리, 감김 속도, 장력, 느슨함과 부하 제한 상태가 포함됩니다.'],
  about:['Clover Flight Lab','A는 네 장의 유연한 날개, B는 고정된 돔 아래 제어기 위치를 이동하는 낙하 실험실입니다.\n\nMuJoCo가 물리 운동을 계산하고 브라우저가 계산된 위치와 회전을 재생합니다. AI 학습과 실제 센서는 아직 연결하지 않았습니다. 공기력은 조정 가능한 근사 모델입니다.'],
  scene:['3D 장면 보기','드래그로 회전하고 스크롤로 확대합니다. 기체 추적은 날개 중심을 따라가며, 지면 기준은 왼쪽에 실제 크기의 전체 낙하 경로와 지면, 오른쪽에 기체 추적 확대 화면을 함께 보여줍니다. 각 화면을 따로 드래그·확대할 수 있으며 재생 시점은 같습니다. 위에서 보기는 분절 윤곽을 확인하는 추적 시점입니다. 높이 눈금은 모든 시점에서 낙하를 표시합니다. 두 실행을 바꾸거나 나란히 비교할 수 있습니다.\n\n비교 화면의 두 물체는 각각 독립적인 실험입니다. 보기 좋게 옆으로 배치했으며 물리적으로 상호작용하지 않습니다. 비교 모드의 수치는 민트색 실행 기준입니다. 추적 시점의 격자는 시점 가이드이며, 지면 기준의 격자만 실제 z=0 지면입니다.'],
  settings:['실험 조건','설정을 바꾼 뒤 실험 실행을 누르면 같은 조건에서 A는 PD 제어와 무제어, B는 선택한 알고리즘과 줄 길이 고정를 새로 계산합니다. 초기 방향 시드는 기울어진 방향을 결정하며 같은 시드는 같은 조건을 재현합니다.\n\nA는 최대 5초, B는 최대 8초 또는 지면 근처에 도달할 때까지 계산합니다. 설정 변경은 기존 재생에 즉시 반영되지 않습니다.'],
  controller:['두 축 PD 제어','Kp는 기울기를 바로잡는 반응의 크기, Kd는 회전을 줄이는 감쇠의 크기입니다.\n\n마주 보는 실을 한쪽은 감고 반대쪽은 같은 길이만큼 풉니다. 이동 한계는 ±12 mm, 속도 한계는 40 mm/s입니다. 제어기는 시뮬레이터의 정확한 자세와 각속도를 사용합니다. 구동기 토크 한계와 센서 오차는 아직 포함하지 않았습니다.'],
  wind:['3차원 바람','실측 모드는 Falkenberg 50m 초음파 풍속계의 u/v/w를 X(동)/Y(북)/Z(위)로 재생합니다. 2025-02-12 관측, 명목 10Hz이며 최대 0.2초 간격만 선형 보간합니다. 구간 끝을 반복하지 않습니다. 기본 풍속·시드·돌풍 설정은 무시합니다. 기체 전체에 같은 바람을 적용하며 공간 난류나 3m 높이의 바람을 재현하지 않습니다.\n\n합성 모드: 기본 X·Y 바람에 랜덤 횡풍을 더합니다. 돌풍 최대 풍속은 추가 바람 벡터의 상한이며, 변화 간격마다 뽑은 방향과 세기를 부드럽게 이어줍니다. 기본값은 X 0.2m/s + 최대 0.4m/s 돌풍, 0.8초 간격입니다. 같은 바람 시드는 같은 바람을 재현하고, 두 제어 비교에도 동일한 바람을 적용합니다. 공간 전체에 같은 횡풍을 적용하는 시험 모델로, 실제 난류나 수직 돌풍은 포함하지 않습니다. 무풍은 일정한 바람을 선택하고 X/Y를 모두 0으로 설정하세요.'],
  playback:['낙하 재생','물리 계산을 완료한 결과를 재생합니다. 기본 재생 속도는 0.25배입니다. 재생 막대를 움직여 자세·실 이동·비행 기록을 함께 확인하세요.\n\n계산 간격은 1 ms, 전송 프레임 간격은 10 ms입니다. 3D 화면은 프레임 사이를 보간합니다. 각 실험 종료 이후에는 마지막 자세가 유지됩니다.'],
  telemetry:['비행 기록','가로축은 시뮬레이션 시간입니다. 민트색은 A의 PD 제어 또는 B의 선택한 제어, 주황색은 A의 무제어 또는 B의 줄 길이 고정입니다. 세로선은 현재 재생 위치입니다.\n\nCSV에는 두 실행의 높이, 기울기, 낙하 속도, A의 실 이동량(mm)·장력(N) 또는 B의 세 줄 길이·감김 속도·장력·제어기 실제 위치가 포함됩니다. 10 ms 간격의 기록이며 최종 프레임도 포함합니다.'],
  results:['결과 읽기','기울기 RMS는 전체 계산 구간에서 기울기의 평균적인 크기입니다. 최대 기울기가 90°를 넘으면 뒤집힘으로 표시합니다.\n\n비행 시간은 지면 근처 도달 또는 시간 제한까지입니다. 두 실행의 종료 시점이 다를 수 있어 RMS의 비교 구간도 다릅니다. 평균 낙하속도는 전체 무게중심의 높이 변화 ÷ 실행 시간입니다. 화면의 순간 낙하속도는 돔의 속도입니다. 한 번의 결과가 안정성을 보장하지는 않습니다.'],
  aero:['공기역학 표시','B: 청록 화살표는 돔 자체 무게중심에 적용하는 CFD 공기력 합력입니다. 보라 호는 그 점 기준 총 공기 토크(정적 CFD + 회전 감쇠)이며 5 mN·m = 288° 호, 초과 시 표시 길이는 제한됩니다. B에는 면별 하중 색상을 표시하지 않습니다.\n\nA: 청록 화살표는 각 분절 중심에서 계산한 공기력입니다. 빨간 화살표는 전체 질량중심의 중력이며 항상 아래를 향합니다. 파란 화살표는 각 날개에서 평균한 상대풍(바람 속도 − 분절 속도)입니다.\n\n공기력: 10 mN → 표시 길이 8 cm (24 cm에서 제한). 중력: 80.4 mN → 8.04 cm. 상대풍: 1 m/s → 1.2 cm (12 cm에서 제한). 세 화살표의 배율은 서로 다릅니다.\n\n색상은 분절별 법선 공기하중 크기 |F_normal|/면적, 고정 범위 0–30 Pa입니다. 연속적인 압력장이나 CFD 유선이 아닙니다. 공기 조건을 진공으로 바꾸면 공기력은 0이 되고 중력은 유지됩니다.'],
  model:['장치 모델','펼친 폭 약 24 cm, 총 질량 8.2 g입니다. 각 날개는 중심 쪽은 뾰족하고 바깥쪽은 둥근 물방울 윤곽을 6개의 직선 가로 분절로 나눈 형태입니다. 총 24개 패널이 탄성 힌지로 연결되어 휩니다. 화면과 공기력 면적은 동일한 윤곽을 사용하며 관성은 분절별 상자 근사입니다.\n\n실은 늘어날 때만 당기는 힘을 전달합니다. 패널별 항력을 계산하며, 와류·날개 사이 유동 간섭·천의 주름·자체 충돌은 포함하지 않습니다. 줄은 끝점을 잇는 선으로 표시하므로 느슨한 줄의 실제 처짐을 표현하지 않습니다. 지면 접촉과 착지는 계산하지 않습니다.'],
};
for (const button of document.querySelectorAll('[data-info]')) button.addEventListener('click',()=>{const [title,body]=notes[$('variant').value==='B'&&['model','controller'].includes(button.dataset.info)?'dome':button.dataset.info];$('info-title').textContent=title;$('info-body').textContent=body;$('info-dialog').showModal();});
$('close-info').onclick=$('confirm-info').onclick=()=>$('info-dialog').close();
$('info-dialog').addEventListener('click',e=>{if(e.target===$('info-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
let toastTimer;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,6500);}
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('이 브라우저에서는 전체화면을 지원하지 않습니다.');}};

const viewport=$('viewport');
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(38,1,0.001,30);camera.up.set(0,0,1);
let renderer;
try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});}catch{toast('WebGL을 사용할 수 없습니다. 브라우저의 그래픽 가속을 확인해주세요.');throw new Error('WebGL unavailable');}
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x000000,0);renderer.outputColorSpace=THREE.SRGBColorSpace;viewport.appendChild(renderer.domElement);
const detailViewport=$('detail-viewport');
const detailCamera=new THREE.PerspectiveCamera(38,1,.001,30);detailCamera.up.set(0,0,1);
const detailRenderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
detailRenderer.setPixelRatio(Math.min(devicePixelRatio,2));detailRenderer.setClearColor(0x000000,0);detailRenderer.outputColorSpace=THREE.SRGBColorSpace;detailViewport.appendChild(detailRenderer.domElement);
const detailControls=new OrbitControls(detailCamera,detailRenderer.domElement);detailControls.enableDamping=true;detailControls.enablePan=false;detailControls.minDistance=.16;detailControls.maxDistance=2;detailControls.maxPolarAngle=Math.PI*.95;
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.enablePan=false;controls.minDistance=.16;controls.maxDistance=2;controls.maxPolarAngle=Math.PI*.95;
scene.add(new THREE.HemisphereLight(0xccffed,0x35445a,2.4));
const key=new THREE.DirectionalLight(0xc5ffe7,3.4);key.position.set(.5,-.4,1.2);scene.add(key);
const rim=new THREE.DirectionalLight(0x96bbff,2.2);rim.position.set(-.5,.2,.3);scene.add(rim);
const grid=new THREE.GridHelper(4,80,0x47605f,0x273a44);grid.rotation.x=Math.PI/2;grid.position.z=-.16;grid.material.transparent=true;grid.material.opacity=.35;scene.add(grid);
const ring=new THREE.Mesh(new THREE.RingGeometry(.135,.1355,96),new THREE.MeshBasicMaterial({color:0x688a85,transparent:true,opacity:.25,side:THREE.DoubleSide}));ring.position.z=-.159;scene.add(ring);
const models={};let dataset=null,initial=null,view='pd',cameraMode='world',playing=false,playTime=0,duration=0,busy=false;
const reference=new THREE.Vector3();
function makeModel(geometry,mode){
  const group=new THREE.Group();scene.add(group);
  const meshes=geometry.map((g,index)=>{
    let geo;
    if(g.triangles){geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(g.triangles.flat(),3));geo.computeVertexNormals();}
    else if(g.polygon){
      const shape=new THREE.Shape(g.polygon.map(p=>new THREE.Vector2(...p)));
      geo=new THREE.ExtrudeGeometry(shape,{depth:.0006,bevelEnabled:false,steps:1});geo.translate(0,0,-.0003);
    }else geo=g.type===6?new THREE.BoxGeometry(2,2,2):new THREE.SphereGeometry(1,32,16);
    const color=index===0?0xc7d6d5:index===geometry.length-1?0xeab27e:mode==='off'?0xe6a16d:0x67dca4;
    const material=new THREE.MeshStandardMaterial({color,roughness:.48,metalness:.1,side:THREE.DoubleSide});
    const mesh=new THREE.Mesh(geo,material);mesh.userData.baseColor=color;
    if(!g.polygon&&!g.triangles){mesh.scale.set(...g.size);if(g.type===2)mesh.scale.setScalar(g.size[0]);}
    group.add(mesh);
    if(g.polygon){const edge=new THREE.LineSegments(new THREE.EdgesGeometry(geo,25),new THREE.LineBasicMaterial({color:0x143b35,transparent:true,opacity:.8}));mesh.add(edge);}
    return mesh;
  });
  const lines=Array.from({length:initial.tips.length},()=>{const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(6),3));const line=new THREE.Line(geometry,new THREE.LineDashedMaterial({color:mode==='off'?0xe7be91:0xb8e4d7,transparent:true,opacity:.8,dashSize:.008,gapSize:0}));line.userData.tautColor=mode==='off'?0xe7be91:0xb8e4d7;group.add(line);return line;});
  const arrow=(color)=>{const a=new THREE.ArrowHelper(new THREE.Vector3(0,0,1),new THREE.Vector3(),.01,color,.005,.003);group.add(a);return a;};
  const forces=Array.from({length:24},()=>arrow(0x5de2ee));
  const flow=Array.from({length:initial.tips.length===3?8:4},()=>arrow(0x839aff));
  const gravity=arrow(0xfb8f8f);
  const torque=rotationArrow(0xc9a0ff,.10);group.add(torque.group);
  const track=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:mode==='off'?0xeda975:0x7ce4bd,transparent:true,opacity:.5}));scene.add(track);
  const comMarker=new THREE.Mesh(new THREE.SphereGeometry(.003,16,8),new THREE.MeshBasicMaterial({color:0xec93e0,depthTest:false}));comMarker.renderOrder=5;group.add(comMarker);
  const targetMarker=new THREE.Mesh(new THREE.SphereGeometry(.0045,12,8),new THREE.MeshBasicMaterial({color:0xf2d878,wireframe:true,depthTest:false}));targetMarker.renderOrder=5;group.add(targetMarker);
  const worldMarker=new THREE.Mesh(new THREE.RingGeometry(.05,.065,48),new THREE.MeshBasicMaterial({color:0x80bfff,side:THREE.DoubleSide,depthTest:false}));worldMarker.position.set(0,0,.002);worldMarker.renderOrder=6;group.add(worldMarker);
  return {group,meshes,lines,forces,flow,gravity,torque,track,comMarker,targetMarker,worldMarker};
}
function ensureModels(geometry){if(!models.pd){models.pd=makeModel(geometry,'pd');models.off=makeModel(geometry,'off');}}
function resetCamera(){
  const split=cameraMode==='world';
  const hang=initial?.hang||.12;
  const size=$('variant').value==='B'?Math.max(1,hang/.12):1;
  const centerZ=$('variant').value==='B'?.02-hang/2:-.035;
  const followPosition=$('variant').value==='B'?[.32*size,-.40*size,.09*size]:[.22,-.30,.20];
  $('stage').classList.toggle('split-view',split);detailViewport.hidden=!split;$('split-labels').hidden=!split;
  detailControls.target.set(0,0,centerZ);detailCamera.position.set(...followPosition);if(view==='both')detailCamera.position.multiplyScalar(1.5);detailControls.update();
  resizeViews();
  if(split){detailCamera.position.sub(detailControls.target).multiplyScalar(Math.max(1,.85/detailCamera.aspect)).add(detailControls.target);detailControls.update();}
  controls.maxDistance=cameraMode==='world'?30:2;
  if(cameraMode==='world'){
    const h=dataset?.parameters.height||initial?.height||3;
    controls.target.set(0,0,h/2);camera.position.set(h*.35,-h*1.9,h*.9);
    grid.position.z=0;ring.visible=false;
  }else{
    controls.target.set(0,0,centerZ);
    camera.position.set(...(cameraMode==='top'?[.001,-.001,.46]:followPosition));
    grid.position.z=-.16;ring.visible=true;
  }
  controls.update();
}
resetCamera();$('camera-reset').onclick=resetCamera;
$('camera-mode').onchange=()=>{cameraMode=$('camera-mode').value;resetCamera();renderState();};
for(const id of ['show-forces','show-flow','show-load'])$(id).onchange=renderState;
function frameAt(mode,t){
  const frames=dataset?.runs[mode]?.frames;
  if(!frames)return {a:initial,b:initial,alpha:0};
  let low=0,high=frames.length-1;
  while(low<high){const mid=Math.ceil((low+high)/2);if(frames[mid].t<=t)low=mid;else high=mid-1;}
  const a=frames[low],b=frames[Math.min(low+1,frames.length-1)];return {a,b,alpha:b.t>a.t?Math.min(1,Math.max(0,(t-a.t)/(b.t-a.t))):0};
}
const va=new THREE.Vector3(),vb=new THREE.Vector3(),qa=new THREE.Quaternion(),qb=new THREE.Quaternion();
function lerpArray(a,b,t){return a.map((v,i)=>v+(b[i]-v)*t);}
function applyFrame(model,frames,offset,space=cameraMode){
  const {a,b,alpha}=frames;if(!a)return;
  reference.fromArray(space==='world'?[0,0,0]:lerpArray(a.center,b.center,alpha));
  model.group.position.set(offset,0,0);
  model.worldMarker.visible=Boolean(a.world_target)&&space==='world';
  if(a.world_target)model.worldMarker.position.set(a.world_target[0],a.world_target[1],.002).sub(reference);
  model.meshes.forEach((mesh,i)=>{
    va.fromArray(a.position[i]);vb.fromArray(b.position[i]);mesh.position.copy(va.lerp(vb,alpha).sub(reference));
    qa.set(a.quaternion[i][1],a.quaternion[i][2],a.quaternion[i][3],a.quaternion[i][0]);qb.set(b.quaternion[i][1],b.quaternion[i][2],b.quaternion[i][3],b.quaternion[i][0]);mesh.quaternion.copy(qa.slerp(qb,alpha));
  });
  model.lines.forEach((line,i)=>{const positions=line.geometry.attributes.position;va.fromArray(lerpArray(a.tips[i],b.tips[i],alpha)).sub(reference);vb.fromArray(lerpArray(a.anchor,b.anchor,alpha)).sub(reference);positions.setXYZ(0,va.x,va.y,va.z);positions.setXYZ(1,vb.x,vb.y,vb.z);positions.needsUpdate=true;line.geometry.computeBoundingSphere();line.computeLineDistances();const slack=Boolean((alpha<.5?a:b).line_slack?.[i]);line.material.gapSize=slack?.005:0;line.material.opacity=slack?.45:.8;line.material.color.setHex(slack?0xc49a73:line.userData.tautColor);});
  const at=(key,i)=>lerpArray(a[key][i],b[key][i],alpha);
  function arrow(arrow,position,vector,scale,cap,enabled){
    const v=new THREE.Vector3(...vector);const magnitude=v.length();
    arrow.visible=enabled&&magnitude>1e-8;
    if(!arrow.visible)return;
    arrow.position.fromArray(position).sub(reference);arrow.setDirection(v.normalize());
    const length=Math.min(cap,magnitude*scale);arrow.setLength(length,Math.min(.009,length*.25),Math.min(.005,length*.16));
  }
  $('show-load').disabled=a.aero_model==='cap60-cfd-v1';
  const forceOn=$('show-forces').checked,flowOn=$('show-flow').checked&&a.air_present,loadOn=$('show-load').checked;
  model.forces.forEach((ar,i)=>{if(i>=a.aero_force.length){ar.visible=false;return;}arrow(ar,at('aero_position',i),at('aero_force',i),8,.24,forceOn);});
  if(a.aero_torque){const torque=new THREE.Vector3(...lerpArray(a.aero_torque,b.aero_torque,alpha));updateRotationArrow(model.torque,torque,new THREE.Vector3(...at('aero_position',0)).sub(reference),torque.length()/.005,forceOn);}else model.torque.group.visible=false;
  for(let i=0;i<model.flow.length;i++){
    if(a.aero_model==='cap60-cfd-v1'){if(i===0)arrow(model.flow[i],at('aero_position',0),at('airflow',0),.012,.12,flowOn);else model.flow[i].visible=false;continue;}
    const position=[0,0,0],velocity=[0,0,0];
    const count=model.flow.length===8?3:6;
    for(let j=0;j<count;j++){const k=model.flow.length===8?j*8+i:i*6+j;const p=at('aero_position',k),v=at('airflow',k);for(let n=0;n<3;n++){position[n]+=p[n]/count;velocity[n]+=v[n]/count;}}
    arrow(model.flow[i],position,velocity,.012,.12,flowOn);
  }
  model.comMarker.visible=model.targetMarker.visible=Boolean(a.target_com);
  if(a.world_target){
    const pos=lerpArray(a.system_com,b.system_com,alpha);
    $('world-target-readout').textContent=`${(dataset?.parameters.b_controller||$('b-controller').value)==='position'?'지면 목표':'위치 제어 꺼짐 · 기준점'} (0, 0) m · 현재 (${pos[0].toFixed(2)}, ${pos[1].toFixed(2)}) m · 수평 오차 ${Math.hypot(pos[0],pos[1]).toFixed(2)} m`;
  }
  if(a.target_com){model.comMarker.position.fromArray(lerpArray(a.system_com,b.system_com,alpha)).sub(reference);model.targetMarker.position.fromArray(lerpArray(a.target_com,b.target_com,alpha)).sub(reference);}
  arrow(model.gravity,lerpArray(a.system_com,b.system_com,alpha),a.gravity,1,.2,forceOn);
  for(let i=0;i<24;i++){
    const mesh=model.meshes[i+1];
    if(loadOn&&a.aero_model!=='cap60-cfd-v1'){const p=a.loading[i]+(b.loading[i]-a.loading[i])*alpha;mesh.material.color.setHSL(.66-.59*Math.min(p/30,1),.72,.51);}
    else mesh.material.color.setHex(mesh.userData.baseColor);
  }

}
function updateScene(space){
  if(!initial)return;
  grid.position.z=space==='world'?0:-.16;ring.visible=space!=='world';
  for(const mode of ['pd','off']){models[mode].group.visible=view==='both'||view===mode;if(models[mode].group.visible)applyFrame(models[mode],frameAt(mode,playTime),view==='both'?(mode==='pd'?-.155:.155):0,space);models[mode].track.visible=space==='world'&&models[mode].group.visible;models[mode].track.position.x=view==='both'?(mode==='pd'?-.155:.155):0;}
}
function renderState(){
  if(!initial)return;
  updateScene(cameraMode);
  const {a,b,alpha}=frameAt(view==='off'?'off':'pd',playTime);
  const value=k=>a[k]+(b[k]-a[k])*alpha;
  if(a.wind){const w=lerpArray(a.wind,b.wind,alpha);$('wind-readout').textContent=`현재 바람 X ${w[0].toFixed(2)} · Y ${w[1].toFixed(2)} · Z ${w[2].toFixed(2)} m/s (위 +) · 풍속 ${Math.hypot(...w).toFixed(2)} m/s · 공기 대비 하강 ${value('air_descent_speed').toFixed(2)} m/s`;} 
  $('aero-value').textContent=`${(new THREE.Vector3(...lerpArray(a.aero_total,b.aero_total,alpha)).length()*1000).toFixed(1)} mN`;
  $('com-readout').hidden=!a.target_com;
  if(a.world_target){
    const pos=lerpArray(a.system_com,b.system_com,alpha);
    $('world-target-readout').textContent=`${(dataset?.parameters.b_controller||$('b-controller').value)==='position'?'지면 목표':'위치 제어 꺼짐 · 기준점'} (0, 0) m · 현재 (${pos[0].toFixed(2)}, ${pos[1].toFixed(2)}) m · 수평 오차 ${Math.hypot(pos[0],pos[1]).toFixed(2)} m`;
  }
  if(a.target_com){
    const error=new THREE.Vector3(...lerpArray(a.system_com,b.system_com,alpha)).distanceTo(new THREE.Vector3(...lerpArray(a.target_com,b.target_com,alpha)))*1000;
    $('com-readout').textContent=`● 실제 무게중심 / ◌ 목표 · 오차 ${error.toFixed(1)} mm`;
    if(dataset&&dataset.parameters.b_controller!=='manual'&&$('b-controller').value!=='manual'&&a.target_xy){
      const target=lerpArray(a.target_xy,b.target_xy,alpha);
      $('target-dot').setAttribute('cx',120+target[0]/.0012);$('target-dot').setAttribute('cy',110-target[1]/.0012);
      $('target-values').textContent=`자동 X ${(target[0]*1000).toFixed(1)} · Y ${(target[1]*1000).toFixed(1)} mm`;
    }
    const local=lerpArray(a.payload_local,b.payload_local,alpha);$('actual-dot').setAttribute('cx',120+local[0]/.0012);$('actual-dot').setAttribute('cy',110-local[1]/.0012);
  }
  if(a.line_rest){
    const state=alpha<.5?a:b;
    const lengths=lerpArray(a.line_rest,b.line_rest,alpha),rates=lerpArray(a.winch_speed,b.winch_speed,alpha),tension=lerpArray(a.tension,b.tension,alpha);
    for(let i=0;i<3;i++){
      const row=$(`winch-${i}`);row.classList.toggle('slack',state.line_slack[i]);row.classList.toggle('stalled',state.winch_stalled[i]);
      row.innerHTML=`<th>${i+1}</th><td>${(lengths[i]*1000).toFixed(1)}</td><td>${(rates[i]*1000).toFixed(1)}</td><td>${(tension[i]*1000).toFixed(1)}</td>`;
      row.title=`실제 거리 ${(state.line_actual[i]*1000).toFixed(1)} mm · 목표 ${(state.line_target[i]*1000).toFixed(1)} mm`;
    }
    $('winch-state').textContent=state.line_slack.map((slack,i)=>`${i+1}: ${state.winch_stalled[i]?'부하 제한':slack?'느슨함':tension[i]<1e-7?'무장력':'장력 전달'}`).join(' · ');
  }
  $('load-scale').hidden=!$('show-load').checked;
  document.querySelector('.force-legend .blue').textContent=a.air_present?'↗ 상대풍':'진공 · 상대풍 없음';
  const startHeight=dataset?.parameters.height||initial.height;
  $('alt-top').textContent=`${startHeight} m`;
  $('alt-dot').style.top=`${100*(1-Math.max(0,Math.min(1,value('height')/startHeight)))}%`;
  $('height').innerHTML=`${value('height').toFixed(2)} <small>m</small>`;$('tilt').innerHTML=`${value('tilt').toFixed(1)} <small>°</small>`;$('speed').innerHTML=`${value('speed').toFixed(2)} <small>m/s</small>`;
  $('time').innerHTML=`${playTime.toFixed(2)} <span>/ ${duration.toFixed(2)} s</span>`;
  $('timeline').value=playTime;paintRange($('timeline'));
  if(!busy)$('status').textContent=playing?'재생 중':playTime>=duration&&dataset?'재생 완료':dataset?'일시정지':'준비';
  $('play').textContent=playing?'Ⅱ':'▶';$('play').setAttribute('aria-label',playing?'일시정지':'재생');
  drawCharts();
}
for(const button of document.querySelectorAll('[data-view]'))button.onclick=()=>{view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b===button));$('model-labels').classList.toggle('visible',view==='both');resetCamera();renderState();};
function paintRange(el){el.style.setProperty('--fill',`${100*(Number(el.value)-Number(el.min))/(Number(el.max)-Number(el.min))}%`);}
function updateInputs(){document.querySelectorAll('input[type=range]').forEach(el=>{paintRange(el);const output=document.querySelector(`output[for="${el.id}"]`);if(output){const n=Number(el.value);output.innerHTML=el.name==='line_length_mm'?`${n.toFixed(1)} <span>mm</span>`:el.name==='drive_speed_mm_s'?`${n.toFixed(0)} <span>mm/s</span>`:el.name==='height'?`${n.toFixed(1)} <span>m</span>`:el.name==='tilt'?`${n} <span>°</span>`:n.toFixed(3);}});}
$('settings').addEventListener('input',()=>{updateInputs();if(dataset)$('run-note').textContent='설정 변경됨 · 실행하면 반영됩니다';});
$('defaults').onclick=()=>{const variant=$('variant').value;$('settings').reset();$('variant').value=variant;setTarget(0,0);$('b-controller').value='optimized';modeUI();updateInputs();$('run-note').textContent=dataset?'설정 초기화됨 · 실행하면 반영됩니다':'동일 조건으로 두 제어 모드 비교';};updateInputs();
$('play').onclick=()=>{if(!dataset)return;if(playTime>=duration)playTime=0;playing=!playing;renderState();};
$('rewind').onclick=()=>{playTime=0;playing=false;renderState();};
$('timeline').oninput=()=>{playing=false;playTime=Number($('timeline').value);renderState();};
function resultsTable(){
  const p=dataset.runs.pd.summary,o=dataset.runs.off.summary;
  const end=s=>s.termination==='timeout'?' (제한)':'';
  $('results-content').classList.remove('empty-results');
  $('results-content').innerHTML=`<table><thead><tr><th></th><th class="mint">${dataset.parameters.variant==='B'?bLabel():'PD 제어'}</th><th class="orange">${dataset.parameters.variant==='B'?'줄 길이 고정':'무제어'}</th></tr></thead><tbody><tr><td>비행 시간</td><td>${p.duration.toFixed(2)} s${end(p)}</td><td>${o.duration.toFixed(2)} s${end(o)}</td></tr><tr><td>평균 낙하속도</td><td>${p.mean_descent_speed.toFixed(2)} m/s</td><td>${o.mean_descent_speed.toFixed(2)} m/s</td></tr><tr><td>공기 대비 평균 하강</td><td>${p.mean_air_descent_speed.toFixed(2)} m/s</td><td>${o.mean_air_descent_speed.toFixed(2)} m/s</td></tr><tr><td>기울기 RMS</td><td>${p.rms_tilt.toFixed(1)}°</td><td>${o.rms_tilt.toFixed(1)}°</td></tr><tr><td>최대 기울기</td><td>${p.max_tilt.toFixed(1)}°</td><td>${o.max_tilt.toFixed(1)}°</td></tr>${dataset.parameters.variant==='B'?`<tr><td>최종 수평 오차</td><td>${p.horizontal_error.toFixed(2)} m</td><td>${o.horizontal_error.toFixed(2)} m</td></tr>`:''}<tr><td>뒤집힘</td>${[p,o].map(s=>`<td class="${s.inverted?'result-yes':'result-no'}">${s.inverted?'발생':'없음'}</td>`).join('')}</tr></tbody></table>`;
}
$('settings').onsubmit=async e=>{
  e.preventDefault();if(busy||!$('settings').reportValidity())return;
  const values=Object.fromEntries([...new FormData($('settings')).entries()].map(([k,v])=>[k,['variant','b_controller','wind_mode','wind_clip'].includes(k)?v:Number(v)]));
  values.seconds=values.variant==='B'?8:5;
  $('variant').disabled=true;$('b-controller').disabled=true;busy=true;playing=false;$('run').disabled=true;$('run').innerHTML='계산 중…';$('status').textContent='계산 중';$('run-note').textContent='두 실험의 낙하 궤적을 계산합니다';
  try{
    const response=await fetch('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});
    if(!response.ok){const error=await response.json();throw new Error(typeof error.detail==='string'?error.detail:'설정값을 확인해주세요.');}
    dataset=await response.json();
    $('wind-source').textContent=dataset.wind_source?`실측: ${dataset.wind_source.site}, 높이 ${dataset.wind_source.height_m}m · ${dataset.wind_source.clip.start_utc}부터 10초. 원본 풍속 그대로, 최대 0.2초 간격 선형 보간. 3m 바람 예측 아님. DOI: 10.5281/zenodo.18268508`:'합성 시험 바람 · 공간적으로 균일';
    initial=dataset.runs.pd.frames[0];ensureModels(dataset.geometry);
    for(const mode of ['pd','off']){models[mode].track.geometry.dispose();models[mode].track.geometry=new THREE.BufferGeometry().setFromPoints(dataset.runs[mode].frames.map(f=>new THREE.Vector3(f.center[0],f.center[1],f.center[2])));}
    resetCamera();duration=Math.max(...Object.values(dataset.runs).map(r=>r.summary.duration));playTime=0;playing=true;
    $('timeline').max=duration;for(const id of ['play','rewind','timeline','download'])$(id).disabled=false;
    modeUI();resultsTable();$('run-note').textContent='계산 완료 · 재생 속도를 조절해보세요';$('footer-status').textContent=`${values.height.toFixed(1)} m / ${values.tilt}° / SEED ${values.seed}`;
  }catch(error){toast(`실험을 실행하지 못했습니다. ${error.message}`);$('run-note').textContent='실행 실패 · 다시 시도해주세요';}
  finally{$('variant').disabled=false;$('b-controller').disabled=false;busy=false;$('run').disabled=false;$('run').innerHTML='<span>▶</span> 실험 실행 <span class="arrow">↗</span>';renderState();}
};
$('download').onclick=()=>{
  if(!dataset)return;
  const isB=dataset.parameters.variant==='B';
  const header=isB?'mode,algorithm,time_s,height_m,tilt_deg,descent_speed_m_s,rest_1_m,rest_2_m,rest_3_m,actual_1_m,actual_2_m,actual_3_m,target_1_m,target_2_m,target_3_m,reel_in_1_m_s,reel_in_2_m_s,reel_in_3_m_s,tension_1_N,tension_2_N,tension_3_N,slack_1,slack_2,slack_3,load_limited_1,load_limited_2,load_limited_3,payload_x_m,payload_y_m,payload_z_m,target_x_m,target_y_m':'mode,time_s,height_m,tilt_deg,descent_speed_m_s,spool_x_mm,spool_y_mm,tension_px_N,tension_py_N,tension_nx_N,tension_ny_N';
  const rows=[header+',wind_x_m_s,wind_y_m_s,wind_z_m_s,air_descent_speed_m_s'];
  for(const [mode,run]of Object.entries(dataset.runs))for(const f of run.frames){
    rows.push((isB?[mode,mode==='off'?'fixed_lengths':dataset.parameters.b_controller,f.t,f.height,f.tilt,f.speed,...f.line_rest,...f.line_actual,...f.line_target,...f.winch_speed,...f.tension,...f.line_slack,...f.winch_stalled,...f.payload_local,...f.target_xy]:[mode,f.t,f.height,f.tilt,f.speed,...f.spool,...f.tension]).concat(f.wind,[f.air_descent_speed]).join(','));
  }
  const url=URL.createObjectURL(new Blob([rows.join('\n')],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='clover-experiment.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function drawCharts(){
  for(const key of ['tilt','height']){
    const canvas=$(`${key}-chart`),rect=canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio,2);
    if(!rect.width||!rect.height)continue;
    const width=Math.round(rect.width*dpr),height=Math.round(rect.height*dpr);if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
    const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,rect.width,rect.height);
    const w=rect.width,h=rect.height,left=26,right=9,top=10,bottom=19,pw=w-left-right,ph=h-top-bottom;
    const max=dataset?Math.max(key==='tilt'?30:1,...Object.values(dataset.runs).flatMap(r=>r.frames.map(f=>f[key])))*1.07:key==='tilt'?90:3;
    const maxTime=duration||1;ctx.font='9px -apple-system, sans-serif';
    for(let i=0;i<3;i++){const y=top+ph*i/2;ctx.strokeStyle='#263640';ctx.lineWidth=.6;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(w-right,y);ctx.stroke();ctx.fillStyle='#5f7684';ctx.fillText((max*(1-i/2)).toFixed(0),0,y+3);}
    ctx.fillStyle='#5f7684';ctx.fillText('0',left,h-3);ctx.fillText(`${maxTime.toFixed(2)} s`,w-40,h-3);
    if(dataset){for(const mode of ['off','pd']){const frames=dataset.runs[mode].frames;ctx.strokeStyle=mode==='pd'?'#7ce4bd':'#eda975';ctx.lineWidth=1.7;ctx.beginPath();frames.forEach((f,i)=>{const x=left+pw*f.t/maxTime,y=top+ph*(1-f[key]/max);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();}const x=left+pw*playTime/maxTime;ctx.strokeStyle='#bcccd588';ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,top+ph);ctx.stroke();ctx.setLineDash([]);}
  }
}
function resizeViews(){
  for(const [element,render,cam] of [[viewport,renderer,camera],[detailViewport,detailRenderer,detailCamera]]){
    const {width,height}=element.getBoundingClientRect();if(!width||!height)continue;
    render.setSize(width,height);cam.aspect=width/height;cam.updateProjectionMatrix();
  }
}
new ResizeObserver(()=>{resizeViews();drawCharts();}).observe(viewport);
let last=performance.now();
function animate(now){const dt=Math.min((now-last)/1000,.1);last=now;if(playing){playTime=Math.min(duration,playTime+dt*Number($('rate').value));if(playTime>=duration)playing=false;renderState();}controls.update();updateScene(cameraMode);renderer.render(scene,camera);if(cameraMode==='world'){detailControls.update();updateScene('follow');detailRenderer.render(scene,detailCamera);}requestAnimationFrame(animate);}
requestAnimationFrame(animate);
async function init(){try{const [healthResponse,initialResponse]=await Promise.all([fetch('/api/health'),fetch(`/api/initial?variant=${$('variant').value}`)]);if(!healthResponse.ok||!initialResponse.ok)throw new Error('서버 응답 오류');const health=await healthResponse.json();const data=await initialResponse.json();initial=data.frame;ensureModels(data.geometry);resetCamera();$('connection').innerHTML='<i></i>엔진 연결됨';$('connection').title=`MuJoCo ${health.version}`;renderState();}catch(error){$('connection').textContent='연결 실패';toast(`서버 연결에 실패했습니다. ${error.message}`);}}
function setTarget(x,y){
  if(x<-.06-1e-8||x>.12+1e-8||Math.abs(y)>(.12-x)/Math.sqrt(3)+1e-8){toast('삼각형 안을 선택해주세요.');return;}
  if(busy)return;
  $('b-controller').value='manual';modeUI();
  $('target-x').value=String(x*1000);$('target-y').value=String(y*1000);
  $('target-dot').setAttribute('cx',120+x/.0012);$('target-dot').setAttribute('cy',110-y/.0012);
  $('target-values').textContent=`X ${(x*1000).toFixed(1)} · Y ${(y*1000).toFixed(1)} mm`;
  $('run-note').textContent='목표 변경됨 · 실행하면 반영됩니다';
}
$('target-map').onclick=e=>{const point=new DOMPoint(e.clientX,e.clientY).matrixTransform($('target-map').getScreenCTM().inverse());setTarget((point.x-120)*.0012,(110-point.y)*.0012);};
$('target-map').onkeydown=e=>{const d={ArrowRight:[.005,0],ArrowLeft:[-.005,0],ArrowUp:[0,.005],ArrowDown:[0,-.005]}[e.key];if(d){e.preventDefault();setTarget(Number($('target-x').value)/1000+d[0],Number($('target-y').value)/1000+d[1]);}};
$('center-target').onclick=()=>setTarget(0,0);
$('b-example').onclick=()=>{
  if(busy)return;
  $('line-length').value=169.7;$('drive-speed').value=40;
  $('height-input').value=3;$('tilt-input').value=5;$('seed').value=11;$('medium').value='1.225';
  for(const el of document.querySelectorAll('[name="wind_x"],[name="wind_y"]'))el.value=0;
  $('wind-mode').value='constant';$('b-controller').value='optimized';updateInputs();modeUI();$('settings').requestSubmit();
};
$('b-controller').onchange=()=>{modeUI();$('run-note').textContent='알고리즘 변경됨 · 실행하면 반영됩니다';};
function bLabel(){return ({manual:'목표 이동',p:'P 보정',pd:'PD 보정',aero_pd:'공기력 보상',optimized:'튜닝 PD',position:'원점 위치 제어',predictive:'예측 제동'})[dataset?.parameters.b_controller||$('b-controller').value];}
function modeUI(){
  const b=$('variant').value==='B';$('b-controls').hidden=!b;$('a-gains').hidden=b;
  document.querySelector('[data-view="pd"]').textContent=b?bLabel():'PD 제어';document.querySelector('[data-view="off"]').textContent=b?'줄 길이 고정':'무제어';
  for(const el of document.querySelectorAll('.legend .mint,#model-labels .mint'))el.textContent=b?'● '+bLabel():'● PD 제어';
  for(const el of document.querySelectorAll('.legend .orange,#model-labels .orange'))el.textContent=b?'● 줄 길이 고정':'● 무제어';
  $('project-name').textContent=b?'B · 고정 돔':'A · 물방울 날개';$('model-spec').textContent=b?'24 cm · 높이 6 cm · 예비 CFD':'24 cm · 8.2 g · A';
}
$('variant').onchange=async()=>{
  playing=false;dataset=null;initial=null;duration=0;playTime=0;
  for(const mode of ['pd','off']){if(models[mode]){for(const object of [models[mode].group,models[mode].track]){scene.remove(object);object.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});}delete models[mode];}}
  for(const id of ['play','rewind','timeline','download'])$(id).disabled=true;
  $('results-content').textContent='새 버전에서 실험을 시작하세요.';$('run-note').textContent='동일 조건으로 두 제어 모드 비교';
  modeUI();$('run').disabled=true;$('variant').disabled=true;await init();$('run').disabled=false;$('variant').disabled=false;
};
modeUI();init();
