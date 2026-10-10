import * as T from 'three';
export function capGeometry(){
 const pts=[];const vertex=(theta,phi)=>[.15*Math.sin(theta)*Math.cos(phi),.15*Math.sin(theta)*Math.sin(phi),.15*Math.cos(theta)-.09];
 const limit=Math.acos(.6);
 for(let i=0;i<20;i++)for(let j=0;j<80;j++){
  const a=vertex(limit*i/20,2*Math.PI*j/80),b=vertex(limit*(i+1)/20,2*Math.PI*j/80),c=vertex(limit*(i+1)/20,2*Math.PI*(j+1)/80),d=vertex(limit*i/20,2*Math.PI*(j+1)/80);
  pts.push(...a,...b,...c,...a,...c,...d);
 }
 const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(pts,3));g.computeVertexNormals();return g;
}
// Arc direction follows the right-hand rule about the world-space vector.
export function rotationArrow(color,radius){
 const group=new T.Group(),positions=new Float32Array(65*3);
 const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(positions,3));
 const material=new T.LineBasicMaterial({color,depthTest:false,transparent:true,opacity:.95});
 const arc=new T.Line(geometry,material);arc.frustumCulled=false;arc.renderOrder=12;group.add(arc);
 const tip=new T.Mesh(new T.ConeGeometry(.004,.012,12),new T.MeshBasicMaterial({color,depthTest:false}));tip.renderOrder=12;group.add(tip);
 return {group,arc,tip,radius};
}
export function updateRotationArrow(item,vector,center,fraction,visible){
 const magnitude=vector.length();item.group.visible=visible&&magnitude>1e-9;
 if(!item.group.visible)return;
 item.group.position.copy(center);item.group.quaternion.setFromUnitVectors(new T.Vector3(0,0,1),vector.clone().normalize());
 const sweep=Math.min(1,fraction)*Math.PI*1.6,r=item.radius,attr=item.arc.geometry.attributes.position;
 for(let i=0;i<=64;i++){const angle=sweep*i/64;attr.setXYZ(i,r*Math.cos(angle),r*Math.sin(angle),0);}attr.needsUpdate=true;
 item.tip.position.set(r*Math.cos(sweep),r*Math.sin(sweep),0);
 item.tip.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),new T.Vector3(-Math.sin(sweep),Math.cos(sweep),0));
 item.tip.scale.setScalar(Math.min(1,sweep/.3));
}
