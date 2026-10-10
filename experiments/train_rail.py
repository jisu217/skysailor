"""SAC training entry point. Run only after validating the provisional aerodynamic model.
Optional dependencies: uv run --with stable-baselines3 python experiments/train_rail.py
"""
import sys,argparse,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
p=argparse.ArgumentParser();p.add_argument('--reward',choices=['altitude','airtime'],default='altitude');p.add_argument('--steps',type=int,default=100000);p.add_argument('--seed',type=int,default=0);p.add_argument('--output',default='outputs/rl-380');p.add_argument('--allow-provisional-aero',action='store_true');args=p.parse_args()
if not args.allow_provisional_aero:p.error('380mm aerodynamic coefficients are provisional; use --allow-provisional-aero for exploratory training only')
if args.steps<=0:p.error('steps must be positive')
from stable_baselines3 import SAC
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import CheckpointCallback,BaseCallback
import torch
torch.set_num_threads(1)
from rail_env import RailAirtimeEnv
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
env=Monitor(RailAirtimeEnv(reward_mode=args.reward),str(out/'episodes'))
model=SAC('MlpPolicy',env,seed=args.seed,verbose=1,learning_starts=1000,buffer_size=100000,batch_size=256,gamma=.9999,device='cpu')
class Progress(BaseCallback):
    def _on_step(self):
        if self.num_timesteps%100==0:
            (out/'status.json').write_text(json.dumps({'status':'training','steps':self.num_timesteps,'target_steps':args.steps,'reward':args.reward,'updated_unix':time.time()}))
        return True
(out/'config.json').write_text(json.dumps(vars(args),indent=2))
try:
    model.learn(total_timesteps=args.steps,callback=[Progress(),CheckpointCallback(save_freq=2000,save_path=str(out/'checkpoints'),name_prefix='sac')])
    (out/'status.json').write_text(json.dumps({'status':'complete','steps':model.num_timesteps,'target_steps':args.steps,'reward':args.reward}))
finally:model.save(str(out/'policy'));env.close()
