"""Approximate aerodynamics; physical forces only, no artificial attitude torque."""
from dataclasses import dataclass
import argparse
import csv
import json
from pathlib import Path
import time

import mujoco
import numpy as np
from leaf import panels, SEGMENTS, LEAF_LENGTH


@dataclass
class Config:
    dt: float = 0.001
    height: float = 3.0
    air_density: float = 1.225
    drag_normal: float = 1.3
    drag_tangent: float = 0.08
    cable_stiffness: float = 30.0
    cable_damping: float = 0.025
    travel: float = 0.012
    spool_speed: float = 0.04
    kp: float = 0.018
    kd: float = 0.004


def model_xml(c):
    strips = panels()
    total_area = sum(p['area'] for p in strips)
    leaves, assets = [], []
    for j, panel in enumerate(strips):
        # Native viewer uses the same outline. Explicit body inertia keeps mesh
        # convexification out of the dynamics; aero uses exact polygon area.
        vertices = [(x,y,z) for z in (-.0003,.0003) for x,y in panel['polygon']]
        assets.append(f'<mesh name="panel{j}" vertex="'+ ' '.join(str(v) for p in vertices for v in p)+'"/>')
    for i in range(4):
        parts = []
        for j,p in enumerate(strips):
            x = 0 if j == 0 else strips[j-1]['length']
            mass = .0008*p['area']/total_area
            width = np.ptp(p['polygon'][:,1])
            ix = mass*(width**2+.0006**2)/12
            iy = mass*(p['length']**2+.0006**2)/12
            iz = ix+iy
            rotation = f'euler="0 0 {i*90}"' if j == 0 else ''
            parts.append(f'<body name="panel_{i}_{j}" pos="{x} 0 0" {rotation}>'
                         f'<joint name="bend_{i}_{j}" axis="0 1 0" stiffness="0.004" damping="0.00004" range="-20 40"/>'
                         f'<inertial pos="{p["center"][0]} {p["center"][1]} 0" mass="{mass}" diaginertia="{ix} {iy} {iz}"/>'
                         f'<geom type="mesh" mesh="panel{j}" rgba="0.18 0.65 0.4 1"/>'
                         f'<site name="air_{i}_{j}" pos="{p["center"][0]} {p["center"][1]} 0"/>')
        tip_x = LEAF_LENGTH-strips[-1]['root']
        parts.append(f'<site name="tip{i}" pos="{tip_x} 0 0"/>'+'</body>'*SEGMENTS)
        leaves.append(''.join(parts))
    cables = ''.join(f'<spatial name="line{i}" width="0.0005"><site site="tip{i}"/><site site="anchor"/></spatial>' for i in range(4))
    return f'''<mujoco model="clover"><compiler angle="degree"/>
      <asset>{''.join(assets)}</asset>
      <option timestep="{c.dt}" integrator="implicitfast" gravity="0 0 -9.81"/>
      <default><geom contype="0" conaffinity="0"/><site size="0.001" rgba="1 0.65 0.2 1"/></default>
      <worldbody><light pos="0 0 5"/>
        <geom type="plane" size="5 5 0.1" rgba="0.18 0.2 0.24 1"/>
        <body name="hub" pos="0 0 {c.height}"><freejoint/>
          <geom type="sphere" size="0.008" mass="0.001" rgba="0.9 0.9 0.9 1"/>
          {''.join(leaves)}
        </body>
        <body name="payload" pos="0 0 {c.height-0.085}"><freejoint/>
          <geom type="box" size="0.012 0.01 0.007" mass="0.004" rgba="0.95 0.55 0.15 1"/>
          <site name="anchor"/>
        </body>
      </worldbody><tendon>{cables}</tendon></mujoco>'''


