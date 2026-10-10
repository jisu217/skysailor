"""Measured unscaled 3D wind replay: distinguish ground and air-relative descent."""
import sys,json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard import Experiment,experiment

def run(clip):
 p=Experiment(variant='B',b_controller='optimized',wind_mode='measured',wind_clip=clip,seconds=8,line_length_mm=169.7)
 r=experiment(p)
 return dict(parameters=p.model_dump(),source=r['wind_source'],runs={k:v['summary'] for k,v in r['runs'].items()})
if __name__=='__main__':
 with ProcessPoolExecutor(max_workers=3) as p:rows=list(p.map(run,['gentle','up','down']))
 Path('outputs/B-measured-wind-validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 for r in rows:print(r['parameters']['wind_clip'],r['runs'],flush=True)
