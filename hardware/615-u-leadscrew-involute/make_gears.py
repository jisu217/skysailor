from pathlib import Path
import sys,json,math
import numpy as np,trimesh as t,cadquery as cq
out=Path(__file__).resolve().parent;sys.path.insert(0,str(out/'vendor'))
from cq_gears import SpurGear
pa=25;backlash=.06/(.5*math.tan(math.radians(pa)))
for name,z,bore,phase,y in [('large-gear',36,4.1,0,0),('motor-gear',12,1.1,15,-12)]:
 gear=SpurGear(module=.5,teeth_number=z,width=2,pressure_angle=pa,backlash=backlash,clearance=.1,bore_d=bore)
 solid=gear.build();assert solid.isValid()
 cq.exporters.export(solid,str(out/(name+'.step')))
 cq.exporters.export(solid,str(out/(name+'-print.stl')),tolerance=.005,angularTolerance=.05)
 m=t.load(out/(name+'-print.stl'));assert m.is_volume
 m.apply_transform(t.transformations.rotation_matrix(math.radians(phase),[0,0,1]))
 mat=np.array([[0,0,1,-3.5],[1,0,0,y],[0,1,0,10],[0,0,0,1]],float);m.apply_transform(mat)
 m.export(out/(name+'-assembled.stl'))
 print(name,len(m.faces),'volume',m.volume,flush=True)
# One driven-tooth period equals three pinion-tooth periods? 10deg driven =30deg driver, one tooth each.
a=t.load(out/'large-gear-assembled.stl');b=t.load(out/'motor-gear-assembled.stl');results=[]
for angle in np.linspace(0,10,41):
 aa=a.copy();bb=b.copy();aa.apply_transform(t.transformations.rotation_matrix(math.radians(angle),[1,0,0],point=[0,0,10]));bb.apply_transform(t.transformations.rotation_matrix(math.radians(-3*angle),[1,0,0],point=[0,-12,10]))
 hit=t.boolean.intersection([aa,bb],engine='manifold');v=0 if hit.is_empty else abs(float(hit.volume));results.append(v)
 assert v<.0001,(angle,v)
(out/'gear-inspection.json').write_text(json.dumps({'library':'cq_gears','module_mm':.5,'teeth':[12,36],'pressure_angle_deg':25,'center_distance_mm':12,'face_width_mm':2,'tooth_thickness_reduction_each_mm':.06,'nominal_pair_pitch_backlash_mm':.12,'extra_root_clearance_mm':.1,'mesh_samples':41,'max_overlap_mm3':max(results)},indent=2))
print('41 sampled gear phases clear',flush=True)
