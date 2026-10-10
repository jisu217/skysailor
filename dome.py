"""B: rigid shallow cap and free payload connected by three unilateral, winched cables.

Aerodynamics use the preliminary 6 cm cap CFD lookup and exploratory tilt damping.
"""
import numpy as np
import mujoco
from clover import CloverSim, Config
from cap_drop import loads, damping_torque

RADIUS = .12
CAP_HEIGHT = .06
SPHERE_RADIUS = (RADIUS**2+CAP_HEIGHT**2)/(2*CAP_HEIGHT)
MU_MIN = 1-CAP_HEIGHT/SPHERE_RADIUS
DOME_MASS = .0042
PAYLOAD_MASS = .004
HANG = .12


def patches(radius=RADIUS, depth=CAP_HEIGHT):
    CAP_HEIGHT=depth;SPHERE_RADIUS=(radius**2+depth**2)/(2*depth);MU_MIN=1-depth/SPHERE_RADIUS
    result = []
    def point(mu, phi):
        return SPHERE_RADIUS*np.array([np.sqrt(max(0,1-mu*mu))*np.cos(phi),np.sqrt(max(0,1-mu*mu))*np.sin(phi),mu])+[0,0,CAP_HEIGHT-SPHERE_RADIUS]
    for band in range(3):
        for sector in range(8):
            mus = np.linspace(MU_MIN+(1-MU_MIN)*band/3,MU_MIN+(1-MU_MIN)*(band+1)/3,5)
            phis = np.linspace(sector*np.pi/4,(sector+1)*np.pi/4,5)
            triangles = []
            for a,b in zip(mus[:-1],mus[1:]):
                for c,d in zip(phis[:-1],phis[1:]):
                    v0,v1,v2,v3 = point(a,c),point(a,d),point(b,d),point(b,c)
                    for triangle in ([v0,v1,v2],[v0,v2,v3]):
                        if np.linalg.norm(np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0])) > 1e-12:
                            triangles.extend(triangle)
            center = point(MU_MIN+(1-MU_MIN)*(band+.5)/3,(sector+.5)*np.pi/4)
            normal = (center-[0,0,CAP_HEIGHT-SPHERE_RADIUS])/SPHERE_RADIUS
            result.append({'vertices':np.array(triangles),'normal':normal,'center':center,'area':2*np.pi*SPHERE_RADIUS*CAP_HEIGHT/24})
    return result


def model_xml(config, surface, attachments, hang=HANG, payload_mass=PAYLOAD_MASS, planar=False, radius=RADIUS, depth=CAP_HEIGHT, dome_mass=DOME_MASS):
    CAP_HEIGHT=depth;DOME_MASS=dome_mass;SPHERE_RADIUS=(radius**2+depth**2)/(2*depth);MU_MIN=1-depth/SPHERE_RADIUS
    assets,geoms,sites = [],[],[]
    for i,p in enumerate(surface):
        # Non-coplanar curved patch vertices produce a valid native visual mesh.
        values=' '.join(str(x) for x in p['vertices'].ravel())
        assets.append(f'<mesh name="patch{i}" vertex="{values}"/>')
        geoms.append(f'<geom type="mesh" mesh="patch{i}" rgba="0.3 0.7 0.6 1"/>')
        pos=' '.join(str(x) for x in p['center']);normal=' '.join(str(x) for x in p['normal'])
        sites.append(f'<site name="air{i}" pos="{pos}" zaxis="{normal}"/>')
    for i,p in enumerate(attachments):
        sites.append(f'<site name="tip{i}" pos="'+ ' '.join(str(x) for x in p)+'"/>')
    mean_mu2=(1+MU_MIN+MU_MIN**2)/3
    mean_x2=SPHERE_RADIUS**2*(1-mean_mu2)/2
    var_z=CAP_HEIGHT**2/12
    inertia_xy=DOME_MASS*(mean_x2+var_z)
    inertia_z=2*DOME_MASS*mean_x2
    cables=''.join(f'<spatial name="line{i}" width=".0006"><site site="tip{i}"/><site site="anchor"/></spatial>' for i in range(len(attachments)))
    payload_joints='<joint name="payload_x" type="slide" axis="1 0 0"/><joint name="payload_y" type="slide" axis="0 1 0"/>' if planar else '<freejoint name="payload_free"/>'
    return f'''<mujoco model="dome_b"><asset>{''.join(assets)}</asset>
      <option timestep="{config.dt}" integrator="implicitfast" gravity="0 0 -9.81"/>
      <default><geom contype="0" conaffinity="0"/><site size=".001"/></default>
      <worldbody><geom type="plane" size="5 5 .1"/>
        <body name="hub" pos="0 0 {config.height}"><freejoint/>
          <inertial pos="0 0 {CAP_HEIGHT/2}" mass="{DOME_MASS}" diaginertia="{inertia_xy} {inertia_xy} {inertia_z}"/>
          <geom type="sphere" size=".004"/>{''.join(geoms)}{''.join(sites)}
        {"" if planar else "</body>"}
          <body name="payload" pos="0 0 {0 if planar else config.height-hang}">
            {payload_joints}
            <geom type="box" size=".012 .01 .007" mass="{payload_mass}"/><site name="anchor"/>
          </body>{"</body>" if planar else ""}
      </worldbody><tendon>{cables}</tendon></mujoco>'''


