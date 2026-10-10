from pathlib import Path
from threading import BoundedSemaphore
from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict,Field
from cap_drop import simulate,loads
import numpy as np

class Settings(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    shell_g:float=Field(4,ge=.5,le=100)
    ballast_g:float=Field(6,ge=.5,le=100)
    com_x_mm:float=Field(0)
    com_y_mm:float=Field(0)
    com_z_mm:float=Field(-40)
    height:float=Field(3,ge=.5,le=10)
    tilt:float=Field(10,ge=0,le=180)
    wind_x:float=Field(0,ge=-3,le=3)
    wind_y:float=Field(0,ge=-3,le=3)
    rotation_damping:bool=True
    seconds:float=Field(8,ge=.1,le=15)

app=FastAPI(title='Rigid cap drop — preliminary CFD')
slots=BoundedSemaphore(2)
@app.post('/api/simulate')
def run(p:Settings):
    if not slots.acquire(False):raise HTTPException(503,'계산 중입니다. 잠시 후 다시 실행해주세요.')
    try:return simulate(p.model_dump())
    except ValueError as e:raise HTTPException(422,str(e)) from e
    finally:slots.release()
class PoseSettings(Settings):
    airspeed:float=Field(1.6,ge=0,le=15)
    azimuth:float=Field(0,ge=-180,le=180)

@app.post('/api/pose')
def pose(p:PoseSettings):
    theta,phi=np.radians([p.tilt,p.azimuth])
    cy,sy=np.cos(theta),np.sin(theta)
    cz,sz=np.cos(phi),np.sin(phi)
    rot=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    com=np.array([p.com_x_mm,p.com_y_mm,p.com_z_mm])/1000
    force,moment,alpha=loads(rot.T@np.array([0,0,p.airspeed]),com)
    force=rot@force;moment=rot@moment
    gravity=np.array([0,0,-(p.shell_g+p.ballast_g)/1000*9.81])
    return dict(force=force.tolist(),gravity=gravity.tolist(),net=(force+gravity).tolist(),
                torque=moment.tolist(),com=(rot@com).tolist(),alpha=alpha)

app.mount('/',StaticFiles(directory=Path(__file__).parent/'web/dist/cap',html=True),name='cap')
