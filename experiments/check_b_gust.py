"""Same seeded gust realization for fixed lines and tuned PD; no retuning."""
import sys,json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard import Experiment,experiment

def run(seed):
 p=Experiment(variant='B',b_controller='optimized',seconds=8,line_length_mm=169.7,
              wind_mode='constant' if seed<0 else 'gust',wind_x=0 if seed<0 else .2,wind_seed=max(seed,0))
 r=experiment(p)
 return {'parameters':p.model_dump(),'runs':{k:v['summary'] for k,v in r['runs'].items()}}
if __name__=='__main__':
 with ProcessPoolExecutor(max_workers=4) as pool: rows=list(pool.map(run,[-1,0,1,2,3,4]))
 Path('outputs/B-gust-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
 for r in rows: print(r['parameters']['wind_mode'],r['parameters']['wind_seed'],r['runs'],flush=True)
