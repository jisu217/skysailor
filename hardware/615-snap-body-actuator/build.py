from pathlib import Path
import trimesh as t,numpy as np,json
out=Path(__file__).resolve().parent;src=out.parent/'615-slotted-worm-actuator'
def box(d,p):
 m=t.creation.box(d);m.apply_translation(p);return m
def cyl(r,h,p,axis='z'):
 m=t.creation.cylinder(radius=r,height=h,sections=64)
 if axis=='x':m.apply_transform(t.geometry.align_vectors([0,0,1],[1,0,0]))
 m.apply_translation(p);return m
def U(ms):return t.boolean.union(ms,engine='manifold')
def D(a,*b):return t.boolean.difference([a,*b],engine='manifold')
rack=t.load(src/'rack.stl',force='mesh');worm=t.load(src/'worm.stl',force='mesh')
# Lower shell is open above: the rack drops over narrow posts through its slot.
base=[box([54,17,1.7],[-7,0,-1.15])]
for y in [-7.4,7.4]:base.append(box([40,2.2,3.9],[-5,y,1.65]))
for x in [-5,5]:base.append(cyl(1,1.6,(x,0,.5)))
for x in [-6.5,6.5]:base.append(D(box([2.5,1.8,6.3],[x,0,2.85]),cyl(1.7,4,(x,0,6),'x')))
body=U(base)
# Upper shell carries retaining ledges, bearing upper halves and axial-entry motor cradle.
upper=[]
for y in [-7.4,7.4]:upper.append(box([40,2.2,5.4],[-5,y,6.3]))
for x in [-6.5,6.5]:upper.append(box([2.5,17,3],[x,0,7.5]))
for y in [-5.9,5.9]:upper.append(box([12,1.6,1.4],[0,y,4.5]))
upper.append(box([17,17,5.2],[-16.5,0,6.4]))
cap=U(upper);cap=D(cap,cyl(1.7,18,(0,0,6),'x'),cyl(3.15,19,(-16.5,0,6),'x'))
# Four outward-flexing cantilever latches; positive hook retention, no screws.
# 0.8mm beam, 0.65mm hook projection, 0.2mm vertical seating clearance.
for x in [-20,10]:
 for side in [-1,1]:
  foot=box([6,2.4,1.3],[x,side*9,-1.35])
  beam=box([4,.8,9.4],[x,side*9.75,2.9])
  yz=[(8.7,6.4),(9.55,6.4),(9.55,7.6),(9.35,7.6),(8.7,6.7)]
  points=[[xx,side*y,z] for xx in [x-2,x+2] for y,z in yz]
  hook=t.convex.convex_hull(np.array(points))
  body=U([body,foot,beam,hook])
  catch=box([4,1,0.8],[x,side*8.7,5.8])
  cap=U([cap,catch])
# Two locating pins align the halves before latches engage.
for x,y in [(-12,-7.4),(1,7.4)]:
 body=U([body,cyl(.75,1.1,(x,y,4.05))]);cap=D(cap,cyl(.95,1.5,(x,y,4.25)))
parts={'body':body,'cap':cap,'rack':rack,'worm':worm};report={}
for name,m in parts.items():
 assert m.is_watertight and m.is_volume and len(m.split())==1,name
 m.export(out/(name+'.stl'));(out/(name+'.json')).write_text(json.dumps({'vertices':m.vertices.round(4).tolist(),'faces':m.faces.tolist()},separators=(',',':')))
 report[name]={'dimensions_mm':m.extents.tolist(),'volume_mm3':float(m.volume)}
checks=[]
for s in np.linspace(-6,6,13):
 r=rack.copy();r.apply_translation([s,0,0]);w=worm.copy();w.apply_transform(t.transformations.rotation_matrix(-s*2*np.pi/2.5,[1,0,0],point=[0,0,6]))
 row={'travel_mm':float(s)}
 for n,b in [('lower',body),('upper',cap),('worm',w)]:
  hit=t.boolean.intersection([r,b],engine='manifold');vol=0 if hit.is_empty else abs(float(hit.volume));row[n]=vol;assert vol<.001,row
 checks.append(row)
# Drop-in assembly path: rack can be lowered vertically without crossing lower shell material.
for dz in [0,1,2,4,6,10]:
 r=rack.copy();r.apply_translation([0,0,dz]);h=t.boolean.intersection([r,body],engine='manifold');assert h.is_empty or abs(h.volume)<.001,('rack insertion',dz)
h=t.boolean.intersection([body,cap],engine='manifold');assert h.is_empty or abs(h.volume)<.001,'seated shell interference'
report['snap_fit']={'beam_mm':.8,'hook_overlap_mm':.5,'vertical_clearance_mm':.2,'note':'Elastic insertion and PLA fatigue not physically validated; geometric seated clearance only.'}
report['checks']=checks;report['assembly_drop_check']='rack vertical insertion at center: six heights clear';(out/'inspection.json').write_text(json.dumps(report,indent=2));print(report)
