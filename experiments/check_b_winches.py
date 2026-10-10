"""Three real cable-length actuators; supersedes planar B benchmarks."""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard import Experiment,experiment
results=[]
for length,speed,tilt,algorithm in [(169.7,40,5,'aero_pd'),(169.7,40,15,'aero_pd'),(169.7,150,15,'aero_pd'),(250,150,15,'aero_pd'),(250,150,15,'predictive')]:
 p=Experiment(variant='B',line_length_mm=length,drive_speed_mm_s=speed,tilt=tilt,b_controller=algorithm)
 start=time.time();r=experiment(p)
 entry={'model':'B-winched-cables-v1','parameters':p.model_dump(),'elapsed_wall_s':time.time()-start,'runs':{k:v['summary'] for k,v in r['runs'].items()}}
 results.append(entry);print(entry,flush=True)
Path('outputs/B-physical-winches.json').write_text(json.dumps(results,indent=2)+'\n')
