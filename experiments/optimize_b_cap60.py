"""Reproducible bounded PD search; optimize time to ground, reserve holdout cases."""
import sys,json,time,argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dome import DomeSim
from clover import Config
from b_control import BController
BASE=[.08,.02,.001,.0004]
TRAIN=[dict(tilt=5,seed=0),dict(tilt=15,seed=0),dict(tilt=25,seed=1)]
HOLD=[dict(tilt=t,seed=s,wind=w) for t,s,w in [(10,3,0),(20,4,0),(30,5,0),(15,6,.3),(25,7,-.3),(0,8,0)]]

def run(job):
    gains,case,dt=job
    sim=DomeSim(Config(dt=dt,height=3,spool_speed=.04),line_length=.1697)
    sim.reset(case['tilt'],case['seed']);wind=np.array([case.get('wind',0),0,0]);sim.wind=wind
    ctrl=BController('optimized') if isinstance(gains,str) else BController('aero_pd',*gains)
    peak=0.;sq=0.;n=0
    while sim.data.time<8 and not sim.landed():
        sim.step(ctrl.action(sim),wind)
        tilt=np.degrees(np.arccos(np.clip(sim.data.xmat[sim.hub].reshape(3,3)[2,2],-1,1)))
        peak=max(peak,tilt);sq+=tilt*tilt;n+=1
    return dict(case=case,duration=sim.data.time,max_tilt=peak,rms_tilt=np.sqrt(sq/n),ground=bool(sim.landed()))

def score(rows):
    # Penalize flips and unfinished runs; duration dominates among stable trajectories.
    return float(np.mean([r['duration']-2*(r['max_tilt']>90)-4*(not r['ground']) for r in rows]))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--validate',action='store_true');parser.add_argument('--final',action='store_true');args=parser.parse_args()
    out=Path('outputs/B-cap60-controller-search.json')
    if args.final:
        data=json.loads(out.read_text())
        cases=[dict(tilt=t,seed=s,wind=w) for t,s,w in [(5,11,.15),(12,12,-.15),(18,13,0),(22,14,.2),(28,15,-.2),(35,16,0)]]
        with ProcessPoolExecutor(max_workers=4) as pool:
            data['deployed_check']=[dict(controller=g,runs=list(pool.map(run,[(g,c,.001) for c in cases]))) for g in [BASE,'optimized']]
        out.write_text(json.dumps(data,indent=2)+'\n')
        print(data['deployed_check'],flush=True)
    elif not args.validate:
        rng=np.random.default_rng(606)
        candidates=[BASE]+[list(np.array(BASE)*np.exp(rng.uniform(np.log(.2),np.log(3),4))) for _ in range(23)]
        results=[]
        with ProcessPoolExecutor(max_workers=4) as pool:
            for i,gains in enumerate(candidates):
                rows=list(pool.map(run,[(gains,c,.002) for c in TRAIN]))
                entry=dict(gains=gains,score=score(rows),runs=rows);results.append(entry)
                print(i,round(entry['score'],4),gains,flush=True)
                out.write_text(json.dumps(dict(seed=606,screen_dt=.002,training=TRAIN,candidates=results),indent=2)+'\n')
    else:
        data=json.loads(out.read_text());top=sorted(data['candidates'],key=lambda r:r['score'],reverse=True)[:3]
        gains=[BASE]+[r['gains'] for r in top if r['gains']!=BASE]
        validation=[]
        with ProcessPoolExecutor(max_workers=4) as pool:
            for g in gains:
                rows=list(pool.map(run,[(g,c,.001) for c in TRAIN+HOLD]))
                fine=list(pool.map(run,[(g,c,.0005) for c in TRAIN[:2]]))
                validation.append(dict(gains=g,score=score(rows),runs=rows,fine=fine))
                print('VALIDATED',validation[-1],flush=True)
        data['validation']=validation;out.write_text(json.dumps(data,indent=2)+'\n')
