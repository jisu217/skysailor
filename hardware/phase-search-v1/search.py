from pathlib import Path
import numpy as np,trimesh,json
out=Path(__file__).resolve().parent
# Use original high-resolution generation, without exports or viewer construction.
src=(out.parent/'fixed-axle-half-phase-v1/build.py').read_text();ns={'__file__':str(out/'unused.py')};exec(src[:src.index('# No guide flanges:')],ns)
low=ns['band'](0,2);top=ns['band'](5,7)
worm=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl')
T=np.array([[0,0,1,-3],[1,0,0,-8.5],[0,1,0,3.5],[0,0,0,1]])
def placed(phi):
 w=worm.copy();w.apply_transform(trimesh.transformations.rotation_matrix(phi,[0,0,1]));w.apply_transform(T);return w
w0=placed(0)
def volume(a,b):
 m=trimesh.boolean.intersection([a,b],engine='manifold');return float(m.volume) if len(m.faces) else 0.
def lower(deg,turn=0):
 m=low.copy();m.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(deg-7.5)+turn,[0,0,1]));return m
rows=[]
for deg in np.arange(0,15,.5):rows.append([float(deg),volume(lower(deg),w0)])
best=min(rows,key=lambda x:x[1])[0]
for deg in np.arange(best-.5,best+.501,.05):rows.append([float(deg%15),volume(lower(deg%15),w0)])
rows.sort(key=lambda x:x[1]);candidates=list(dict.fromkeys([7.5]+[round(x[0],4) for x in rows[:5]]))
print('Static best',rows[:5],flush=True)
# Candidate 24:1 kinematic relation, both possible signs; no claim this ratio is conjugate.
results=[]
for sign in [-1,1]:
 for deg in candidates:
  vals=[]
  for phi in np.linspace(0,2*np.pi,13)[:-1]:
   w=placed(phi);r=sign*phi/24
   upper=top.copy();upper.apply_transform(trimesh.transformations.rotation_matrix(r,[0,0,1]))
   vals.append(volume(lower(deg,r),w)+volume(upper,w))
  results.append(dict(phase_deg=deg,sign=sign,max_overlap_mm3=max(vals),mean_overlap_mm3=float(np.mean(vals)),overlap_by_pose_mm3=vals))
 print('Direction',sign,'completed',flush=True)
report=dict(static_top_overlap_mm3=volume(top,w0),static_search=rows,dynamic_results=results,notes='12 sampled poses per worm revolution, assumed 24:1. Interference only, not contact/load validation.')
(out/'results.json').write_text(json.dumps(report,indent=2));print('Dynamic best',min(results,key=lambda x:(x['max_overlap_mm3'],x['mean_overlap_mm3'])),flush=True)
