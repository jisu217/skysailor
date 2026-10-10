from pathlib import Path
import numpy as np,json
p=Path(__file__).resolve().parent
s=(p/'search.py').read_text();exec(s[:s.index('rows=[]')])
rows=[]
for deg in np.arange(5.8,7.01,.2):
 vals=[]
 for phi in np.linspace(0,2*np.pi,25)[:-1]:
  w=placed(phi);vals.append(volume(lower(float(deg),-phi/24),w))
 rows.append(dict(phase_deg=round(float(deg),2),max_overlap_mm3=max(vals),mean_overlap_mm3=float(np.mean(vals))))
print(rows,flush=True)
best=min(rows,key=lambda x:(x['max_overlap_mm3'],x['mean_overlap_mm3']))
vals=[]
for phi in np.linspace(0,2*np.pi,97)[:-1]:
 w=placed(phi);upper=top.copy();upper.apply_transform(trimesh.transformations.rotation_matrix(-phi/24,[0,0,1]));vals.append(volume(lower(best['phase_deg'],-phi/24),w)+volume(upper,w))
report=dict(candidates=rows,best_phase_deg=best['phase_deg'],pose_count=96,max_overlap_mm3=max(vals),mean_overlap_mm3=float(np.mean(vals)),ratio_assumed=24,rotation_sign=-1)
(p/'refined.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
