import mujoco
import numpy as np
import pytest
from clover import CloverSim, Config


def test_cables_cannot_accelerate_system_com_in_vacuum():
    sim = CloverSim(Config(air_density=0))
    sim.reset(0)
    masses = sim.model.body_mass
    before = np.sum(masses[:,None]*sim.data.xipos,axis=0)/masses.sum()
    for _ in range(200):
        sim.step([1,-1])
    after = np.sum(masses[:,None]*sim.data.xipos,axis=0)/masses.sum()
    t = sim.data.time
    assert np.linalg.norm((after-before)[:2]) < 1e-5
    assert after[2]-before[2] == pytest.approx(-.5*9.81*t*t,abs=.002)
    assert np.all(sim.tensions >= 0)


def test_spool_rate_limit_and_invalid_action():
    sim = CloverSim()
    sim.step([1,-1])
    assert sim.spool == pytest.approx([sim.c.dt*sim.c.spool_speed,-sim.c.dt*sim.c.spool_speed])
    with pytest.raises(ValueError):
        sim.step([float('nan'),0])


def test_repeatable_reset_and_disturbed_descent():
    sim = CloverSim()
    first = sim.reset(25,seed=4).copy()
    for _ in range(500):
        sim.step(sim.pd_action(),wind=[.3,-.2,0])
    assert np.all(np.isfinite(sim.data.qvel))
    assert np.max(np.abs(sim.spool)) <= sim.c.travel
    assert all(w.number == 0 for w in sim.data.warning)
    assert sim.reset(25,seed=4) == pytest.approx(first)


def test_segmented_leaf_area_and_mass():
    from leaf import panels, outline, polygon_properties
    strips = panels()
    assert len(strips) == 6
    assert sum(p['area'] for p in strips) == pytest.approx(polygon_properties(outline())[0])
    assert all(p['area'] > 0 for p in strips)
    sim = CloverSim()
    assert sim.model.body_mass.sum() == pytest.approx(.0082)
    assert len(sim.air_sites) == 24
    assert sim.model.opt.gravity == pytest.approx([0,0,-9.81])


def test_aero_opposes_relative_motion_and_vacuum_removes_it():
    sim = CloverSim()
    sim.data.qvel[2] = -2
    mujoco.mj_forward(sim.model, sim.data)
    aero = sim.aerodynamics()
    relative = -aero['airflow']
    assert np.all(np.sum(aero['force']*relative,axis=1) <= 1e-12)
    assert np.sum(aero['force'],axis=0)[2] > 0
    sim.c.air_density = 0
    assert np.all(sim.aerodynamics()['force'] == 0)
    assert np.all(sim.aerodynamics()['loading'] == 0)
    assert sim.model.opt.gravity[2] == -9.81
