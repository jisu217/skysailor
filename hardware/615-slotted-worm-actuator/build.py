from pathlib import Path
import numpy as np,trimesh as tm,json
out=Path(__file__).resolve().parent
LEAD=2.5;CLEAR=.18
def box(dim,pos):
 m=tm.creation.box(dim);m.apply_translation(pos);return m
def cyl(r,h,pos,axis='z'):
 m=tm.creation.cylinder(radius=r,height=h,sections=64)
 if axis=='x':m.apply_transform(tm.geometry.align_vectors([0,0,1],[1,0,0]))
 m.apply_translation(pos);return m
def union(ms):return tm.boolean.union(ms,engine='manifold')
def diff(a,*bs):return tm.boolean.difference([a,*bs],engine='manifold')
def helix(length,extra=0):
 nx=int(length*24)+1;nt=96;x=np.linspace(-length/2,length/2,nx);theta=np.arange(nt)*2*np.pi/nt
 X,TH=np.meshgrid(x,theta,indexing='ij');q=np.abs((TH/(2*np.pi)-X/LEAD+.5)%1-.5);r=3.4+np.clip((.38-q)/.28,0,1)*1.1+extra
 verts=np.column_stack([X.ravel(),(r*np.cos(TH)).ravel(),(6+r*np.sin(TH)).ravel()]);faces=[]
 for i in range(nx-1):
  for j in range(nt):
   a=i*nt+j;b=i*nt+(j+1)%nt;c=(i+1)*nt+j;d=(i+1)*nt+(j+1)%nt;faces.extend([[a,b,c],[b,d,c]])
 verts=np.vstack([verts,[-length/2,0,6],[length/2,0,6]])
 for j in range(nt):faces.extend([[nx*nt,(j+1)%nt,j],[nx*nt+1,(nx-1)*nt+j,(nx-1)*nt+(j+1)%nt]])
 m=tm.Trimesh(verts,faces,process=True);m.fix_normals();return m
worm=union([helix(8),cyl(1.5,13,(0,0,6),'x'),cyl(2.1,.6,(-4.85,0,6),'x'),cyl(2.1,.6,(4.85,0,6),'x')]);worm=diff(worm,cyl(.6,15,(0,0,6),'x'))
print('Worm built',flush=True)
rack=box([36,12,3.5],[0,0,1.75]);rack=diff(rack,helix(42,CLEAR))
slot=union([box([26,2.4,8],[0,0,1.5]),cyl(1.2,8,(-13,0,1.5)),cyl(1.2,8,(13,0,1.5))]);rack=diff(rack,slot)
# Output extension and eye. Rack guide slot stays separate from attachment hole.
rack=union([rack,box([8,6,3.5],[21,0,1.75]),cyl(3,3.5,(25,0,1.75))]);rack=diff(rack,cyl(1.1,8,(25,0,2)))
print('Matched concave rack built',flush=True)
bodyparts=[box([54,17,1.7],[-7,0,-1.15])]
for y in [-7.4,7.4]:bodyparts.append(box([18,2.2,6.3],[0,y,2.85]))
for x in [-6.5,6.5]:bodyparts.append(box([2.5,17,2.2],[x,0,4.9]))
for x in [-5,5]:bodyparts.append(cyl(1,1.6,(x,0,.5)))
# Motor saddle, nominal diameter6 x length15; .2mm radial allowance.
cradle=diff(box([17,17,2.2],[-16.5,0,4.9]),cyl(3.2,19,(-16.5,0,6),'x'))
for y in [-7.4,7.4]:bodyparts.append(box([17,2.2,6.3],[-16.5,y,2.85]))
bodyparts.append(cradle);body=union(bodyparts);body=diff(body,cyl(1.7,20,(0,0,6),'x'))
cap=union([box([2.5,17,3],[x,0,7.5]) for x in [-6.5,6.5]]+[box([15.5,2.2,1.2],[0,y,8.4]) for y in [-7.4,7.4]])
cap=diff(cap,cyl(1.7,20,(0,0,6),'x'))
# Simple pilot holes for M1.6 hardware, not a qualified screw-fit specification.
for x in [-6.5,6.5]:
 for y in [-6.5,6.5]:
  body=diff(body,cyl(.65,5,(x,y,4)));cap=diff(cap,cyl(.9,5,(x,y,7.5)))
# Under-cap ledges retain rack edges while leaving .3mm running clearance.
ledges=[box([10,1.2,1.4],[0,y,4.5]) for y in [-5.8,5.8]]
body=union([body]+ledges+[box([10,1.3,2],[0,y,4]) for y in [-6.7,6.7]])
parts={'body':body,'rack':rack,'worm':worm,'cap':cap}
report={}
for name,m in parts.items():
 assert m.is_watertight and m.is_volume,(name,'invalid')
 m.export(out/(name+'.stl'));report[name]={'dimensions_mm':m.extents.tolist(),'volume_mm3':float(m.volume),'components':len(m.split())}
 (out/(name+'.json')).write_text(json.dumps({'vertices':m.vertices.round(4).tolist(),'faces':m.faces.tolist()},separators=(',',':')))
# Sample collision checks of nominal mesh geometries, not strength/friction validation.
checks=[]
for s in np.linspace(-6,6,13):
 moved=rack.copy();moved.apply_translation([s,0,0]);w=worm.copy();w.apply_transform(tm.transformations.rotation_matrix(-2*np.pi*s/LEAD,[1,0,0],point=[0,0,6]))
 row={'travel_mm':float(s)}
 for name,other in [('body',body),('cap',cap),('worm',w)]:
  hit=tm.boolean.intersection([moved,other],engine='manifold');row[name+'_overlap_mm3']=0 if hit.is_empty else abs(float(hit.volume))
 checks.append(row)
 assert max(row[k] for k in row if k.endswith('_mm3'))<.001,row
print(checks,flush=True)
report['checks']=checks;report['parameters']={'motor_nominal_mm':[6,15],'shaft_bore_mm':1.2,'worm_OD_mm':9,'worm_length_mm':8,'lead_mm':2.5,'stroke_mm':12,'radial_tooth_clearance_mm':CLEAR,'note':'Concept test parts. Nominal mesh collision checks only; no torque, backlash, thermal, printability or endurance validation.'}
(out/'inspection.json').write_text(json.dumps(report,indent=2));print(report['parameters'])