class CloverSim:
    """action[0:2] are normalized differential spool positions, in [-1, 1]."""
    def __init__(self, config=None):
        self.c = config or Config()
        self.model = mujoco.MjModel.from_xml_string(model_xml(self.c))
        self.data = mujoco.MjData(self.model)
        self.hub = self.model.body('hub').id
        self.payload = self.model.body('payload').id
        self.panels = panels()
        self.air_sites = [self.model.site(f'air_{i}_{j}').id for i in range(4) for j in range(SEGMENTS)]
        self.wind = np.zeros(3)
        self.tips = [self.model.site(f'tip{i}').id for i in range(4)]
        self.anchor = self.model.site('anchor').id
        self.reset()

    def reset(self, tilt_deg=15, seed=0):
        mujoco.mj_resetData(self.model, self.data)
        self.wind = np.zeros(3)
        for i in range(4):
            for j in range(SEGMENTS):
                self.data.joint(f'bend_{i}_{j}').qpos[0] = np.deg2rad(6)
        mujoco.mj_forward(self.model, self.data)
        self.rest = np.array([np.linalg.norm(self.data.site_xpos[s]-self.data.site_xpos[self.anchor]) for s in self.tips])
        # Rotate the complete suspended assembly, preserving cable geometry.
        angle = np.random.default_rng(seed).uniform(-np.pi, np.pi)
        axis = np.array([np.cos(angle), np.sin(angle), 0.])
        quat = np.r_[np.cos(np.deg2rad(tilt_deg)/2), axis*np.sin(np.deg2rad(tilt_deg)/2)]
        rot = np.empty(9)
        mujoco.mju_quat2Mat(rot, quat)
        self.data.qpos[3:7] = quat
        adr = self.model.jnt_qposadr[self.model.body_jntadr[self.payload]]
        self.data.qpos[adr:adr+3] = np.array([0, 0, self.c.height])+rot.reshape(3,3)@np.array([0,0,-0.085])
        self.data.qpos[adr+3:adr+7] = quat
        self.spool = np.zeros(2)
        self.tensions = np.zeros(4)
        mujoco.mj_forward(self.model, self.data)
        return self.observe()

    def velocity(self, sid):
        jac = np.zeros((3, self.model.nv))
        mujoco.mj_jacSite(self.model, self.data, jac, None, sid)
        return jac @ self.data.qvel

    def force(self, sid, force):
        mujoco.mj_applyFT(self.model, self.data, force, np.zeros(3), self.data.site_xpos[sid], int(self.model.site_bodyid[sid]), self.data.qfrc_applied)

    def observe(self):
        rot = self.data.xmat[self.hub].reshape(3,3)
        vel = np.zeros(6)
        mujoco.mj_objectVelocity(self.model, self.data, mujoco.mjtObj.mjOBJ_BODY, self.hub, vel, 1)
        up = rot.T @ np.array([0,0,1.])
        return np.r_[up, vel[:3], self.spool/self.c.travel]

    def pd_action(self):
        obs = self.observe()
        # Positive x spool shortens +x cable; positive y shortens +y cable.
        return np.clip((self.c.kp*np.array([obs[0], obs[1]]) + self.c.kd*np.array([-obs[4], obs[3]]))/self.c.travel, -1, 1)

    def step(self, action, wind=(0,0,0)):
        action = np.asarray(action, dtype=float)
        if action.shape != (2,) or not np.all(np.isfinite(action)):
            raise ValueError('action must contain two finite numbers')
        target = np.clip(action, -1, 1)*self.c.travel
        self.spool += np.clip(target-self.spool, -self.c.spool_speed*self.c.dt, self.c.spool_speed*self.c.dt)
        lengths = self.rest + np.array([-self.spool[0], -self.spool[1], self.spool[0], self.spool[1]])
        self.data.qfrc_applied[:] = 0
        for i, sid in enumerate(self.tips):
            delta = self.data.site_xpos[self.anchor]-self.data.site_xpos[sid]
            length = np.linalg.norm(delta)
            direction = delta/max(length, 1e-9)
            rate = np.dot(self.velocity(self.anchor)-self.velocity(sid), direction)
            tension = max(0., self.c.cable_stiffness*(length-lengths[i])+self.c.cable_damping*rate) if length > lengths[i] else 0.
            self.tensions[i] = tension
            self.force(sid, tension*direction)
            self.force(self.anchor, -tension*direction)
        self.wind = np.asarray(wind, dtype=float)
        for sid, force in zip(self.air_sites, self.aerodynamics()['force']):
            self.force(sid, force)
        mujoco.mj_step(self.model, self.data)
        mujoco.mj_forward(self.model, self.data)
        if not np.all(np.isfinite(self.data.qpos)):
            raise FloatingPointError('non-finite simulation state')
        return self.observe()

    def aerodynamics(self):
        forces, airflow, loading = [], [], []
        for j, sid in enumerate(self.air_sites):
            normal = self.data.site_xmat[sid].reshape(3,3)[:,2]
            relative = self.velocity(sid)-self.wind
            vn = np.dot(relative, normal)
            tangent = relative-vn*normal
            area = self.panels[j % SEGMENTS]['area']
            normal_load = .5*self.c.air_density*self.c.drag_normal*vn*abs(vn)
            force = -area*(normal_load*normal + .5*self.c.air_density*self.c.drag_tangent*np.linalg.norm(tangent)*tangent)
            forces.append(force)
            airflow.append(-relative)
            loading.append(abs(normal_load))
        return {'force':np.array(forces), 'airflow':np.array(airflow), 'loading':np.array(loading)}

    def landed(self):
        return bool(np.min(self.data.geom_xpos[1:,2]) < 0.012)

    def record(self):
        obs = self.observe()
        return [self.data.time, self.data.xpos[self.hub,2], np.rad2deg(np.arccos(np.clip(obs[2],-1,1))), *self.spool, *self.tensions]


