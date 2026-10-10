"""Versioned benchmarks. Submissions are bounded numeric policies, never Python code."""
import json
import threading
import time
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from fastapi import APIRouter, HTTPException, Request
import shutil
from agent_sandbox import DockerAgent,AgentError,available,extract_archive,MAX_ARCHIVE
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT=Path(__file__).parent/'outputs'/'benchmarks'
REPLAYS=Path(__file__).parent/'outputs'/'strategy_runs'
METRICS=[dict(id='calm-380-v1',title='01 · 무풍 제어',wind_mode='constant'),dict(id='wind-380-v1',title='02 · 실측 바람 제어',wind_mode='measured')]
for m in METRICS:
    m.update(diameter_mm=380,depth_mm=80,dome_mass_g=25,payload_mass_g=18,rail_mass_g=5,support_mass_g=3,rail_drop_mm=5,linear_speed_mm_s=30,angular_speed_deg_s=180,torque_mnm=5,linear_force_n=.5,linear_accel_m_s2=.5,height_m=3,seconds=10,seeds=[0,1,2,3,4],initial_tilt_deg=[3,15],score='mean altitude integral (m*s)',aero='provisional scaled CFD',observation_size=17)
METRICS.append(dict(METRICS[1],id='hanging-wind-380-v1',title='03 · 3점 매달린 추 / 실측 바람',mechanism='H',observation_size=28,action_size=3,ring_radius_mm=80,connector_drop_mm=60,pendulum_length_mm=50,actuator_speed_mm_s=30))
HANGING_ID='hanging-wind-380-v1'
DIRECT_ID='direct-wind-380-v1'
METRICS.append(dict(METRICS[2],id=DIRECT_ID,title='04 · 테두리 3막대 / 실측 바람',mechanism='P',observation_size=22,ring_radius_mm=190,pendulum_length_mm=0))
router=APIRouter(prefix='/api/benchmarks')
executor=ThreadPoolExecutor(max_workers=1)
lock=threading.Lock();active=set()
class Hardware(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    payload_mass_g:float=Field(18,ge=.1,le=100)
    rail_drop_mm:float=Field(5,ge=5,le=300)

    ring_radius_mm:float=Field(80,ge=40,le=150)
    connector_drop_mm:float=Field(60,ge=40,le=150)
    pendulum_length_mm:float=Field(50,ge=15,le=120)
    actuator_speed_mm_s:float=Field(30,ge=5,le=100)

def hardware_for(request):
    keys=['payload_mass_g','ring_radius_mm','connector_drop_mm','pendulum_length_mm','actuator_speed_mm_s'] if request.metric_id==HANGING_ID else ['payload_mass_g','rail_drop_mm']
    if request.metric_id==DIRECT_ID:keys=['payload_mass_g','connector_drop_mm','actuator_speed_mm_s']
    return {k:getattr(request,k) for k in keys}

class Submission(Hardware):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    metric_id:str
    participant:str=Field(min_length=1,max_length=60)
    name:str=Field(min_length=1,max_length=80)
    weights:list[list[float]]
    bias:list[float]
    @model_validator(mode='after')
    def validate_policy(self):
        if self.metric_id not in [m['id'] for m in METRICS]:raise ValueError('Unknown metric')
        n,o=(3,22) if self.metric_id==DIRECT_ID else (3,28) if self.metric_id==HANGING_ID else (2,17)
        if len(self.weights)!=n or any(len(row)!=o for row in self.weights) or len(self.bias)!=n:raise ValueError(f'weights must be {n}x{o}; bias must be {n}')
        if not np.isfinite(self.weights).all() or not np.isfinite(self.bias).all() or np.max(np.abs(self.weights))>100 or np.max(np.abs(self.bias))>100:raise ValueError('Finite coefficients in [-100,100] required')
        if not self.participant.strip() or not self.name.strip():raise ValueError('Names cannot be blank')
        return self

def save(row):
    ROOT.mkdir(parents=True,exist_ok=True)
    p=ROOT/(row['id']+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(row,allow_nan=False));tmp.replace(p)

def evaluate(row,request,agent_path=None):
    from rail_env import RailAirtimeEnv
    from hanging import HangingEnv,DirectEnv
    from dashboard import snapshot,geometry
    try:
        row['hardware']=hardware_for(request);row['status']='running';save(row)
        metric=next(m for m in METRICS if m['id']==request.metric_id)
        REPLAYS.mkdir(parents=True,exist_ok=True)
        for seed in metric['seeds']:
            env=DirectEnv(hardware_for(request),metric['wind_mode']) if request.metric_id==DIRECT_ID else HangingEnv(hardware_for(request),metric['wind_mode']) if request.metric_id==HANGING_ID else RailAirtimeEnv(wind_mode=metric['wind_mode'],payload_mass_g=request.payload_mass_g,rail_drop_mm=request.rail_drop_mm);agent=None
            try:
                obs,meta=env.reset(seed=seed)
                if agent_path is not None:agent=DockerAgent(agent_path,action_size=3 if request.metric_id in (HANGING_ID,DIRECT_ID) else 2)
                frames=[snapshot(env.sim)];gs=geometry(env.sim);score=0.;peak=frames[0]['tilt'];start=time.perf_counter()
                for _ in range(501):
                    action=agent.act(obs) if agent is not None else np.tanh(np.asarray(request.weights)@obs+request.bias)
                    obs,r,done,timeout,info=env.step(action);score+=r;peak=max(peak,info['tilt_deg']);frames.append(snapshot(env.sim))
                    if done or timeout:break
                else:raise RuntimeError('Physics time limit exceeded')
                rid=uuid4().hex
                summary=dict(duration_s=info['time_s'],max_tilt_deg=peak,termination='ground' if done else 'timeout',mean_descent_m_s=float(np.trapezoid([f['speed'] for f in frames],[f['t'] for f in frames])/info['time_s']),wall_seconds=time.perf_counter()-start)
                replay=dict(hardware=hardware_for(request),settings=env.params.model_copy(update={'wind_clip':meta['wind_clip']}).model_dump(),geometry=gs,frames=frames,summary=summary,strategy='agent',quality='fine',agent_name=request.name,metric_id=request.metric_id)
                p=REPLAYS/(rid+'.json');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(replay,allow_nan=False));tmp.replace(p)
                row['episodes'].append(dict(seed=seed,replay_id=rid,score=score,**summary));save(row)
            finally:
                if agent is not None:agent.close()
                env.close()
        row.update(status='complete',score=float(np.mean([e['score'] for e in row['episodes']])),mean_duration_s=float(np.mean([e['duration_s'] for e in row['episodes']])),flip_rate=float(np.mean([e['max_tilt_deg']>90 for e in row['episodes']])))
        save(row)
    except Exception as exc:
        row.update(status='failed',error=str(exc)[:400] if isinstance(exc,AgentError) else '평가 중 오류가 발생했습니다. 운영자에게 문의하세요.');save(row)
    finally:
        with lock:active.discard(row['id'])

