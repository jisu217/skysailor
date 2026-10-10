"""Compare fixed feedback and short-horizon push/brake at two actuator speeds."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard import Experiment,experiment
results=[]
for length,speed,tilt in [(169.7,40,5),(169.7,40,15),(169.7,150,15),(250,40,15)]:
 for algo in ['aero_pd','predictive']:
  params=Experiment(variant='B',b_controller=algo,line_length_mm=length,drive_speed_mm_s=speed,tilt=tilt,mode='pd')
  result=experiment(params)['runs']['pd']['summary'];results.append(dict(parameters=params.model_dump(),summary=result))
  print(length,speed,tilt,algo,result,flush=True)
Path('outputs/B-length-speed-prediction.json').write_text(json.dumps(results,indent=2)+'\n')
