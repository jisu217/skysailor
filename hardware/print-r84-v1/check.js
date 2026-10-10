
(async()=>{
 const root=document.getElementById('print-r84'),view=root.querySelector('.gear-view');
 if(!window.THREE){root.querySelector('[data-status]').textContent='3D 표시를 불러오지 못했습니다.';return;}
 const T=window.THREE,scene=new T.Scene(),camera=new T.PerspectiveCamera(38,1,.1,500),renderer=new T.WebGLRenderer({alpha:true,antialias:true});
 renderer.setPixelRatio(Math.min(devicePixelRatio,2));view.appendChild(renderer.domElement);camera.up.set(0,0,1);
 const data=JSON.parse(root.querySelector('[data-mesh]').textContent);
 async function arr(s,Type,delta=false){const zipped=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const stream=new Blob([zipped]).stream().pipeThrough(new DecompressionStream('gzip'));const shuffled=new Uint8Array(await new Response(stream).arrayBuffer());const count=shuffled.length/4,bytes=new Uint8Array(shuffled.length);for(let j=0;j<4;j++)for(let i=0;i<count;i++)bytes[4*i+j]=shuffled[j*count+i];const result=new Type(bytes.buffer);if(delta)for(let i=1;i<result.length;i++)result[i]+=result[i-1];return result;}
 const geometries={};for(const [name,d] of Object.entries(data)){const g=new T.BufferGeometry();g.setAttribute('position',new T.BufferAttribute(await arr(d.v,Float32Array),3));g.setIndex(new T.BufferAttribute(await arr(d.f,Uint32Array,true),1));g.computeVertexNormals();geometries[name]=g;}
 const meshes={};function add(name,type,matrix){const mesh=new T.Mesh(geometries[type],new T.MeshStandardMaterial({roughness:.7,flatShading:true}));if(matrix)mesh.applyMatrix4(matrix);scene.add(mesh);meshes[name]=mesh;}
 for(const name of Object.keys(data))add(name,name);
 const grid=new T.GridHelper(256,32);grid.rotation.x=Math.PI/2;grid.position.z=-.03;scene.add(grid);
 const ambient=new T.AmbientLight(),light=new T.DirectionalLight();ambient.intensity=1.8;light.intensity=2.4;light.position.set(-15,-20,40);scene.add(ambient,light);
 const swatches={};for(const token of ['--viz-series-1','--viz-series-2','--foreground','--background']){const s=document.createElement('span');s.style.color=`var(${token})`;s.hidden=true;root.appendChild(s);swatches[token]=s;}
 const color=t=>new T.Color(getComputedStyle(swatches[t]).color);
 let yaw=-1.1,pitch=.8,distance=220,drag=null;
 function restore(s){const p=s?.privateContent;if(p){if(Number.isFinite(p.yaw))yaw=p.yaw;if(Number.isFinite(p.pitch))pitch=Math.max(-1.56,Math.min(1.56,p.pitch));if(Number.isFinite(p.distance))distance=Math.max(25,Math.min(450,p.distance));}}
 restore(window.openai?.widgetState);
 function save(){window.openai?.setWidgetState({modelContent:{design:'print-r84-v1',gear_count:2,spool_core_radius_mm:3,body_height_mm:7,spool_height_mm:3},privateContent:{yaw,pitch,distance}})?.catch(()=>{});}
 function render(){grid.material.color.copy(color('--foreground'));grid.material.transparent=true;grid.material.opacity=.12;for(const [name,m] of Object.entries(meshes)){m.material.color.copy(name.endsWith('frame')||name.startsWith('marker')?color('--foreground').lerp(color('--background'),.65):name.startsWith('worm')||name.startsWith('motor')||name.startsWith('shaft')?color('--viz-series-2'):color('--viz-series-1'));}const illumination=color('--background').lerp(color('--foreground'),.5);ambient.color.copy(illumination);light.color.copy(illumination);camera.position.set(distance*Math.cos(pitch)*Math.cos(yaw),distance*Math.cos(pitch)*Math.sin(yaw),1+distance*Math.sin(pitch));camera.lookAt(0,0,3.5);renderer.render(scene,camera);}
 new ResizeObserver(()=>{const w=view.clientWidth,h=Math.max(200,view.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();render();}).observe(view);
 view.onpointerdown=e=>{drag=[e.clientX,e.clientY];view.setPointerCapture(e.pointerId);};
 view.onpointermove=e=>{if(!drag)return;yaw-=(e.clientX-drag[0])*.009;pitch=Math.max(-1.56,Math.min(1.56,pitch+(e.clientY-drag[1])*.009));drag=[e.clientX,e.clientY];render();};
 view.onpointerup=()=>{drag=null;save();};view.onpointercancel=()=>{drag=null;};
 let timer;view.addEventListener('wheel',e=>{e.preventDefault();distance=Math.max(25,Math.min(450,distance+e.deltaY*.025));render();clearTimeout(timer);timer=setTimeout(save,250);},{passive:false});
 root.querySelectorAll('button').forEach(b=>b.onclick=()=>{pitch=b.dataset.view==='top'?1.56:b.dataset.view==='side'?0:.8;yaw=-1.1;render();save();});
 window.addEventListener('openai:set_globals',e=>{restore(e.detail?.globals?.widgetState);render();});new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['class','style','data-theme']});render();
})();