@router.get('')
def metrics():return METRICS

@router.get('/submissions')
def submissions():
    rows=[]
    for p in ROOT.glob('*.json'):
        try:
            r=json.loads(p.read_text())
            with lock:
                if r['status'] in ('queued','running') and r['id'] not in active:r.update(status='failed',error='서버 재시작으로 평가가 중단되었습니다.')
            rows.append(r)
        except (OSError,ValueError):continue
    return sorted(rows,key=lambda r:r['created'],reverse=True)

@router.post('/submissions',status_code=202)
def submit(request:Submission):
    with lock:
        if len(active)>=2:raise HTTPException(429,'평가 대기열이 찼습니다. 잠시 뒤 제출하세요.')
        row=dict(id=uuid4().hex,metric_id=request.metric_id,participant=request.participant,name=request.name,created=time.time(),status='queued',episodes=[],policy=request.model_dump(),hardware=hardware_for(request))
        active.add(row['id'])
        try:save(row);executor.submit(evaluate,row,request)
        except Exception:active.discard(row['id']);raise
    return dict(id=row['id'])

class CodeSubmission(Hardware):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    metric_id:str
    participant:str=Field(min_length=1,max_length=60)
    name:str=Field(min_length=1,max_length=80)

@router.get('/runtime')
def runtime():
    return dict(available=available(),format='agent.zip',python='3.12',packages={'numpy':'2.5.3','torch':'2.8.0'},init_seconds=20,action_seconds=.25,episode_seconds=60,memory_mb=1024)

@router.post('/code-submissions',status_code=202)
async def submit_code(request:Request,metric_id:str,participant:str,name:str,payload_mass_g:float=18,rail_drop_mm:float=5,ring_radius_mm:float=80,connector_drop_mm:float=60,pendulum_length_mm:float=50,actuator_speed_mm_s:float=30):
    try:meta=CodeSubmission(metric_id=metric_id,participant=participant,name=name,payload_mass_g=payload_mass_g,rail_drop_mm=rail_drop_mm,ring_radius_mm=ring_radius_mm,connector_drop_mm=connector_drop_mm,pendulum_length_mm=pendulum_length_mm,actuator_speed_mm_s=actuator_speed_mm_s)
    except ValueError:raise HTTPException(422,'이름과 기체 설정 범위를 확인하세요. 지표별 입력 범위는 제출 안내를 참고하세요.')
    if meta.metric_id not in [m['id'] for m in METRICS] or not participant.strip() or not name.strip():raise HTTPException(422,'잘못된 지표 또는 이름입니다.')
    if not available():raise HTTPException(503,'격리 평가 실행 환경이 준비되지 않았습니다. 운영자에게 문의하세요.')
    run_id=uuid4().hex
    with lock:
        if len(active)>=2:raise HTTPException(429,'평가 대기열이 찼습니다. 잠시 뒤 제출하세요.')
        active.add(run_id)
    folder=ROOT/'agents'/run_id
    try:
        data=bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data)>MAX_ARCHIVE:raise HTTPException(413,'ZIP은 20MB 이하여야 합니다.')
        extract_archive(bytes(data),folder)
        row=dict(id=run_id,metric_id=metric_id,participant=participant,name=name,created=time.time(),status='queued',episodes=[],agent_type='python',runtime='skysailor-agent:v1',hardware=hardware_for(meta))
        save(row);executor.submit(evaluate,row,meta,folder)
    except Exception as exc:
        with lock:active.discard(run_id)
        if folder.exists():shutil.rmtree(folder)
        if isinstance(exc,AgentError):raise HTTPException(422,str(exc))
        raise
    return dict(id=run_id)

@router.get('/example')
def example(metric_id:str="calm-380-v1"):
    from fastapi.responses import Response
    import io,zipfile
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name in ('agent.py','requirements.txt'):
            z.write(Path(__file__).parent/'participant'/('direct-example' if metric_id==DIRECT_ID else 'hanging-example' if metric_id==HANGING_ID else 'python-example')/name,name)
    return Response(stream.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="agent-example.zip"'})
