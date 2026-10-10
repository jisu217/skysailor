"""Local practice evaluator. Only load agent code you trust."""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from uuid import uuid4
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rail_env import RailAirtimeEnv
from dashboard import geometry, snapshot

VERSION = 'skysailor-380-v1'
def evaluate(agent_path, seeds, output, name):
    spec = importlib.util.spec_from_file_location('participant_agent', agent_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    agent = module.Agent()
    output.mkdir(parents=True, exist_ok=True)
    episodes = []
    for seed in seeds:
        env = RailAirtimeEnv()
        try:
            obs, metadata = env.reset(seed=seed)
            agent.reset(seed)
            gs = geometry(env.sim)
            frames = [snapshot(env.sim)]
            reward = 0.; peak = float(frames[0]['tilt']); start = time.perf_counter()
            for _ in range(501):
                action = np.asarray(agent.act(obs.copy()), dtype=float)
                if action.shape != (2,) or not np.isfinite(action).all() or (np.abs(action)>1).any():
                    raise ValueError('Agent must return two finite values in [-1, 1]')
                obs, r, terminated, truncated, info = env.step(action)
                reward += r; peak = max(peak, info['tilt_deg'])
                frames.append(snapshot(env.sim))
                if terminated or truncated: break
            else: raise RuntimeError('Episode exceeded step limit')
            run_id = uuid4().hex
            summary = dict(duration_s=info['time_s'], max_tilt_deg=peak,
                termination='ground' if terminated else 'timeout',
                mean_descent_m_s=float(np.mean([f['speed'] for f in frames])),
                wall_seconds=time.perf_counter()-start)
            replay = dict(settings=env.params.model_copy(update={'wind_clip':metadata['wind_clip']}).model_dump(), strategy='agent', quality='fine',
                agent_name=name, environment_version=VERSION, geometry=gs, frames=frames, summary=summary)
            (output / (run_id+'.json')).write_text(json.dumps(replay, allow_nan=False))
            episodes.append(dict(seed=seed, reward=reward, duration_s=info['time_s'],
                max_tilt_deg=peak, replay_id=run_id, wind_clip=metadata['wind_clip']))
        finally: env.close()
    report = dict(id=uuid4().hex, name=name, environment_version=VERSION,
        evaluation_kind='public-practice', score=float(np.mean([e['reward'] for e in episodes])),
        mean_duration_s=float(np.mean([e['duration_s'] for e in episodes])),
        flip_rate=float(np.mean([e['max_tilt_deg']>90 for e in episodes])), episodes=episodes)
    (output / ('evaluation-'+report['id']+'.json')).write_text(json.dumps(report,indent=2,allow_nan=False))
    return report

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agent',default='participant/agent.py');p.add_argument('--name',default='Neutral baseline')
    p.add_argument('--seeds',default='0,1,2,3,4');p.add_argument('--output',default='outputs/strategy_runs')
    a=p.parse_args();seeds=[int(s) for s in a.seeds.split(',')]
    if not 1<=len(seeds)<=100: p.error('Provide 1–100 seeds')
    print(json.dumps(evaluate(Path(a.agent),seeds,Path(a.output),a.name),indent=2))
