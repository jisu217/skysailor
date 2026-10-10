"""O4 manual input tapes: deterministic preview and server-side scoring."""
import json,time
from uuid import uuid4
import numpy as np
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field,ConfigDict
import benchmark as b
router=APIRouter(prefix='/api/manual')
class Flight(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    seed:int=Field(ge=0,le=4)
    actions:list[tuple[float,float,float]]=Field(default_factory=list,max_length=501)
    rewound:bool=False
class Run(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    payload_mass_g:float=Field(18,ge=.1)
    connector_drop_mm:float=Field(60,ge=40)
    actuator_speed_mm_s:float=Field(30,ge=5)
    flight:Flight
class Submit(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    participant:str=Field(min_length=1,max_length=60)
    name:str=Field(min_length=1,max_length=50)
    payload_mass_g:float=Field(18,ge=.1)
    connector_drop_mm:float=Field(60,ge=40)
    actuator_speed_mm_s:float=Field(30,ge=5)
    flights:list[Flight]=Field(min_length=5,max_length=5)
def hardware(r):return {k:getattr(r,k) for k in ('payload_mass_g','connector_drop_mm','actuator_speed_mm_s')}
def simulate(hw,f,frames=False):
    from hanging import DirectEnv
    from dashboard import snapshot,geometry
    if any(not np.isfinite(a).all() or np.max(np.abs(a))>1 for a in f.actions):raise ValueError('입력은 -1~1이어야 합니다.')
    started=time.perf_counter();env=DirectEnv(hw)
    try:
        obs,meta=env.reset(seed=f.seed);gs=geometry(env.sim);history=[snapshot(env.sim)];score=0.;done=False;used=0
        for a in f.actions:
            if done:
                if frames:raise ValueError('비행 종료 뒤 입력이 포함되어 있습니다.')
                break
            obs,r,d,tr,info=env.step(a);score+=r;done=d or tr;used+=1;history.append(snapshot(env.sim))
        ts=[x['t'] for x in history];tilts=[x['tilt'] for x in history];duration=ts[-1]
        summary=dict(duration_s=duration,max_tilt_deg=max(tilts),mean_tilt_deg=float(np.trapezoid(tilts,ts)/duration) if duration else tilts[0],termination='ground' if done and duration<10 else 'timeout' if done else 'pending')
        summary.update(mean_descent_m_s=float(np.trapezoid([x['speed'] for x in history],ts)/duration) if duration else 0.,wall_seconds=time.perf_counter()-started)
        result=dict(frame=history[-1],geometry=gs,ended=done,score=score,steps=used,summary=summary,observation=obs.tolist())
        if frames:result['replay']=dict(hardware=hw,settings=env.params.model_copy(update={'wind_clip':meta['wind_clip']}).model_dump(),geometry=gs,frames=history,summary=summary,strategy='manual',quality='fine',metric_id=b.DIRECT_ID)
        return result
    finally:env.close()
@router.post('/preview')
def preview(r:Run):
    try:return simulate(hardware(r),r.flight)
    except ValueError as e:raise HTTPException(422,str(e))
def evaluate(row,r):
    try:
        row['status']='running';b.save(row);b.REPLAYS.mkdir(parents=True,exist_ok=True)
        for f in sorted(r.flights,key=lambda f:f.seed):
            result=simulate(hardware(r),f,True)
            if not result['ended']:raise ValueError('5개 비행을 모두 끝내야 제출할 수 있습니다.')
            rid=uuid4().hex;replay=result['replay'];replay.update(agent_name=row['name'],manual_rewound=f.rewound)
            p=b.REPLAYS/(rid+'.json');p.write_text(json.dumps(replay,allow_nan=False))
            row['episodes'].append(dict(seed=f.seed,replay_id=rid,score=result['score'],**result['summary']));b.save(row)
        row.update(status='complete',score=float(np.mean([e['score'] for e in row['episodes']])),mean_duration_s=float(np.mean([e['duration_s'] for e in row['episodes']])),flip_rate=float(np.mean([e['max_tilt_deg']>90 for e in row['episodes']])))
        b.save(row)
    except Exception as e:row.update(status='failed',error=str(e)[:200]);b.save(row)
    finally:
        with b.lock:b.active.discard(row['id'])
@router.post('/submit',status_code=202)
def submit(r:Submit):
    if sorted(f.seed for f in r.flights)!=list(range(5)):raise HTTPException(422,'seed 0–4를 각각 한 번씩 포함해야 합니다.')
    if not r.participant.strip() or not r.name.strip():raise HTTPException(422,'이름을 입력하세요.')
    for f in r.flights:
        if not f.actions or any(not np.isfinite(a).all() or np.max(np.abs(a))>1 for a in f.actions):raise HTTPException(422,'비행 입력을 확인하세요.')
    rewind=any(f.rewound for f in r.flights)
    row=dict(id=uuid4().hex,metric_id=b.DIRECT_ID,participant=r.participant,name='MANUAL'+(' · 되돌리기 사용' if rewind else '')+' · '+r.name,created=time.time(),status='queued',episodes=[],agent_type='manual',manual_rewound=rewind,manual_assistance='paused/stepped input allowed',hardware=hardware(r),manual_tapes=r.model_dump())
    with b.lock:
        if len(b.active)>=2:raise HTTPException(429,'평가 대기열이 찼습니다.')
        b.active.add(row['id'])
        try:b.save(row);b.executor.submit(evaluate,row,r)
        except Exception:b.active.discard(row['id']);raise
    return dict(id=row['id'])
