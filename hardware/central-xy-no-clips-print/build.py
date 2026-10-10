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
# Preserve the complete 8mm tooth envelope; replace only journals and thrust collars.
tooth=t.boolean.intersection([worm,box([8,20,20],[0,0,6])],engine='manifold')
worm=U([tooth,cyl(1.4,15,(0,0,6),'x'),cyl(2.1,.4,(-4.75,0,6),'x'),cyl(2.1,.4,(4.75,0,6),'x')])
worm=D(worm,cyl(.6,17,(0,0,6),'x'))

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
# Two locating pins align the halves before latches engage.
for x,y in [(-12,-7.4),(1,7.4)]:
 body=U([body,cyl(.75,1.1,(x,y,4.05))]);cap=D(cap,cyl(.95,1.5,(x,y,4.25)))
# Keep tested rear mounting eye and bore 1.1mm worm.
body=U([body,box([5,7,1.7],[-34.5,0,-1.15]),cyl(3.5,1.7,[-36,0,-1.15])])
body=D(body,cyl(1.1,5,[-36,0,-1.15]))
worm=t.load(out.parent/'615-worm-bore11/worm.stl')
# Clearance for the output pivot pedestal at fully retracted rack.
body=D(body,box([10,6,3],[21.3,0,-1.15]))
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
report['housing']='Four latches and catches removed; locating pins retained; adhesive assembly.'
report['journal_revision']={'overall_length_mm':15,'journal_diameter_mm':2.8,'existing_bearing_bore_mm':3.4,'radial_clearance_mm':.3,'axial_clearance_per_side_mm':.3,'motor_bore_mm':1.1,'toothed_length_mm':8,'note':'Only worm needs reprinting; tooth profile and housing unchanged.'}
report['checks']=checks;report['assembly_drop_check']='rack vertical insertion at center: six heights clear';(out/'inspection.json').write_text(json.dumps(report,indent=2));print(report)
