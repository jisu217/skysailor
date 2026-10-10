"""Rigid cap drop using preliminary static CFD; optional exploratory pitch damping."""
from pathlib import Path
import json
import mujoco
import numpy as np

SOURCE=Path(__file__).parent/'web/src/cap/loads.json'
ROWS=json.loads(SOURCE.read_text())['results']
ANGLES=np.array([r['angle_deg'] for r in ROWS])
COEFF=np.array([[r['force_coeff_body'][0],r['force_coeff_body'][2],r['moment_coeff_body'][1]] for r in ROWS])
# Axisymmetric mean model: remove transverse force/moment at axial incidence.
COEFF[[0,-1],0]=0;COEFF[[0,-1],2]=0
AREA=np.pi*.12**2
DAMPING=json.loads((SOURCE.parent/"rotation_damping.json").read_text())

def damping_torque(omega_body,rho=1.225):
    # Axisymmetry extends pitch damping to x/y tilt; axial spin was not measured.
    return -DAMPING["coefficient_Nm_s_per_rad"]*(rho/DAMPING["reference_density"])*np.asarray(omega_body)*np.array([1.,1.,0.])



def loads(relative_body,com,rho=1.225,radius=.12):
    speed=np.linalg.norm(relative_body)
    if speed<1e-8 or rho==0:return np.zeros(3),np.zeros(3),0.
    alpha=np.degrees(np.arccos(np.clip(relative_body[2]/speed,-1,1)))
    fx,fz,my=[np.interp(alpha,ANGLES,COEFF[:,j]) for j in range(3)]
    transverse=np.linalg.norm(relative_body[:2])
    # Canonical incoming air is (-sin(alpha),0,cos(alpha)).
    xaxis=np.r_[-relative_body[:2]/transverse,0] if transverse>1e-10 else np.array([1.,0,0])
    yaxis=np.cross([0,0,1],xaxis)
    scale=.5*rho*speed**2*np.pi*radius**2
    force=scale*(fx*xaxis+fz*np.array([0,0,1]))
    moment=scale*(2*radius)*my*yaxis-np.cross(com,force)
    return force,moment,float(alpha)


def mass_properties(shell_g,ballast_g,com):
    ms,mb=shell_g/1000,ballast_g/1000;mass=ms+mb
    shell_com=np.array([0,0,.03]);com=np.asarray(com)
    ballast=(mass*com-ms*shell_com)/mb
    inertia=np.diag(ms*np.array([.0042,.0042,.0078]))
    for m,point in [(ms,shell_com),(mb,ballast)]:
        r=point-com;inertia+=m*(np.dot(r,r)*np.eye(3)-np.outer(r,r))
    return mass,ballast,inertia


def simulate(p,dt=.001):
    com=np.array([p['com_x_mm'],p['com_y_mm'],p['com_z_mm']])/1000
    mass,ballast,inertia=mass_properties(p['shell_g'],p['ballast_g'],com)
    vec=lambda a:' '.join(f'{x:.15g}' for x in a)
    full=[inertia[0,0],inertia[1,1],inertia[2,2],inertia[0,1],inertia[0,2],inertia[1,2]]
    xml=f'''<mujoco><option timestep="{dt}" gravity="0 0 -9.81" integrator="RK4"/>
    <worldbody><body name="cap"><freejoint/><inertial pos="{vec(com)}" mass="{mass}" fullinertia="{vec(full)}"/></body></worldbody></mujoco>'''
    model=mujoco.MjModel.from_xml_string(xml);data=mujoco.MjData(model)
    half=np.deg2rad(p['tilt'])/2;data.qpos[3:7]=[np.cos(half),0,np.sin(half),0]
    data.qpos[:3]=[0,0,p['height']];mujoco.mj_forward(model,data)
    wind=np.array([p['wind_x'],p['wind_y'],0]);frames=[];peak_spin=0.;peak_ratio=0.;termination='timeout'
    # Exact spherical-cap support points in the direction of world -z.
    def clearance():
        rot=data.xmat[1].reshape(3,3);direction=rot[2,:]
        horizontal=np.linalg.norm(direction[:2]);rim=-.12*horizontal
        tip=.06*direction[2]
        # Sphere centre z=-.09, polar cosine in [.6,1].
        candidate=-.09*direction[2]-.15 if -direction[2]>=.6 else np.inf
        return min(data.xpos[1,2]+min(rim,tip,candidate), (data.xpos[1]+rot@ballast)[2])
    def evaluate():
        rot=data.xmat[1].reshape(3,3);vel=np.empty(6)
        mujoco.mj_objectVelocity(model,data,mujoco.mjtObj.mjOBJ_BODY,1,vel,0)
        # mj_objectVelocity(BODY) is evaluated at body COM.
        relative=rot.T@(wind-vel[3:]);force,moment,alpha=loads(relative,com,p.get('rho',1.225))
        if p.get("rotation_damping",True):
            moment+=damping_torque(rot.T@vel[:3],p.get("rho",1.225))
        return rot,vel,rot@force,rot@moment,alpha,np.linalg.norm(relative)
    def frame():
        rot,vel,force,moment,alpha,speed=evaluate()
        damping=rot@damping_torque(rot.T@vel[:3],p.get("rho",1.225)) if p.get("rotation_damping",True) else np.zeros(3)
        return dict(t=float(data.time),position=data.xpos[1].tolist(),quaternion=data.qpos[3:7].tolist(),
            com=data.xipos[1].tolist(),ballast=(data.xpos[1]+rot@ballast).tolist(),
            force=force.tolist(),torque=moment.tolist(),torque_aero=(moment-damping).tolist(),
            torque_damping=damping.tolist(),angular_velocity=vel[:3].tolist(),velocity=vel[3:].tolist(),
            speed=float(np.linalg.norm(vel[3:])),tilt=float(np.degrees(np.arccos(np.clip(rot[2,2],-1,1)))),
            alpha=alpha,spin=float(np.linalg.norm(vel[:3])),clearance=float(clearance()))
    if clearance()<=0:raise ValueError('초기 자세에서 물체가 지면 아래에 있습니다. 시작 높이를 높여주세요.')
    frames.append(frame())
    for step in range(int(p['seconds']/dt)):
        rot,vel,force,moment,alpha,speed=evaluate()
        # xfrc_applied is a world force and torque about the COM (shift only once).
        data.xfrc_applied[1,:3]=force;data.xfrc_applied[1,3:]=moment
        mujoco.mj_step(model,data);mujoco.mj_forward(model,data)
        if not np.all(np.isfinite(data.qpos)) or np.max(np.abs(data.qvel))>1e4:
            raise ValueError('운동 계산이 불안정합니다. 질량·무게중심 설정을 완화해주세요.')
        spin=np.linalg.norm(vel[:3]);peak_spin=max(peak_spin,spin)
        if speed>.1:peak_ratio=max(peak_ratio,spin*.24/speed)
        if (step+1)%10==0:frames.append(frame())
        if clearance()<=0:
            termination='ground';break
    if abs(frames[-1]['t']-data.time)>1e-8:frames.append(frame())
    return dict(parameters=p,rotation_damping=dict(enabled=p.get("rotation_damping",True),**DAMPING),frames=frames,ballast_body=ballast.tolist(),inertia=inertia.tolist(),
        summary=dict(duration=float(data.time),termination=termination,peak_spin_deg_s=float(np.degrees(peak_spin)),
        peak_rotation_ratio=float(peak_ratio),max_tilt=max(f['tilt'] for f in frames),
        horizontal_distance=float(np.linalg.norm(np.array(frames[-1]['com'])[:2]-np.array(frames[0]['com'])[:2]))))
