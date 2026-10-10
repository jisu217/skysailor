"""Rotating diameter rail on a rigid circular guide below the cap.

Hinge torque is bounded; the carriage has an ideal speed-limited linear drive.
All masses and internal reaction forces are coupled through MuJoCo dynamics.
The preliminary CFD loads act on the cap only (no rail/guide drag).
"""
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from clover import Config
from dome import DomeSim, RADIUS, PAYLOAD_MASS, patches, model_xml


class RailSim(DomeSim):
    def __init__(self, config=None, payload_mass=PAYLOAD_MASS, rail_mass=.005,
                 support_mass=.003, drop=.04, linear_speed=.08,
                 torque_limit=.002, angular_speed=np.pi, radius=.12, depth=.06, dome_mass=.0042, linear_force_limit=None, linear_accel_limit=None):
        self.radius=float(radius);self.depth=float(depth);self.dome_mass=float(dome_mass)
        if min(self.radius,self.depth,self.dome_mass)<=0 or self.depth>self.radius:raise ValueError("Invalid cap dimensions")
        self.linear_force_limit=linear_force_limit;self.linear_accel_limit=linear_accel_limit
        self.c=config or Config()
        values=[payload_mass,rail_mass,support_mass,drop,linear_speed,torque_limit,angular_speed]
        if not np.all(np.isfinite(values)) or min(values)<=0:raise ValueError('Rail parameters must be positive and finite')
        self.payload_mass=float(payload_mass);self.rail_mass=float(rail_mass)
        self.support_mass=float(support_mass);self.hang=float(drop)
        self.linear_speed=float(linear_speed);self.torque_limit=float(torque_limit);self.angular_speed=float(angular_speed)
        self.planar=True;self.cable_count=0;self.attachments=np.empty((0,3))
        self.target_xy=np.zeros(2);self.target_payload=np.array([0.,0.,-drop]);self.line_length=0.
        self.panels=patches(self.radius,self.depth)
        root=ET.fromstring(model_xml(self.c,self.panels,self.attachments,drop,payload_mass,True,radius=self.radius,depth=self.depth,dome_mass=self.dome_mass))
        hub=root.find("./worldbody/body[@name='hub']")
        hub.remove(hub.find("body[@name='payload']"))
        # Fixed guide: 2/3 of support mass in a thin ring, 1/3 in a thin shaft.
        ring_mass=support_mass*2/3;shaft_mass=support_mass/3
        com_z=-(ring_mass*drop+shaft_mass*drop/2)/support_mass
        ixy=ring_mass*(self.radius**2/2+(-drop-com_z)**2)+shaft_mass*(drop**2/12+.002**2/4+(-drop/2-com_z)**2)
        iz=ring_mass*self.radius**2+shaft_mass*.002**2/2
        guide=ET.SubElement(hub,'body',name='guide')
        ET.SubElement(guide,'inertial',pos=f'0 0 {com_z}',mass=str(support_mass),diaginertia=f'{ixy} {ixy} {iz}')
        ET.SubElement(guide,'geom',name='shaft',type='cylinder',size=f'.002 {drop/2}',pos=f'0 0 {-drop/2}',rgba='.65 .75 .8 1')
        for i in range(32):
            a=i*2*np.pi/32;b=(i+1)*2*np.pi/32
            ends=[self.radius*np.cos(a),self.radius*np.sin(a),-drop,self.radius*np.cos(b),self.radius*np.sin(b),-drop]
            ET.SubElement(guide,'geom',name=f'guide{i}',type='capsule',size='.0015',fromto=' '.join(map(str,ends)),rgba='.5 .65 .75 1')
        beam=ET.SubElement(guide,'body',name='rail',pos=f'0 0 {-drop}')
        ET.SubElement(beam,'joint',name='rail_angle',type='hinge',axis='0 0 1',damping='0')
        ET.SubElement(beam,'geom',name='rail_beam',type='box',size=f'{self.radius} .003 .002',mass=str(rail_mass),rgba='.95 .65 .25 1')
        for i,x in enumerate([-self.radius,self.radius]):ET.SubElement(beam,'site',name=f'rail_end{i}',pos=f'{x} 0 0')
        payload=ET.SubElement(beam,'body',name='payload')
        ET.SubElement(payload,'joint',name='rail_position',type='slide',axis='1 0 0',damping='0',limited='true',range=f'{-self.radius} {self.radius}')
        ET.SubElement(payload,'geom',name='carriage',type='box',size='.012 .01 .007',mass=str(payload_mass),rgba='.95 .4 .7 1')
        ET.SubElement(payload,'site',name='anchor')
        self.model=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))
        self.model.opt.integrator=mujoco.mjtIntegrator.mjINT_EULER
        self.data=mujoco.MjData(self.model)
        self.hub=self.model.body('hub').id;self.payload=self.model.body('payload').id
        self.rail_body=self.model.body('rail').id
        self.anchor=self.model.site('anchor').id;self.tips=[]
        self.air_sites=[self.model.site(f'air{i}').id for i in range(24)]
        self.rail_ends=[self.model.site(f'rail_end{i}').id for i in range(2)]
        self.angle_qpos=self.model.jnt_qposadr[self.model.joint('rail_angle').id]
        self.payload_qpos=self.model.jnt_qposadr[self.model.joint('rail_position').id]
        self.reset()

    def reset(self,tilt_deg=15,seed=0):
        mujoco.mj_resetData(self.model,self.data)
        angle=np.random.default_rng(seed).uniform(-np.pi,np.pi)
        half=np.deg2rad(tilt_deg)/2
        self.data.qpos[3:7]=np.r_[np.cos(half),np.array([np.cos(angle),np.sin(angle),0])*np.sin(half)]
        self.wind=np.zeros(3);self.active_target_xy=np.zeros(2)
        self.spool=np.empty(0);self.target_lengths=np.empty(0);self.winch_rates=np.empty(0)
        self.winch_stalled=np.empty(0,dtype=bool);self.tensions=np.empty(0);self.rail_drive=np.zeros(2)
        mujoco.mj_forward(self.model,self.data)
        return self.observe()

    def validate_target(self,xy):
        xy=np.asarray(xy)
        if xy.shape!=(2,) or not np.all(np.isfinite(xy)) or np.linalg.norm(xy)>self.radius+1e-9:raise ValueError('Target must be inside the guide circle')

    def lengths_for_target(self,target):return np.empty(0)

    def cable_state(self,rest_rates=None):
        return dict(lengths=np.empty(0),directions=np.empty((0,3)),rates=np.empty(0),tension=np.empty(0),slack=np.empty(0,dtype=bool))

    def rail_goal(self):
        theta=self.data.qpos[self.angle_qpos];radius=np.linalg.norm(self.active_target_xy)
        if radius<1e-10:return theta,0.
        phi=np.arctan2(self.active_target_xy[1],self.active_target_xy[0])
        error=(phi-theta+np.pi/2)%np.pi-np.pi/2
        target_angle=theta+error
        signed_radius=radius*(1 if np.cos(phi-target_angle)>=0 else -1)
        return target_angle,signed_radius

    def step(self,action,wind=(0,0,0),velocity=None,drive=None):
        target=np.asarray(action,dtype=float)*self.radius;self.validate_target(target)
        self.active_target_xy=target.copy();self.wind=np.asarray(wind,dtype=float)
        theta_goal,r_goal=self.rail_goal()
        r=self.data.qpos[self.payload_qpos]
        # Linear drive speed is relative to the rotating beam, not world speed.
        next_r=r+np.clip(r_goal-r,-self.linear_speed*self.c.dt,self.linear_speed*self.c.dt)
        velocity_omega=None
        if velocity is not None:
            theta=self.data.qpos[self.angle_qpos]
            radial=np.array([np.cos(theta),np.sin(theta)]);tangent=np.array([-np.sin(theta),np.cos(theta)])
            vr=float(np.dot(velocity,radial))
            next_r=np.clip(r+np.clip(vr,-self.linear_speed,self.linear_speed)*self.c.dt,-self.radius,self.radius)
            if abs(r)>.002:
                velocity_omega=float(np.dot(velocity,tangent))/r
            elif np.linalg.norm(velocity)>1e-10:
                phi=np.arctan2(velocity[1],velocity[0]);error=(phi-theta+np.pi/2)%np.pi-np.pi/2
                velocity_omega=8*error*min(1.,np.linalg.norm(velocity)/self.linear_speed)
            else:velocity_omega=0.
        if drive is not None:
            drive=np.asarray(drive,dtype=float)
            if drive.shape!=(2,) or not np.all(np.isfinite(drive)):raise ValueError('Invalid motor drive')
            velocity_omega=float(np.clip(drive[0],-self.angular_speed,self.angular_speed))
            next_r=np.clip(r+np.clip(drive[1],-self.linear_speed,self.linear_speed)*self.c.dt,-self.radius,self.radius)
        desired_acc=((next_r-r)/self.c.dt-self.data.qvel[7])/self.c.dt
        if self.linear_accel_limit is not None:desired_acc=float(np.clip(desired_acc,-self.linear_accel_limit,self.linear_accel_limit))
        self.data.qfrc_applied[:]=0
        aero=self.aerodynamics()
        mujoco.mj_applyFT(self.model,self.data,aero['force'][0],aero['torque_com'],self.data.xipos[self.hub],self.hub,self.data.qfrc_applied)
        mass=np.empty((self.model.nv,self.model.nv));mujoco.mj_fullM(self.model,self.data,mass)
        inertia=mass[6,6]-mass[6,:6]@np.linalg.solve(mass[:6,:6],mass[:6,6])
        error=theta_goal-self.data.qpos[self.angle_qpos]
        omega_goal=np.clip(8*error if velocity_omega is None else velocity_omega,-self.angular_speed,self.angular_speed)
        torque=np.clip(inertia*(omega_goal-self.data.qvel[6])/.04,-self.torque_limit,self.torque_limit)
        self.data.qfrc_applied[6]=torque
        rhs=self.data.qfrc_applied+self.data.qfrc_passive-self.data.qfrc_bias
        free_acc=np.linalg.solve(mass[:7,:7],rhs[:7]-mass[:7,7]*desired_acc)
        force=mass[7,:7]@free_acc+mass[7,7]*desired_acc-self.data.qfrc_passive[7]+self.data.qfrc_bias[7]
        if self.linear_force_limit is not None:force=float(np.clip(force,-self.linear_force_limit,self.linear_force_limit))
        self.data.qfrc_applied[7]=force;self.rail_drive[:]=[torque,force]
        mujoco.mj_step(self.model,self.data);mujoco.mj_forward(self.model,self.data)
        if not np.all(np.isfinite(self.data.qpos)):raise FloatingPointError('Non-finite rail state')
        return self.observe()

    def rail_state(self):
        r=float(self.data.qpos[self.payload_qpos]);theta_goal,r_goal=self.rail_goal()
        inertia=float(self.model.body_inertia[self.rail_body,2]+self.model.body_inertia[self.payload,2]+self.payload_mass*r*r)
        return dict(angle=float(self.data.qpos[self.angle_qpos]),radius=r,angular_velocity=float(self.data.qvel[6]),
                    linear_velocity=float(self.data.qvel[7]),angle_goal=float(theta_goal),radius_goal=float(r_goal),
                    torque=float(self.rail_drive[0]),linear_force=float(self.rail_drive[1]),
                    axial_inertia=inertia,torque_limit=self.torque_limit,linear_speed_limit=self.linear_speed,
                    angular_speed_command_limit=self.angular_speed,ends=self.data.site_xpos[self.rail_ends].tolist())

    def target_com_world(self):
        point=self.data.xpos[self.hub]+self.data.xmat[self.hub].reshape(3,3)@np.r_[self.active_target_xy,-self.hang]
        return self.system_com()+self.payload_mass/self.model.body_mass.sum()*(point-self.data.xipos[self.payload])

    def landed(self):
        if super().landed():return True
        # Include the shaft, circular guide, beam and carriage in ground detection.
        for i in range(26,self.model.ngeom):
            size=self.model.geom_size[i];rot=self.data.geom_xmat[i].reshape(3,3);kind=self.model.geom_type[i]
            if kind==mujoco.mjtGeom.mjGEOM_BOX:extent=np.dot(np.abs(rot[2]),size)
            elif kind==mujoco.mjtGeom.mjGEOM_CAPSULE:extent=size[0]+size[1]*abs(rot[2,2])
            else:extent=size[0]*np.sqrt(max(0.,1-rot[2,2]**2))+size[1]*abs(rot[2,2])
            if self.data.geom_xpos[i,2]-extent<=0:return True
        return False