def run(mode='pd', seconds=5., seed=0, tilt=15., wind=(0,0,0), viewer=False):
    sim = CloverSim()
    sim.reset(tilt, seed)
    rows = [sim.record()]
    def advance():
        sim.step(sim.pd_action() if mode == 'pd' else np.zeros(2), wind)
        rows.append(sim.record())
    if viewer:
        import mujoco.viewer
        with mujoco.viewer.launch_passive(sim.model, sim.data) as view:
            view.cam.distance = 0.6
            view.cam.elevation = -15
            while view.is_running() and sim.data.time < seconds and not sim.landed():
                start = time.monotonic()
                for _ in range(16):
                    if sim.landed() or sim.data.time >= seconds:
                        break
                    advance()
                view.cam.lookat[:] = sim.data.xpos[sim.hub]
                view.sync()
                time.sleep(max(0., 0.016-(time.monotonic()-start)))
    else:
        while sim.data.time < seconds and not sim.landed():
            advance()
    return np.array(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['off','pd','compare'], default='compare')
    parser.add_argument('--viewer', action='store_true')
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--tilt', type=float, default=15)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--wind', nargs=3, type=float, default=[0,0,0])
    parser.add_argument('--out', type=Path, default=Path('outputs'))
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error('--seconds must be positive')
    if args.viewer and args.mode == 'compare':
        parser.error('--viewer requires --mode pd or --mode off')
    args.out.mkdir(parents=True, exist_ok=True)
    modes = ['off','pd'] if args.mode == 'compare' else [args.mode]
    results, summary = {}, {}
    for mode in modes:
        rows = run(mode, args.seconds, args.seed, args.tilt, args.wind, args.viewer)
        results[mode] = rows
        with (args.out/f'{mode}.csv').open('w') as f:
            writer = csv.writer(f)
            writer.writerow(['time_s','height_m','tilt_deg','spool_x_m','spool_y_m','tension_px_N','tension_py_N','tension_nx_N','tension_ny_N'])
            writer.writerows(rows)
        summary[mode] = {'duration_s':float(rows[-1,0]), 'rms_tilt_deg':float(np.sqrt(np.mean(rows[:,2]**2))), 'max_tilt_deg':float(rows[:,2].max()), 'final_height_m':float(rows[-1,1]), 'inverted':bool(np.any(rows[:,2]>90))}
    (args.out/'summary.json').write_text(json.dumps({'parameters':vars(args)|{'out':str(args.out)},'results':summary}, indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,1,figsize=(9,8),sharex=True)
    for mode, rows in results.items():
        for ax, col in zip(axes, [1,2,3]):
            ax.plot(rows[:,0],rows[:,col],label=mode)
    for ax, label in zip(axes,['Height (m)','Tilt (deg)','X spool (m)']):
        ax.set_ylabel(label)
        ax.grid(alpha=.25)
        ax.legend()
    axes[-1].set_xlabel('Time (s)')
    fig.suptitle('Clover descent — approximate aerodynamic model')
    fig.tight_layout()
    fig.savefig(args.out/'comparison.png',dpi=150)
    plt.close(fig)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
