"""Three axial, force-limited length servos meeting at a ball-jointed pendulum.
Actuator/support mass is lumped into the fixed ring (3g), connector mass 1g.
No drag on suspension; no self-collision. A lower-half workspace stop avoids
crossing the coplanar singularity. Pendulum and hub dynamics are fully coupled.
"""
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from clover import Config
from dome import DomeSim, patches, model_xml

class HangingSim(DomeSim):
    def __init__(self,payload_mass_g=18,ring_radius_mm=80,connector_drop_mm=60,pendulum_length_mm=50,actuator_speed_mm_s=30,direct=False):
        self.direct=direct
        if direct:ring_radius_mm=190
        self.c=Config();self.radius=.19;self.depth=.08;self.dome_mass=.025
        self.payload_mass=payload_mass_g/1000;self.ring_radius=ring_radius_mm/1000
        self.hang=connector_drop_mm/1000;self.pendulum_length=pendulum_length_mm/1000;self.motor_speed=actuator_speed_mm_s/1000
        self.planar=False;self.cable_count=3;self.force_limit=.5
        self.attachments=np.array([[self.ring_radius*np.cos(i*2*np.pi/3),self.ring_radius*np.sin(i*2*np.pi/3),0] for i in range(3)])
        self.panels=patches(self.radius,self.depth)
        root=ET.fromstring(model_xml(self.c,self.panels,self.attachments,self.hang,self.payload_mass,True,radius=self.radius,depth=self.depth,dome_mass=self.dome_mass))
        hub=root.find("./worldbody/body[@name='hub']");hub.remove(hub.find("body[@name='payload']"))
        guide=ET.SubElement(hub,'body',name='ring')
        rr=self.ring_radius;ET.SubElement(guide,'inertial',pos='0 0 0',mass='.003',diaginertia=f'{.003*rr*rr/2} {.003*rr*rr/2} {.003*rr*rr}')
        for i in range(32):
            a=i*2*np.pi/32;b=(i+1)*2*np.pi/32
            ET.SubElement(guide,'geom',type='capsule',size='.0015',fromto=f'{rr*np.cos(a)} {rr*np.sin(a)} 0 {rr*np.cos(b)} {rr*np.sin(b)} 0',rgba='.6 .75 .8 1')
        for a in ([] if direct else self.attachments):
            outer=a*self.radius/rr
            ET.SubElement(guide,'geom',type='capsule',size='.001',fromto=' '.join(map(str,[*a,*outer])),rgba='.6 .75 .8 1')
        joint=ET.SubElement(hub,'body',name='connector',pos=f'0 0 {-self.hang}')
        for name,axis,limits in [('cx','1 0 0',(-rr*.6,rr*.6)),('cy','0 1 0',(-rr*.6,rr*.6)),('cz','0 0 1',(-.04,min(.04,self.hang-.02)))]:
            ET.SubElement(joint,'joint',name=name,type='slide',axis=axis,**({'limited':'false'} if direct else {'limited':'true','range':f'{limits[0]} {limits[1]}'}))
        if direct:
            # Translation-only idealized point payload. No independent rotation or pendulum.
            ET.SubElement(joint,'inertial',pos='0 0 0',mass=str(self.payload_mass+.001),diaginertia='1e-10 1e-10 1e-10')
            ET.SubElement(joint,'site',name='anchor')
            payload=ET.SubElement(joint,'body',name='payload')
            ET.SubElement(payload,'geom',type='sphere',size='.01',mass='0',rgba='.95 .7 .3 1')
        else:
            ET.SubElement(joint,'geom',type='sphere',size='.004',mass='.001',rgba='.4 .9 .8 1');ET.SubElement(joint,'site',name='anchor')
            pendulum=ET.SubElement(joint,'body',name='pendulum');ET.SubElement(pendulum,'joint',name='swing',type='ball',damping='.00001')
            L=self.pendulum_length
            ET.SubElement(pendulum,'inertial',pos=f'0 0 {-L}',mass=str(self.payload_mass),diaginertia=' '.join([str(.4*self.payload_mass*.01**2)]*3))
            ET.SubElement(pendulum,'geom',type='capsule',size='.0008',fromto=f'0 0 0 0 0 {-L}',rgba='.8 .8 .8 1')
            payload=ET.SubElement(pendulum,'body',name='payload',pos=f'0 0 {-L}');ET.SubElement(payload,'geom',type='sphere',size='.01',mass='0',rgba='.95 .7 .3 1')
        # Each actuator's physical stroke: initial length ±30mm (soft MuJoCo stops).
        initial=np.hypot(rr,self.hang)
        for tendon in root.findall('./tendon/spatial'):
            tendon.set('limited','false' if direct else 'true')
            if not direct:tendon.set('range',f'{initial-.03} {initial+.03}')
        self.model=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'));self.data=mujoco.MjData(self.model)
        self.hub=self.model.body('hub').id;self.payload=self.model.body('payload').id;self.connector=self.model.body('connector').id
        self.anchor=self.model.site('anchor').id;self.tips=[self.model.site(f'tip{i}').id for i in range(3)];self.air_sites=[self.model.site(f'air{i}').id for i in range(24)]
        self.reset()
    def reset(self,tilt_deg=5,seed=0):
        mujoco.mj_resetData(self.model,self.data);a=np.random.default_rng(seed).uniform(-np.pi,np.pi);h=np.deg2rad(tilt_deg)/2
        self.data.qpos[3:7]=[np.cos(h),np.cos(a)*np.sin(h),np.sin(a)*np.sin(h),0]
        self.wind=np.zeros(3);self.active_target_xy=np.zeros(2);self.winch_rates=np.zeros(3);self.winch_stalled=np.zeros(3,dtype=bool);self.tensions=np.zeros(3)
        mujoco.mj_forward(self.model,self.data);self.spool=self.data.ten_length.copy();self.target_lengths=self.spool.copy()
    def cable_state(self,rest_rates=None):
        return dict(lengths=self.data.ten_length.copy(),slack=np.zeros(3,dtype=bool))
    def target_com_world(self):return self.system_com()
    def step(self,action,wind):
        self.wind=np.asarray(wind);self.data.qfrc_applied[:]=0
        aero=self.aerodynamics();mujoco.mj_applyFT(self.model,self.data,aero['force'][0],aero['torque_com'],self.data.xipos[self.hub],self.hub,self.data.qfrc_applied)
        self.spool=np.clip(self.spool+np.asarray(action)*self.motor_speed*self.c.dt,0. if self.direct else self.model.tendon_range[:,0],np.inf if self.direct else self.model.tendon_range[:,1]);self.target_lengths=self.spool.copy()
        local=np.r_[self.data.qpos[7:9],self.data.qpos[9]-self.hang]
        delta=local-self.attachments;J=delta/np.maximum(np.linalg.norm(delta,axis=1)[:,None],1e-12)
        rates=J@self.data.qvel[6:9]
        # Axial force servo, positive force extends. Forces map to relative slides,
        # so equal/opposite internal reactions are handled by the coupled mass matrix.
        force=np.clip(80*(self.spool-self.data.ten_length)-1.2*rates,-self.force_limit,self.force_limit)
        self.data.qfrc_applied[6:9]=J.T@force;self.tensions=force;self.winch_rates=rates;self.winch_stalled=np.abs(force)>=self.force_limit-1e-8
        mujoco.mj_step(self.model,self.data);mujoco.mj_forward(self.model,self.data)
        if not np.isfinite(self.data.qpos).all():raise FloatingPointError('Nonfinite suspension')
    def landed(self):
        if super().landed():return True
        # Fixed ring/supports, connector and pendulum rod are capsule/sphere geoms.
        for i in range(26,self.model.ngeom):
            size=self.model.geom_size[i];rot=self.data.geom_xmat[i].reshape(3,3)
            extent=size[0]+(size[1]*abs(rot[2,2]) if self.model.geom_type[i]==mujoco.mjtGeom.mjGEOM_CAPSULE else 0)
            if self.data.geom_xpos[i,2]-extent<=0:return True
        return False

