"""50 Hz ideal-state feedback for the B three-winch payload; ideal sensors; preliminary CFD dome loads."""
from dataclasses import replace
import numpy as np
import mujoco
from dome import DomeSim, RADIUS, DOME_MASS, PAYLOAD_MASS, CAP_HEIGHT

CONTROL_PERIOD = .02
OPTIMIZED_GAINS = (.13025789019862935, .028998845326895988, .0002151458954118229, .00026057057690896847)

MASS_FRACTION = PAYLOAD_MASS/(DOME_MASS+PAYLOAD_MASS)


def project_triangle(xy, vertices):
    """Euclidean projection onto the closed support triangle."""
    xy=np.asarray(xy,dtype=float)
    if xy.shape != (2,) or not np.all(np.isfinite(xy)):
        raise ValueError('Non-finite B controller target')
    edges=np.roll(vertices,-1,axis=0)-vertices;offset=xy-vertices
    if np.all(edges[:,0]*offset[:,1]-edges[:,1]*offset[:,0]>=0):return xy.copy()
    candidates=[]
    for a,b in zip(vertices,np.roll(vertices,-1,axis=0)):
        edge=b-a
        candidates.append(a+np.clip(np.dot(xy-a,edge)/np.dot(edge,edge),0,1)*edge)
    return min(candidates,key=lambda p:np.linalg.norm(p-xy)).copy()


class BController:
    def __init__(self, algorithm='pd', kp=.08, kd=.02, torque_kp=.001, torque_kd=.0004):
        if algorithm not in ('manual','center','p','pd','aero_pd','optimized','position','predictive'):
            raise ValueError('Unknown B algorithm')
        self.algorithm=algorithm
        self.tuned_active = None
        if algorithm == 'position':
            kp,kd,torque_kp,torque_kd=.08,.02,.006,.002
        self.kp,self.kd=kp,kd
        self.torque_kp,self.torque_kd=torque_kp,torque_kd
        self.next_update=0.
        self.target=np.zeros(2)
        self.saturated=False
        self.predictor=None
        self.world_target=np.zeros(2)
        self.position_kp=1.
        self.position_kd=1.
        self.max_target_tilt=np.deg2rad(15)

    def action(self, sim):
        if sim.data.time+1e-9 >= self.next_update:
            self.next_update=sim.data.time+CONTROL_PERIOD
            rot=sim.data.xmat[sim.hub].reshape(3,3)
            up=rot.T@np.array([0.,0.,1.])
            if self.algorithm == 'optimized' and self.tuned_active is None:
                # Select once at launch; avoid gain switching as the dome oscillates.
                self.tuned_active = bool(up[2] >= np.cos(np.deg2rad(25))-1e-12)
                if self.tuned_active:
                    self.kp,self.kd,self.torque_kp,self.torque_kd=OPTIMIZED_GAINS
            if self.algorithm == 'position':
                vcom=np.zeros(3)
                for body in (sim.hub,sim.payload):
                    v=np.zeros(6)
                    mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,body,v,0)
                    vcom+=sim.model.body_mass[body]*v[3:]
                vcom/=(DOME_MASS+PAYLOAD_MASS)
                lean=self.position_kp*(self.world_target-sim.system_com()[:2])-self.position_kd*vcom[:2]
                limit=np.tan(self.max_target_tilt)
                lean*=min(1.,limit/max(np.linalg.norm(lean),1e-12))
                normal=np.r_[lean,1.];normal/=np.linalg.norm(normal)
                up=rot.T@normal
            velocity=np.zeros(6)
            mujoco.mj_objectVelocity(sim.model,sim.data,mujoco.mjtObj.mjOBJ_BODY,sim.hub,velocity,1)
            tilt_rate=np.array([velocity[1],-velocity[0]])
            raw=self.kp*up[:2]
            if self.algorithm in ('pd','aero_pd','optimized','position','predictive'):raw-=self.kd*tilt_rate
            if self.algorithm=='manual':raw=sim.target_xy.copy()
            elif self.algorithm=='center':raw=np.zeros(2)
            elif self.algorithm in ('aero_pd','optimized','position','predictive'):
                aero=sim.aerodynamics()
                force=rot.T@aero['force'].sum(axis=0)
                moment=rot.T@aero['torque_origin']
                com_z=(rot.T@(sim.system_com()-sim.data.xpos[sim.hub]))[2]
                # Low dynamic pressure gives negligible attitude authority: use PD until Fz grows.
                if force[2]>.015:
                    desired=self.torque_kp*np.array([-up[1],up[0]])-self.torque_kd*velocity[:2]
                    raw=np.array([desired[1]-moment[1]+com_z*force[0],
                                  moment[0]+com_z*force[1]-desired[0]])/(force[2]*MASS_FRACTION)
            if self.algorithm=='predictive':raw=self.predictive_target(sim,raw)
            self.target=project_triangle(raw,sim.attachments[:,:2])
            self.saturated=bool(np.linalg.norm(raw-self.target)>1e-8)
        sim.active_target_xy=self.target.copy()
        sim.target_lengths=sim.lengths_for_target(self.target)
        return self.target/RADIUS

    def predictive_target(self, sim, base):
        """Short model rollouts: push briefly, then use damping feedback to brake.

        Uses the same force and command-speed bounds. 5 ms prediction steps are
        an approximation of the 1 ms live model, not an optimal-control guarantee.
        """
        if self.predictor is None:
            self.predictor=DomeSim(replace(sim.c,dt=.005),line_length=sim.line_length)
        pred=self.predictor
        bounded=project_triangle(base,sim.attachments[:,:2])
        direction=bounded/max(np.linalg.norm(bounded),1e-9)
        far=project_triangle(direction*.18,sim.attachments[:,:2])
        reverse=project_triangle(-direction*.18,sim.attachments[:,:2])
        # Baseline feedback, brief/higher pushes, reverse braking, and center return.
        candidates=[(bounded,0.),(far,.06),(far,.14),(reverse,.06),(np.zeros(2),.08)]
        best=bounded;best_cost=float('inf')
        for first,hold in candidates:
            mujoco.mj_resetData(pred.model,pred.data)
            pred.data.qpos[:]=sim.data.qpos;pred.data.qvel[:]=sim.data.qvel
            pred.data.ctrl[:]=sim.data.ctrl;pred.data.time=sim.data.time
            pred.spool=sim.spool.copy();pred.wind=sim.wind.copy()
            pred.winch_rates=sim.winch_rates.copy();pred.winch_stalled=sim.winch_stalled.copy()
            mujoco.mj_forward(pred.model,pred.data)
            feedback=BController('aero_pd',self.kp,self.kd,self.torque_kp,self.torque_kd)
            cost=0.
            for k in range(60):
                action=first/RADIUS if k*.005<hold else feedback.action(pred)
                pred.step(action,sim.wind)
                angle=np.arccos(np.clip(pred.data.xmat[pred.hub].reshape(3,3)[2,2],-1,1))
                velocity=np.zeros(6)
                mujoco.mj_objectVelocity(pred.model,pred.data,mujoco.mjtObj.mjOBJ_BODY,pred.hub,velocity,1)
                cost+=.005*(angle**2+.025*np.dot(velocity[:2],velocity[:2]))
            cost+=angle**2+.04*np.dot(velocity[:2],velocity[:2])
            if cost<best_cost:best_cost=cost;best=first
        return best
