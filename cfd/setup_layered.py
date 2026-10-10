"""Configure the new layered mesh with consistent low-Re wall treatment.
Positive tilt rotates the dome's +z axis towards world +x about +y.
Instead of rotating the mesh, rotate the incoming velocity into body coordinates.
"""
import argparse,json,math,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--tilt',type=float,default=0);p.add_argument('--iterations',type=int,default=1200);a=p.parse_args();case=Path(a.case)
if (case/'postProcessing').exists():raise RuntimeError('Existing results: use a fresh case directory')
mesh=json.loads((case/'mesh-metadata.json').read_text())
for src in (Path(__file__).parent/'templates').rglob('*'):
 if src.is_file():
  dst=case/src.relative_to(Path(__file__).parent/'templates');dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
s=math.sin(math.radians(a.tilt));c=math.cos(math.radians(a.tilt));U=f'({-1.6*s:.12g} 0 {1.6*c:.12g})'
p=case/'0/U';text=p.read_text();text=re.sub(r'\(0 0 1\.6\)',U,text);text=text.replace('sides {type slip;}',f'sides {{type inletOutlet; inletValue uniform {U}; value uniform {U};}}');p.write_text(text)
# Continuous velocity-based nut wall treatment plus low-Re k wall treatment.
p=case/'0/nut';p.write_text(p.read_text().replace('nutkWallFunction','nutUSpaldingWallFunction'))
p=case/'0/k';p.write_text(p.read_text().replace('kqRWallFunction','kLowReWallFunction'))
p=case/'system/controlDict';text=p.read_text();text=re.sub(r'endTime\s+\d+;',f'endTime {a.iterations};',text);text=re.sub(r'dragDir\s*\([^)]*\)',f'dragDir ({-s:.12g} 0 {c:.12g})',text);text=re.sub(r'liftDir\s*\([^)]*\)',f'liftDir ({c:.12g} 0 {s:.12g})',text);p.write_text(text)
metadata=dict(speed_m_s=1.6,tilt_deg=a.tilt,diameter_m=.24,rise_m=.04,shell_thickness_m=.001,air_density=1.225,nu=1.5e-5,reynolds=25600,solver='simpleFoam / steady incompressible RANS kOmegaSST',inlet_turbulence_intensity=.01,inlet_length_scale_m=.024,wall_treatment='nutUSpaldingWallFunction + kLowReWallFunction + omegaWallFunction',moment_origin_m=[0,0,0],reference_com_m=[0,0,(.0042*.02-.004*.12)/.0082],positive_pitch='Dome +z leans towards world +x; negative My is restoring at positive tilt',limitations=['Fixed dome only; no payload or cables in flow','Assumed 1 mm shell thickness','Steady RANS cannot resolve unsteady wake','Full 3D mesh; angular and domain resolution require sensitivity checks','Do not calibrate MuJoCo until force, moment and grid convergence are assessed'],**mesh)
(case/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');(case/'case.foam').touch()
print('CASE READY',case,'tilt',a.tilt)