class HangingEnv:
    sim_class=HangingSim
    def __init__(self,hardware,wind_mode='measured'):
        from dashboard import Experiment
        self.hardware=hardware;self.params=Experiment(variant='B',mechanism='H',dome_diameter_mm=380,dome_mass_g=25,wind_mode=wind_mode,seconds=10,payload_mass_g=hardware['payload_mass_g'])
        self.last_action=np.zeros(3)
    def reset(self,seed=0):
        from dashboard import WindProfile
        rng=np.random.default_rng(seed);clip=str(rng.choice(['gentle','up','down']));self.wind=WindProfile(self.params.model_copy(update={'wind_clip':clip}))
        self.sim=self.sim_class(**self.hardware);self.sim.reset(float(rng.uniform(3,15)),int(rng.integers(0,100000)));self.sim.wind=self.wind.at(0);self.last_action=np.zeros(3);self.done=False
        return self.observation(),{'wind_clip':clip}
    def observation(self):
        s=self.sim;R=s.data.xmat[s.hub].reshape(3,3);v=np.zeros(6);mujoco.mj_objectVelocity(s.model,s.data,mujoco.mjtObj.mjOBJ_BODY,s.hub,v,0)
        local=R.T@(s.data.xpos[s.connector]-s.data.xpos[s.hub]);direction=R.T@(s.data.xpos[s.payload]-s.data.xpos[s.connector])/s.pendulum_length
        return np.r_[R.T@[0,0,1],R.T@v[:3]/10,R.T@(s.wind-v[3:])/10,s.data.xpos[s.hub,2]/3,local/.2,s.data.qvel[6:9]/.1,direction,s.data.qvel[9:12]/10,s.data.ten_length/.3,self.last_action].astype(np.float32)
    def step(self,action):
        a=np.asarray(action,dtype=float)
        if self.done or a.shape!=(3,) or not np.isfinite(a).all():raise ValueError('Invalid step')
        a=np.clip(a,-1,1);s=self.sim;score=0.
        for _ in range(20):
            if s.landed() or s.data.time>=10-1e-9:break
            h=max(0.,s.system_com()[2]);t=s.data.time;s.step(a,self.wind.at(t))
            if s.data.time<=t:raise FloatingPointError('Integration reset')
            score+=(h+max(0.,s.system_com()[2]))*.5*(s.data.time-t)
        self.last_action=a;done=s.landed();timeout=s.data.time>=10-1e-9 and not done;self.done=done or timeout
        return self.observation(),float(score),done,timeout,dict(time_s=float(s.data.time),tilt_deg=float(s.record()[2]))
    def close(self):pass

class DirectSim(HangingSim):
    def __init__(self,payload_mass_g=18,connector_drop_mm=60,actuator_speed_mm_s=30):
        super().__init__(payload_mass_g=payload_mass_g,connector_drop_mm=connector_drop_mm,actuator_speed_mm_s=actuator_speed_mm_s,direct=True)

class DirectEnv(HangingEnv):
    sim_class=DirectSim
    def __init__(self,hardware,wind_mode='measured'):
        super().__init__(hardware,wind_mode)
        self.params=self.params.model_copy(update={'mechanism':'P'})
    def observation(self):
        s=self.sim;R=s.data.xmat[s.hub].reshape(3,3);v=np.zeros(6)
        mujoco.mj_objectVelocity(s.model,s.data,mujoco.mjtObj.mjOBJ_BODY,s.hub,v,0)
        local=R.T@(s.data.xpos[s.connector]-s.data.xpos[s.hub])
        return np.r_[R.T@[0,0,1],R.T@v[:3]/10,R.T@(s.wind-v[3:])/10,s.data.xpos[s.hub,2]/3,local/.2,s.data.qvel[6:9]/.1,s.data.ten_length/.3,self.last_action].astype(np.float32)
