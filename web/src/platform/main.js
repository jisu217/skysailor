import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const $=id=>document.getElementById(id),scene=new T.Scene();scene.background=new T.Color('#101c24');
const camera=new T.PerspectiveCamera(40,innerWidth/innerHeight,1,3000);camera.position.set(460,290,510);
const renderer=new T.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);document.body.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(-55,-60,0);controls.enableDamping=true;
scene.add(new T.HemisphereLight(0xdaf5ff,0x344449,2.5));const light=new T.DirectionalLight(0xffffff,3);light.position.set(200,400,300);scene.add(light);
const mat=(color,extra={})=>new T.MeshStandardMaterial({color,roughness:.45,...extra});const white=mat('#c3d6dc'),teal=mat('#76d7be'),gold=mat('#f4ba61');
function ball(r,m,parent=scene){const o=new T.Mesh(new T.SphereGeometry(r,24,16),m);parent.add(o);return o}
function rod(a,b,r,m,parent=scene){const o=new T.Mesh(new T.CylinderGeometry(r,r,1,16),m);parent.add(o);setRod(o,a,b);return o}
function setRod(o,a,b){const d=new T.Vector3().subVectors(b,a);o.position.copy(a).add(b).multiplyScalar(.5);o.scale.y=d.length();o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),d.normalize())}
function ring(radius,tube,m,parent=scene){const o=new T.Mesh(new T.TorusGeometry(radius,tube,12,96),m);o.rotation.x=Math.PI/2;parent.add(o);return o}
const dome=new T.Group();scene.add(dome);const radius=(190*190+80*80)/160,theta=Math.asin(190/radius);const shell=new T.Mesh(new T.SphereGeometry(radius,64,24,0,Math.PI*2,0,theta),mat('#88c8c3',{transparent:true,opacity:.16,side:T.DoubleSide,depthWrite:false}));shell.position.y=80-radius;dome.add(shell);ring(190,2,teal,dome);
const base=new T.Group();scene.add(base);ring(190,2,white,base);
const joint=ball(12,gold);const mass=joint;
const actuators=[],mounts=[];
for(let i=0;i<3;i++){const angle=i*2*Math.PI/3;const a=new T.Vector3(190*Math.cos(angle),0,190*Math.sin(angle));const b=new T.Vector3(30*Math.cos(angle),0,30*Math.sin(angle));const m=mat(['#ef8585','#7aafff','#eed177'][i]);mounts.push({a,b});actuators.push({body:rod(a,b,3,m),shaft:rod(a,b,1.5,white),endA:ball(3,m),endB:ball(3,m)});}
const grid=new T.GridHelper(700,14,0x38515b,0x243b45);grid.position.y=-240;scene.add(grid);
let auto=false;function update(){const x=+$('moveX').value,z=+$('moveZ').value,drop=+$('drop').value;for(const [id,v,unit] of [['moveX',x,'mm'],['moveZ',z,'mm'],['drop',drop,'mm']])$(id+'V').textContent=`${v} ${unit}`;
joint.position.set(x,-drop,z);dome.visible=$('dome').checked;
const lengths=[];mounts.forEach(({a},i)=>{const end=joint.position,mid=a.clone().lerp(end,.55),act=actuators[i];setRod(act.body,a,mid);setRod(act.shaft,mid,end);act.endA.position.copy(a);act.endB.position.copy(end);lengths.push(a.distanceTo(end).toFixed(1));});$('status').textContent=`액추에이터 길이: ${lengths.join(' / ')} mm · 추 수평 이동: ${Math.hypot(mass.position.x,mass.position.z).toFixed(1)} mm`;}
for(const id of ['moveX','moveZ','drop','dome'])$(id).oninput=()=>{auto=false;update()};$('animate').onclick=()=>auto=!auto;$('zero').onclick=()=>{auto=false;for(const id of ['moveX','moveZ'])$(id).value=0;update()};$('top').onclick=()=>{camera.position.set(0,500,.01);controls.target.set(0,-50,0)};$('side').onclick=()=>{camera.position.set(420,80,180);controls.target.set(0,-50,0)};window.onresize=()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)};update();renderer.setAnimationLoop(t=>{if(auto){$('moveX').value=Math.round(25*Math.sin(t/1400));$('moveZ').value=Math.round(25*Math.cos(t/1400));update()}controls.update();renderer.render(scene,camera)});
