"""Headless MuJoCo trajectories served to a browser-native 3D viewer."""
from pathlib import Path
from functools import lru_cache
import json
from datetime import datetime, timezone
from uuid import uuid4
import re
from collections import deque
from threading import BoundedSemaphore
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import mujoco
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from clover import CloverSim, Config
from leaf import SEGMENTS
from dome import DomeSim
from rail import RailSim
from hanging import HangingSim, DirectSim
from b_control import BController, project_triangle


class Experiment(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    height: float = Field(3, ge=0.5, le=10)
    tilt: float = Field(15, ge=0, le=80)
    wind_x: float = Field(0, ge=-3, le=3)
    wind_y: float = Field(0, ge=-3, le=3)
    wind_mode: Literal['constant','gust','measured'] = 'constant'
    wind_clip: Literal['gentle','up','down'] = 'gentle'
    gust_speed: float = Field(.4, ge=0, le=3)
    gust_period: float = Field(.8, ge=.2, le=5)
    wind_seed: int = Field(0, ge=0, le=9999)
    kp: float = Field(0.018, ge=0, le=0.08)
    kd: float = Field(0.004, ge=0, le=0.02)
    seed: int = Field(0, ge=0, le=9999)
    seconds: float = Field(5, ge=0.1, le=10)
    mode: Literal['compare', 'pd', 'off'] = 'compare'
    variant: Literal['A','B'] = 'A'
    b_controller: Literal['manual','p','pd','aero_pd','optimized','position','predictive'] = 'manual'
    line_length_mm: float = Field(float(np.hypot(.12,.12)*1000), ge=120, le=400)
    mechanism: Literal['A','B3','B4','C','H','P'] = 'A'
    dome_diameter_mm: Literal[240,380] = 240
    dome_mass_g: float = Field(4.2,ge=1,le=200)
    rail_mass_g: float = Field(5,ge=.1,le=100)
    support_mass_g: float = Field(3,ge=.1,le=100)
    rail_drop_mm: float = Field(40,ge=5,le=300)
    rail_linear_mm_s: float = Field(80,ge=1,le=500)
    rail_torque_mnm: float = Field(2,ge=.01,le=100)
    rail_angular_deg_s: float = Field(180,ge=1,le=720)
    connector_drop_mm: float = Field(60,ge=40)
    actuator_speed_mm_s: float = Field(30,ge=5)
    payload_mass_g: float = Field(4,ge=.1)
    drive_speed_mm_s: float = Field(40, ge=5, le=300)
    target_x_mm: float = Field(0, ge=-120, le=120)
    target_y_mm: float = Field(0, ge=-120, le=120)
    air_density: float = Field(1.225, ge=0, le=2)


app = FastAPI(title='Clover Flight Lab')
slots = BoundedSemaphore(2)


def geometry(sim):
    result = []
    for i in range(1, sim.model.ngeom):
        g = {'type':int(sim.model.geom_type[i]), 'size':sim.model.geom_size[i].tolist(), 'color':sim.model.geom_rgba[i].tolist()}
        if (1 < i < 26) if isinstance(sim,DomeSim) else (1 < i < sim.model.ngeom-1):
            j = i-2 if isinstance(sim,DomeSim) else (i-2) % SEGMENTS
            if isinstance(sim,DomeSim):g['triangles'] = sim.panels[j]['vertices'].tolist()
            else:g['polygon'] = sim.panels[j]['polygon'].tolist()
            g['area'] = sim.panels[j]['area']
        result.append(g)
    return result


def snapshot(sim):
    data = sim.data
    rot_vel = np.zeros(6)
    mujoco.mj_objectVelocity(sim.model, data, mujoco.mjtObj.mjOBJ_BODY, sim.hub, rot_vel, 0)
    aero = sim.aerodynamics()
    body_ids = sim.model.geom_bodyid[1:]
    quats = []
    positions=[]
    for i,body_id in enumerate(body_ids,start=1):
        primitive=isinstance(sim,(RailSim,HangingSim)) and i>=26
        matrix=data.geom_xmat[i] if primitive else data.xmat[body_id]
        positions.append((data.geom_xpos[i] if primitive else data.xpos[body_id]).tolist())
        quat = np.empty(4)
        mujoco.mju_mat2Quat(quat, matrix)
        quats.append(quat.tolist())
    return {
        'dome_diameter_mm':getattr(sim,'radius',.12)*2000,
        'dome_depth_mm':getattr(sim,'depth',.06)*1000,
        'control_radius':getattr(sim,'radius',.12),
        'dome_mass_g':getattr(sim,'dome_mass',.0042)*1000,
        'rail': sim.rail_state() if isinstance(sim,RailSim) else None,
        'mechanism': 'P' if getattr(sim,'direct',False) else 'H' if isinstance(sim,HangingSim) else 'C' if isinstance(sim,RailSim) else ('B4' if sim.cable_count==4 else 'B3') if isinstance(sim,DomeSim) and sim.planar else 'A',
        't': round(float(data.time), 6),
        'wind': sim.wind.tolist(),
        'air_descent_speed':float(sim.wind[2]-rot_vel[5]),
        'world_target': [0.,0.] if isinstance(sim,DomeSim) else None,
        'horizontal_error': float(np.linalg.norm(sim.system_com()[:2])) if isinstance(sim,DomeSim) else None,
        'height': float(data.xpos[sim.hub, 2]),
        'tilt': float(sim.record()[2]),
        'speed': float(-rot_vel[5]),
        'spool': (sim.spool*1000).tolist(),
        'tension': sim.tensions.tolist(),
        'line_rest': sim.spool.tolist() if isinstance(sim,DomeSim) else None,
        'line_target': sim.target_lengths.tolist() if isinstance(sim,DomeSim) else None,
        'line_actual': sim.cable_state()['lengths'].tolist() if isinstance(sim,DomeSim) else None,
        'line_slack': sim.cable_state()['slack'].tolist() if isinstance(sim,DomeSim) else None,
        'winch_speed': sim.winch_rates.tolist() if isinstance(sim,DomeSim) else None,
        'winch_stalled': sim.winch_stalled.tolist() if isinstance(sim,DomeSim) else None,
        'position': positions,
        'quaternion': quats,
        'tips': data.site_xpos[sim.tips].tolist(),
        'anchor': data.site_xpos[sim.anchor].tolist(),
        'center': data.xpos[sim.hub].tolist(),
        'aero_position': (aero['position'] if isinstance(sim,DomeSim) else data.site_xpos[sim.air_sites]).tolist(),
        'aero_torque': aero['torque_com'].tolist() if isinstance(sim,DomeSim) else None,
        'aero_model': ('380x80-scaled-coefficients-provisional' if getattr(sim,'radius',.12)>.12 else 'cap60-cfd-v1') if isinstance(sim,DomeSim) else 'panel-drag',
        'aero_force': aero['force'].tolist(),
        'airflow': (aero['airflow'] if sim.c.air_density > 0 else np.zeros_like(aero['airflow'])).tolist(),
        'air_present': sim.c.air_density > 0,
        'loading': aero['loading'].tolist(),
        'aero_total': aero['force'].sum(axis=0).tolist(),
        'gravity': (sim.model.body_mass.sum()*sim.model.opt.gravity).tolist(),
        'com': (sim.system_com() if isinstance(sim,DomeSim) else data.subtree_com[sim.hub]).tolist(),
        'target_com': sim.target_com_world().tolist() if isinstance(sim,DomeSim) else None,
        'hang': sim.hang if isinstance(sim,DomeSim) else None,
        'target_xy': sim.active_target_xy.tolist() if isinstance(sim,DomeSim) else None,
        'payload_local': (data.xmat[sim.hub].reshape(3,3).T@(data.xpos[sim.payload]-data.xpos[sim.hub])).tolist() if isinstance(sim,DomeSim) else None,
        'system_com': (np.sum(sim.model.body_mass[:,None]*data.xipos,axis=0)/sim.model.body_mass.sum()).tolist(),
    }


def make_sim(params):
    config=Config(height=params.height,kp=params.kp,kd=params.kd,air_density=params.air_density)
    if params.variant == 'B':
        config.spool_speed=params.drive_speed_mm_s/1000
        if params.mechanism=='P':
            return DirectSim(payload_mass_g=params.payload_mass_g,connector_drop_mm=params.connector_drop_mm,actuator_speed_mm_s=params.actuator_speed_mm_s,config=config)
        if params.mechanism=='C':
            return RailSim(config,payload_mass=params.payload_mass_g/1000,rail_mass=params.rail_mass_g/1000,
                support_mass=params.support_mass_g/1000,drop=params.rail_drop_mm/1000,
                linear_speed=params.rail_linear_mm_s/1000,torque_limit=params.rail_torque_mnm/1000,
                angular_speed=np.deg2rad(params.rail_angular_deg_s),radius=params.dome_diameter_mm/2000,depth=.08 if params.dome_diameter_mm==380 else .06,dome_mass=params.dome_mass_g/1000)
        return DomeSim(config,target_xy=np.array([params.target_x_mm,params.target_y_mm])/1000,line_length=params.line_length_mm/1000,payload_mass=params.payload_mass_g/1000,planar=params.mechanism!='A',cable_count=4 if params.mechanism=='B4' else 3)
    return CloverSim(config)


@lru_cache(maxsize=1)
def measured_wind():
    return json.loads((Path(__file__).parent/'data/wind/measured.json').read_text())


class WindProfile:
    """Spatially uniform horizontal test gusts; seeded, smooth, independent of dt."""
    def __init__(self, params):
        self.record=None
        self.metadata=None
        if params.wind_mode=='measured':
            data=measured_wind();self.record=data['clips'][params.wind_clip]
            self.times=np.array(self.record['time_s']);self.values=np.array(self.record['velocity_m_s'])
            if params.seconds>self.times[-1]+1e-9:raise ValueError('실측 구간보다 긴 실험은 재생할 수 없습니다.')
            self.metadata={k:v for k,v in data.items() if k!='clips'}
            self.metadata['clip']={k:v for k,v in self.record.items() if k not in ('time_s','velocity_m_s')}
            return
        self.base=np.array([params.wind_x,params.wind_y,0.])
        self.period=params.gust_period
        self.amplitude=params.gust_speed if params.wind_mode=='gust' else 0.
        rng=np.random.default_rng(params.wind_seed)
        n=int(np.ceil(params.seconds/self.period))+3
        draws=rng.random((n,2))
        angles=(draws[:,0]*2-1)*np.pi
        radii=np.sqrt(draws[:,1])
        self.knots=np.column_stack([radii*np.cos(angles),radii*np.sin(angles),np.zeros(n)])

    def at(self,time):
        if self.record is not None:
            if time < -1e-8 or time > self.times[-1]+1e-8:raise ValueError('실측 구간 끝: 반복 재생하지 않습니다.')
            return np.array([np.interp(time,self.times,self.values[:,i]) for i in range(3)])
        u=max(0.,float(time))/self.period
        i=min(int(u),len(self.knots)-2);f=np.clip(u-i,0,1)
        f=f*f*(3-2*f)
        return self.base+self.amplitude*((1-f)*self.knots[i]+f*self.knots[i+1])


def experiment(params):
    wind=WindProfile(params)
    result = {'parameters':params.model_dump(), 'runs':{}, 'geometry':None,
              'wind_source':wind.metadata,
              'model': 'B-cap60-cfd-winches-v1' if params.variant=='B' else 'A-panel-drag',
              'limitations': '예비 CFD 표 + 60° 시험의 회전 감쇠 근사. 줄·제어기 공기력과 센서 오차 제외.' if params.variant=='B' else '패널 항력 근사'}
    for mode in (['off','pd'] if params.mode == 'compare' else [params.mode]):
        sim = make_sim(params)
        sim.reset(params.tilt, params.seed)
        if sim.landed():raise ValueError("줄 길이에 비해 시작 높이가 낮습니다. 낙하 높이를 높여주세요.")
        sim.wind = wind.at(0)
        if result['geometry'] is None:
            result['geometry'] = geometry(sim)
        controller=BController(params.b_controller if mode=='pd' else 'center') if isinstance(sim,DomeSim) else None
        if controller:
            controller.action(sim)
            if mode=='pd':
                result['controller']={'algorithm':controller.algorithm, 'tuned_active':controller.tuned_active,
                                      'gains':[controller.kp,controller.kd,controller.torque_kp,controller.torque_kd]}
        frames = [snapshot(sim)]
        tilts = [float(sim.record()[2])]
        count = 0
        vertical_wind_integral=0.
        initial_com_height=float(snapshot(sim)['system_com'][2])
        while sim.data.time < params.seconds-1e-9 and not sim.landed():
            sim.wind=wind.at(sim.data.time)
            action=controller.action(sim) if controller else (sim.pd_action() if mode=='pd' else np.zeros_like(sim.spool))
            w_before=sim.wind[2]
            sim.step(action, sim.wind)
            sim.wind=wind.at(sim.data.time)
            vertical_wind_integral+=.5*(w_before+sim.wind[2])*sim.c.dt
            tilts.append(float(sim.record()[2]))
            count += 1
            if count%10 == 0:
                frames.append(snapshot(sim))
        if abs(frames[-1]['t']-sim.data.time) > 1e-8:
            frames.append(snapshot(sim))
        result['runs'][mode] = {
            'frames':frames,
            'summary':{'duration':float(sim.data.time), 'mean_descent_speed':float((initial_com_height-snapshot(sim)['system_com'][2])/sim.data.time), 'mean_air_descent_speed':float((initial_com_height-snapshot(sim)['system_com'][2]+vertical_wind_integral)/sim.data.time), 'rms_tilt':float(np.sqrt(np.mean(np.square(tilts)))), 'max_tilt':max(tilts), 'inverted':bool(max(tilts)>90), 'horizontal_error':float(np.linalg.norm(sim.system_com()[:2])) if isinstance(sim,DomeSim) else None, 'termination':'ground' if sim.landed() else 'timeout'},
        }
    return result


@app.get('/api/health')
def health():
    return {'status':'ok','engine':'MuJoCo','version':mujoco.__version__}


@app.post('/api/simulate')
def simulate(params: Experiment):
    if not slots.acquire(blocking=False):
        raise HTTPException(503, '다른 실험을 계산 중입니다. 잠시 후 다시 실행해주세요.')
    try:
        return experiment(params)
    except ValueError as error:
        raise HTTPException(422,str(error)) from error
    finally:
        slots.release()


@app.get('/api/initial')
def initial(variant: Literal['A','B']='A'):
    sim = make_sim(Experiment(variant=variant))
    return {'frame':snapshot(sim), 'geometry':geometry(sim)}


class GameCommand(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    kind: Literal['reset','step','rewind']
    input_mode: Literal['position','velocity'] = 'position'
    velocity_mm_s: float = Field(80,ge=1,le=500)
    interval_s: float | None = Field(None,ge=.001,le=2)
    z: float = Field(0,ge=-1,le=1)
    x: float = Field(0,ge=-1,le=1)
    y: float = Field(0,ge=-1,le=1)
    preset: Literal['calm','gust','measured'] = 'calm'
    move_seconds: float = Field(.5,ge=0,le=3)
    drive_speed_mm_s: float = Field(40,ge=5,le=300)
    line_length_mm: float = Field(float(np.hypot(.12,.12)*1000),ge=120,le=400)
    mechanism: Literal['A','B3','B4','C','P'] = 'A'
    dome_diameter_mm: Literal[240,380] = 240
    dome_mass_g: float = Field(4.2,ge=1,le=200)
    rail_mass_g: float = Field(5,ge=.1,le=100)
    support_mass_g: float = Field(3,ge=.1,le=100)
    rail_drop_mm: float = Field(40,ge=5,le=300)
    rail_linear_mm_s: float = Field(80,ge=1,le=500)
    rail_torque_mnm: float = Field(2,ge=.01,le=100)
    rail_angular_deg_s: float = Field(180,ge=1,le=720)
    connector_drop_mm: float = Field(60,ge=40)
    actuator_speed_mm_s: float = Field(30,ge=5)
    payload_mass_g: float = Field(4,ge=.1)


FLIGHT_LOG_DIR = Path(__file__).parent/'outputs'/'flight_logs'


@app.get('/api/game/logs')
def flight_logs():
    files=sorted(FLIGHT_LOG_DIR.glob('*.jsonl'),reverse=True)[:100]
    return [{'id':p.stem,'bytes':p.stat().st_size} for p in files]


@app.get('/api/game/logs/{log_id}')
def flight_log(log_id: str):
    if not re.fullmatch(r'[0-9]{8}T[0-9]{12}Z-[a-f0-9]{12}',log_id):
        raise HTTPException(404,'Log not found')
    path=FLIGHT_LOG_DIR/(log_id+'.jsonl')
    if not path.is_file():raise HTTPException(404,'Log not found')
    return FileResponse(path,media_type='application/x-ndjson',filename=path.name)


@app.websocket('/api/game')
async def game_socket(socket: WebSocket):
    await socket.accept()
    sim=None
    log=None
    history=deque()
    state_spec=mujoco.mjtState.mjSTATE_INTEGRATION
    attrs=('wind','active_target_xy','spool','target_lengths','winch_rates','winch_stalled','tensions')
    def remember():
        state=np.empty(mujoco.mj_stateSize(sim.model,state_spec))
        mujoco.mj_getState(sim.model,sim.data,state,state_spec)
        history.append((float(sim.data.time),state,{k:getattr(sim,k).copy() for k in (*attrs,'rail_drive') if hasattr(sim,k)},
                        goal.copy(),start.copy(),target.copy(),started,duration,peak))
        while history and history[0][0]<sim.data.time-2-1e-9:history.popleft()
    async def emit(data, command, params=None):
        nonlocal log
        if command.kind=='reset':
            stamp=datetime.now(timezone.utc)
            log_id=stamp.strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid4().hex[:12]
            FLIGHT_LOG_DIR.mkdir(parents=True,exist_ok=True)
            log=FLIGHT_LOG_DIR/(log_id+'.jsonl')
            metadata={'type':'metadata','version':1,'created_at':stamp.isoformat(),
                'settings':params.model_dump(),'units':'SI (m, kg, s, N); spool is mm; angles are degrees',
                'sample_interval_s':.02,'physics_step_s':sim.c.dt}
            with log.open('x') as f:f.write(json.dumps(metadata)+'\n')
        data['rewind_available']=max(0.,float(sim.data.time)-history[0][0]) if history else 0.
        data['log_id']=log.stem
        with log.open('a') as f:
            f.write(json.dumps({'type':'frame','input':command.model_dump(),'data':data})+'\n')
        await socket.send_json(data)
    try:
        while True:
            payload=await socket.receive_json()
            try:command=GameCommand(**payload)
            except ValueError:
                await socket.send_json({'error':'올바른 조종 입력이 아닙니다.'});continue
            if command.kind=='reset':
                params=Experiment(variant='B',seconds=10,height=3,tilt=5,
                    line_length_mm=command.line_length_mm,payload_mass_g=command.payload_mass_g,
                    mechanism=command.mechanism,drive_speed_mm_s=command.drive_speed_mm_s,
                    connector_drop_mm=command.connector_drop_mm,actuator_speed_mm_s=command.actuator_speed_mm_s,
                    dome_diameter_mm=command.dome_diameter_mm,dome_mass_g=command.dome_mass_g,rail_mass_g=command.rail_mass_g,support_mass_g=command.support_mass_g,
                    rail_drop_mm=command.rail_drop_mm,rail_linear_mm_s=command.rail_linear_mm_s,
                    rail_torque_mnm=command.rail_torque_mnm,rail_angular_deg_s=command.rail_angular_deg_s,
                    wind_mode={'calm':'constant','gust':'gust','measured':'measured'}[command.preset],
                    wind_x=.2 if command.preset=='gust' else 0)
                if command.mechanism=='P':params=params.model_copy(update={'dome_diameter_mm':380,'dome_mass_g':25})
                sim=make_sim(params);sim.reset(5,0);wind=WindProfile(params)
                sim.wind=wind.at(0);peak=5.;ended=False
                goal=np.zeros(2);start=goal.copy();target=goal.copy();started=0.;duration=.5
                history.clear();remember()
                await emit({'frame':snapshot(sim),'geometry':geometry(sim),'ended':False,
                    'source':wind.metadata,'max_tilt':peak},command,params);continue
            if sim is None:
                await socket.send_json({'error':'먼저 새 낙하를 시작하세요.'});continue
            if command.kind=='rewind':
                cutoff=max(history[0][0],sim.data.time-(command.interval_s if command.interval_s is not None else .1))
                while len(history)>1 and history[-1][0]>cutoff+1e-9:history.pop()
                _,state,values,goal,start,target,started,duration,peak=history[-1]
                goal=goal.copy();start=start.copy();target=target.copy()
                for k,v in values.items():setattr(sim,k,v.copy())
                mujoco.mj_setState(sim.model,sim.data,state,state_spec)
                mujoco.mj_forward(sim.model,sim.data)
                ended=bool(sim.landed() or sim.data.time>=10-1e-9)
            elif not ended:
                radius=getattr(sim,'radius',.12)
                raw=np.array([command.x,command.y])*radius
                new_goal=raw/max(1.,np.linalg.norm(raw)/radius) if isinstance(sim,RailSim) else project_triangle(raw,sim.attachments[:,:2])
                if not np.allclose(new_goal,goal,atol=1e-12,rtol=0) or duration!=command.move_seconds:
                    start=target.copy();goal=new_goal;started=sim.data.time;duration=command.move_seconds
                for _ in range(max(1,round((command.interval_s if command.interval_s is not None else .02)/sim.c.dt))):
                    if sim.landed() or sim.data.time>=10-1e-9:break
                    sim.wind=wind.at(sim.data.time)
                    fraction=1. if duration==0 else min(1.,(sim.data.time+sim.c.dt-started)/duration)
                    blend=1. if sim.planar else fraction*fraction*(3-2*fraction)
                    target=start+(goal-start)*blend
                    if command.input_mode=='velocity':
                        direction=np.array([command.x,command.y],dtype=float);direction/=max(1.,np.linalg.norm(direction))
                        rot=sim.data.xmat[sim.hub].reshape(3,3)
                        current=(rot.T@(sim.data.xpos[sim.payload]-sim.data.xpos[sim.hub]))[:2]
                        raw=current+direction*command.velocity_mm_s/1000*sim.c.dt
                        target=raw/max(1.,np.linalg.norm(raw)/radius) if isinstance(sim,RailSim) else project_triangle(raw,sim.attachments[:,:2])
                        goal=target.copy()
                    if isinstance(sim,DirectSim):
                        local=np.r_[sim.data.qpos[7:9],sim.data.qpos[9]-sim.hang]
                        delta=local-sim.attachments
                        jacobian=delta/np.maximum(np.linalg.norm(delta,axis=1)[:,None],1e-12)
                        velocity=np.array([command.x,command.y,command.z],dtype=float)
                        velocity/=max(1.,np.linalg.norm(velocity))
                        rates=jacobian@velocity*command.velocity_mm_s/1000
                        action=rates/max(sim.motor_speed,float(np.max(np.abs(rates))))
                        sim.step(action,sim.wind)
                        goal=local[:2]+velocity[:2]*command.velocity_mm_s/1000*sim.c.dt
                        target=goal.copy();sim.active_target_xy=goal.copy()
                    elif command.input_mode=='velocity' and isinstance(sim,RailSim):
                        sim.step(target/radius,sim.wind,velocity=direction*command.velocity_mm_s/1000)
                    else:sim.step(target/radius,sim.wind)
                    peak=max(peak,float(sim.record()[2]))
                    sim.wind=wind.at(min(10,sim.data.time))
                    remember()
                sim.wind=wind.at(min(10,sim.data.time))
                ended=bool(sim.landed() or sim.data.time>=10-1e-9)
            await emit({'frame':snapshot(sim),'ended':ended,'max_tilt':peak,
                'goal_xy':goal.tolist(),'goal_lengths':(sim.target_lengths if isinstance(sim,DirectSim) else sim.lengths_for_target(goal)).tolist(),
                'move_remaining':max(0.,duration-(sim.data.time-started)),
                'rewound':command.kind=='rewind','move_seconds':duration,
                'termination':('ground' if sim.landed() else 'timeout') if ended else None},command)
    except WebSocketDisconnect:
        pass


# Background computation keeps manual game websocket responsive.
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from rail_strategy import rollout
strategy_executor=ThreadPoolExecutor(max_workers=1)
strategy_lock=Lock()
strategy_jobs={}
STRATEGY_DIR=Path(__file__).parent/'outputs'/'strategy_runs'
class StrategyRequest(BaseModel):
    strategy: Literal['mpc','center']='mpc'
    quality: Literal['fast','fine']='fast'
    parameters: Experiment

def strategy_path(job_id):
    if not re.fullmatch(r'[a-f0-9]{32}',job_id):raise HTTPException(404,'Unknown run')
    return STRATEGY_DIR/(job_id+'.json')

def compute_strategy(job_id,request):
    try:
        def progress(t):
            with strategy_lock:strategy_jobs[job_id].update(status='running',time_s=t)
        result=rollout(request.parameters,request.strategy,request.quality,progress)
        STRATEGY_DIR.mkdir(parents=True,exist_ok=True)
        path=strategy_path(job_id);temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(result));temp.replace(path)
        with strategy_lock:strategy_jobs[job_id].update(status='complete',summary=result['summary'])
    except Exception as exc:
        with strategy_lock:strategy_jobs[job_id].update(status='failed',error=str(exc))

@app.post('/api/game/strategies')
def start_strategy(request: StrategyRequest):
    if request.parameters.mechanism!='C' or request.parameters.variant!='B':
        raise HTTPException(422,'현재 자동 전략은 C 회전 레일 모델만 지원합니다.')
    with strategy_lock:
        if any(j['status'] in ('queued','running') for j in strategy_jobs.values()):
            raise HTTPException(409,'이미 계산 중입니다. 완료 후 다시 실행하세요.')
        job_id=uuid4().hex
        strategy_jobs[job_id]=dict(id=job_id,status='queued',time_s=0,seconds=request.parameters.seconds)
    strategy_executor.submit(compute_strategy,job_id,request)
    return dict(id=job_id)

@app.get('/api/game/strategies')
def list_strategies():
    result=[]
    for path in sorted(STRATEGY_DIR.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
        try:
            d=json.loads(path.read_text());result.append(dict(id=path.stem,strategy=d['strategy'],agent_name=d.get('agent_name'),quality=d['quality'],diameter_mm=d['settings'].get('dome_diameter_mm',240),summary=d['summary']))
        except (ValueError,KeyError):continue
    return result

@app.get('/api/game/strategies/{job_id}')
def strategy_status(job_id: str):
    path=strategy_path(job_id)
    with strategy_lock:
        if job_id in strategy_jobs:return dict(strategy_jobs[job_id])
    if path.exists():return dict(id=job_id,status='complete')
    raise HTTPException(404,'Unknown run')

@app.get('/api/game/strategies/{job_id}/result')
def strategy_result(job_id: str):
    path=strategy_path(job_id)
    if not path.exists():raise HTTPException(404,'아직 완료되지 않았습니다.')
    return FileResponse(path,media_type='application/json')

from training_dashboard import list_runs

@app.get('/api/training')
def training_status():
    return {'runs': list_runs(Path(__file__).parent/'outputs')}

@app.get('/api/challenge/results')
def challenge_results():
    results=[]
    for path in STRATEGY_DIR.glob('evaluation-*.json'):
        try:
            row=json.loads(path.read_text())
            results.append(row)
        except (OSError,ValueError):continue
    return sorted(results,key=lambda r:r['score'],reverse=True)

@app.get('/api/challenge/package')
def challenge_package():
    path=Path(__file__).parent/'participant-kit.zip'
    if not path.is_file():raise HTTPException(404,'Package not built')
    return FileResponse(path,filename='skysailor-380-v1.zip')

from benchmark import router as benchmark_router
app.include_router(benchmark_router)
from manual_arena import router as manual_router
app.include_router(manual_router)

static = Path(__file__).parent/'web'/'dist'
if static.exists():
    app.mount('/', StaticFiles(directory=static, html=True), name='dashboard')