class DomeSim(CloverSim):
    def __init__(self, config=None, target_xy=(0,0), line_length=None, payload_mass=PAYLOAD_MASS, planar=False, cable_count=3):
        self.c = config or Config()
        self.planar=bool(planar)
        if cable_count not in (3,4) or (not planar and cable_count!=3):raise ValueError("Unsupported cable configuration")
        self.cable_count=cable_count
        self.payload_mass=float(payload_mass)
        if not np.isfinite(self.payload_mass) or self.payload_mass<=0:
            raise ValueError("추의 질량은 양수여야 합니다.")
        self.line_length = float(line_length) if line_length is not None else float(np.hypot(RADIUS,HANG))
        if not np.isfinite(self.line_length) or not RADIUS <= self.line_length <= .5:
            raise ValueError("기본 줄 길이는 120 mm 이상이고 500 mm 이하여야 합니다.")
        self.hang=float(np.sqrt(self.line_length**2-RADIUS**2))
        if not np.isfinite(self.c.spool_speed) or self.c.spool_speed <= 0:
            raise ValueError("구동 속도는 양수여야 합니다.")
        if self.planar:self.hang=0.;self.line_length=RADIUS
        self.panels = patches()
        self.attachments = np.array([[RADIUS*np.cos(i*2*np.pi/cable_count),RADIUS*np.sin(i*2*np.pi/cable_count),0] for i in range(cable_count)])
        self.target_xy = np.asarray(target_xy,dtype=float)
        if self.target_xy.shape != (2,) or not np.all(np.isfinite(self.target_xy)):
            raise ValueError('목표 위치는 유한한 X/Y 값이어야 합니다.')
        self.validate_target(self.target_xy)
        self.target_payload = np.r_[self.target_xy,-self.hang]
        self.model = mujoco.MjModel.from_xml_string(model_xml(self.c,self.panels,self.attachments,self.hang,self.payload_mass,self.planar))
        self.data = mujoco.MjData(self.model)
        self.hub = self.model.body('hub').id
        self.payload = self.model.body('payload').id
        self.air_sites = [self.model.site(f'air{i}').id for i in range(24)]
        self.tips = [self.model.site(f'tip{i}').id for i in range(cable_count)]
        self.anchor = self.model.site('anchor').id
        self.payload_qpos=self.model.jnt_qposadr[self.model.joint('payload_x' if self.planar else 'payload_free').id]
        if self.planar:self.model.opt.integrator=mujoco.mjtIntegrator.mjINT_EULER
        self.winch_pull_limit=.08  # N per line: an assumed motor retraction limit.
        self.reset()

    def validate_target(self, xy):
        v=self.attachments[:,:2]
        edges=np.roll(v,-1,axis=0)-v;offset=xy-v
        if np.any(edges[:,0]*offset[:,1]-edges[:,1]*offset[:,0]<-1e-10):
            raise ValueError('목표 위치를 고정점 다각형 안에 지정해주세요.')

    def reset(self, tilt_deg=15, seed=0):
        mujoco.mj_resetData(self.model,self.data)
        self.wind=np.zeros(3)
        angle=np.random.default_rng(seed).uniform(-np.pi,np.pi)
        quat=np.r_[np.cos(np.deg2rad(tilt_deg)/2),np.array([np.cos(angle),np.sin(angle),0])*np.sin(np.deg2rad(tilt_deg)/2)]
        self.data.qpos[3:7]=quat
        rotation=np.empty(9);mujoco.mju_quat2Mat(rotation,quat)
        p=self.payload_qpos
        if not self.planar:
            self.data.qpos[p:p+3]=self.data.qpos[:3]+rotation.reshape(3,3)@np.array([0,0,-self.hang])
            self.data.qpos[p+3:p+7]=quat
        self.active_target_xy=self.target_xy.copy()
        self.spool=np.full(self.cable_count,self.line_length)  # Paid-out unstretched cable lengths, metres.
        self.target_lengths=self.lengths_for_target(self.active_target_xy)
        self.winch_rates=np.zeros(self.cable_count)  # Positive means reeling in.
        self.winch_stalled=np.zeros(self.cable_count,dtype=bool)
        self.tensions=np.zeros(self.cable_count)
        mujoco.mj_forward(self.model,self.data)
        return self.observe()

    def pd_action(self):
        # Compatibility name: B is target tracking, NOT the A attitude PD law.
        return self.target_xy/RADIUS

    def lengths_for_target(self, target):
        # Desired height only: no position or orientation constraint is imposed.
        point=np.r_[target,-self.hang]
        return np.linalg.norm(self.attachments-point,axis=1)

    def cable_state(self, rest_rates=None):
        rest_rates=-self.winch_rates if rest_rates is None else rest_rates
        delta=self.data.site_xpos[self.anchor]-self.data.site_xpos[self.tips]
        lengths=np.linalg.norm(delta,axis=1)
        directions=delta/np.maximum(lengths[:,None],1e-12)
        anchor_velocity=self.velocity(self.anchor)
        rates=np.array([np.dot(anchor_velocity-self.velocity(sid),direction)
                        for sid,direction in zip(self.tips,directions)])
        if self.planar:return dict(lengths=lengths,directions=directions,rates=rates,tension=np.zeros(self.cable_count),slack=np.zeros(self.cable_count,dtype=bool))
        extension=lengths-self.spool
        tension=np.where(extension>1e-10,np.maximum(0.,self.c.cable_stiffness*extension+
                         self.c.cable_damping*(rates-rest_rates)),0.)
        return dict(lengths=lengths,directions=directions,rates=rates,
                    tension=tension,slack=extension<=1e-10)

    def step(self, action, wind=(0,0,0)):
        if self.planar:return self.step_planar(action,wind)
        action=np.asarray(action,dtype=float)
        if action.shape != (2,) or not np.all(np.isfinite(action)):
            raise ValueError('B action must contain two finite numbers')
        target=action*RADIUS
        self.validate_target(target)
        self.active_target_xy=target.copy()
        self.target_lengths=self.lengths_for_target(target)
        cable=self.cable_state(np.zeros(3))
        change=np.clip(self.target_lengths-self.spool,-self.c.spool_speed*self.c.dt,
                       self.c.spool_speed*self.c.dt)
        # Restrict retraction if its spring + dashpot demand would exceed motor pull.
        # External dynamics may still create larger tension; we never clip cable forces.
        demand=self.c.cable_stiffness*(cable['lengths']-self.spool)+self.c.cable_damping*cable['rates']
        available=np.maximum(0.,(self.winch_pull_limit-demand)/
                             (self.c.cable_stiffness+self.c.cable_damping/self.c.dt))
        available=np.maximum(available,np.maximum(0.,self.spool-cable['lengths']))
        limited=np.where(change<0,np.maximum(change,-available),change)
        self.winch_stalled=limited>change+1e-12
        self.spool+=limited
        self.winch_rates=-limited/self.c.dt
        self.data.qfrc_applied[:]=0
        self.wind=np.asarray(wind,dtype=float)
        cable=self.cable_state()
        for sid,tension,direction in zip(self.tips,cable['tension'],cable['directions']):
            force=tension*direction
            self.force(sid,force)
            self.force(self.anchor,-force)
        aero=self.aerodynamics()
        mujoco.mj_applyFT(self.model,self.data,aero['force'][0],aero['torque_com'],
                          self.data.xipos[self.hub],self.hub,self.data.qfrc_applied)
        mujoco.mj_step(self.model,self.data);mujoco.mj_forward(self.model,self.data)
        self.tensions=self.cable_state()['tension']
        if not np.all(np.isfinite(self.data.qpos)):raise FloatingPointError('non-finite B state')
        return self.observe()

    def step_planar(self, action, wind):
        target=np.asarray(action,dtype=float)*RADIUS
        if target.shape!=(2,) or not np.all(np.isfinite(target)):raise ValueError('Invalid target')
        self.validate_target(target)
        self.active_target_xy=target.copy();self.target_lengths=self.lengths_for_target(target)
        p=self.data.qpos[self.payload_qpos:self.payload_qpos+2].copy()
        delta=target-p;distance=np.linalg.norm(delta)
        travel=0.
        if distance>1e-12:
            direction=delta/distance
            # Bound the largest absolute cable derivative over the entire step.
            # Along a straight segment a distance derivative is monotonic;
            # its absolute maximum is at an endpoint (including zero-length limits).
            def slope(q):
                offsets=q-self.attachments[:,:2];lengths=np.linalg.norm(offsets,axis=1)
                return np.max(np.where(lengths>1e-12,np.abs(offsets@direction)/np.maximum(lengths,1e-12),1.))
            initial=slope(p);lo=0.;hi=distance
            for _ in range(32):
                mid=(lo+hi)/2
                if mid*max(initial,slope(p+direction*mid))<=self.c.spool_speed*self.c.dt:lo=mid
                else:hi=mid
            travel=lo
            if distance*max(initial,slope(target))<=self.c.spool_speed*self.c.dt:travel=distance
            next_p=p+direction*travel
        else:next_p=target
        self.wind=np.asarray(wind,dtype=float)
        self.data.qfrc_applied[:]=0
        aero=self.aerodynamics()
        mujoco.mj_applyFT(self.model,self.data,aero['force'][0],aero['torque_com'],self.data.xipos[self.hub],self.hub,self.data.qfrc_applied)
        # Ideal planar drive: solve the coupled mass matrix for the slide forces.
        # This preserves reaction forces on the freely falling dome; no mass teleport.
        mass=np.empty((self.model.nv,self.model.nv));mujoco.mj_fullM(self.model,self.data,mass)
        acceleration=((next_p-p)/self.c.dt-self.data.qvel[6:8])/self.c.dt
        rhs=self.data.qfrc_applied+self.data.qfrc_passive-self.data.qfrc_bias
        base=np.linalg.solve(mass[:6,:6],rhs[:6]-mass[:6,6:]@acceleration)
        self.data.qfrc_applied[6:]=mass[6:,:6]@base+mass[6:,6:]@acceleration-self.data.qfrc_passive[6:]+self.data.qfrc_bias[6:]
        old=self.lengths_for_target(p)
        mujoco.mj_step(self.model,self.data);mujoco.mj_forward(self.model,self.data)
        actual=self.data.qpos[self.payload_qpos:self.payload_qpos+2]
        self.spool=self.lengths_for_target(actual)
        self.winch_rates=(old-self.spool)/self.c.dt
        self.tensions=np.zeros(self.cable_count);self.winch_stalled=np.zeros(self.cable_count,dtype=bool)
        return self.observe()

    def aerodynamics(self):
        rot=self.data.xmat[self.hub].reshape(3,3)
        velocity=np.zeros(6)
        mujoco.mj_objectVelocity(self.model,self.data,mujoco.mjtObj.mjOBJ_BODY,self.hub,velocity,0)
        relative=self.wind-velocity[3:]
        # CFD moment is about the rim centre. Shift to the dome's own COM only;
        # the freely suspended payload is coupled through the physical cable forces.
        local_com=self.model.body_ipos[self.hub]
        force,moment,alpha=loads(rot.T@relative,local_com,self.c.air_density,radius=getattr(self,"radius",.12))
        damping=damping_torque(rot.T@velocity[:3],self.c.air_density)*(getattr(self,"radius",.12)/.12)**4
        total=moment+damping
        origin=total+np.cross(local_com,force)
        return dict(force=np.array([rot@force]),position=np.array([self.data.xipos[self.hub].copy()]),
                    airflow=np.array([relative]),loading=np.zeros(24),
                    torque_com=rot@total,torque_origin=rot@origin,
                    torque_static_com=rot@moment,torque_damping=rot@damping,alpha=alpha)

    def landed(self):
        rot=self.data.xmat[self.hub].reshape(3,3)
        direction=rot[2,:]
        RADIUS=getattr(self,"radius",.12);CAP_HEIGHT=getattr(self,"depth",.06);SPHERE_RADIUS=(RADIUS**2+CAP_HEIGHT**2)/(2*CAP_HEIGHT);MU_MIN=1-CAP_HEIGHT/SPHERE_RADIUS
        rim=-RADIUS*np.linalg.norm(direction[:2])
        tip=CAP_HEIGHT*direction[2]
        candidate=(CAP_HEIGHT-SPHERE_RADIUS)*direction[2]-SPHERE_RADIUS if -direction[2]>=MU_MIN else np.inf
        dome_bottom=self.data.xpos[self.hub,2]+min(rim,tip,candidate)
        payload_geom=self.model.ngeom-1
        payload_rot=self.data.geom_xmat[payload_geom].reshape(3,3)
        payload_bottom=self.data.geom_xpos[payload_geom,2]-np.dot(np.abs(payload_rot[2]),self.model.geom_size[payload_geom])
        return bool(min(dome_bottom,payload_bottom)<=0)

    def system_com(self):
        return np.sum(self.model.body_mass[:,None]*self.data.xipos,axis=0)/self.model.body_mass.sum()

    def target_com_world(self):
        local=(DOME_MASS*np.array([0,0,CAP_HEIGHT/2])+self.payload_mass*np.r_[self.active_target_xy,-self.hang])/(DOME_MASS+self.payload_mass)
        return self.data.xpos[self.hub]+self.data.xmat[self.hub].reshape(3,3)@local
