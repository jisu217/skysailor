# Fast forced-pitch pilot

This experiment measures rotational load changes with actual moving-mesh CFD.
It does not add guessed angular damping to the drop viewer.

## Accepted configuration

- Rigid spherical cap: 240 mm diameter, 60 mm rise, assumed 1 mm wall.
- Incoming air: 1.6 m/s, initial angle 60 degrees to body +z.
- Rotation about body/world y through the rim centre: theta=A sin(2 pi 4 t).
- A=0 (fixed control), 5 degrees and 15 degrees; peak rates 0,126,377 deg/s.
- Two cycles (0.5 s); discard the first cycle, analyse the second.
- Same 52,832-cell mesh and same 200-iteration warm start for all cases.
- No prism inflation or fine axis refinement; 32 azimuthal sectors, 10 mm
  nominal surface resolution. Full checkMesh passes on the accepted mesh.
- OpenFOAM 1912 pimpleFoam, dynamicMotionSolverFvMesh + solidBody motion solver;
  actual whole-mesh rigid rotation and movingWallVelocity on the cap.
- First-order Euler time integration and upwind advection; one PISO outer
  pass, two pressure correctors, adaptive step with maxCo=3, maxDeltaT=.002 s.
  Initial timesteps used maxCo=.9 before the limit was increased for speed.
- Mesh motion at t=.0625 s was checked against the exact 5 degree rotation;
  maximum coordinate fit residual was below 1e-9 m.

The speed savings come from coarser spatial resolution, first-order schemes,
a larger Courant limit and only one measured cycle. First-order schemes can
introduce numerical damping, so measured dissipation is not yet a validated
physical angular damping coefficient. Near-wall and transition errors are
also unresolved. Rotating the finite outer domain introduces further domain
sensitivity; no independence study is claimed.

## Outputs and interpretation

Accepted cases: `cfd/cases/rotation-quick32/{a060,fixed,small,large}`.
Earlier mesh experiments and the aborted fine-grid transient are retained as
diagnostics; they are not used in the load fit.

`rotation_pilot.py report ROOT` subtracts the fixed control at matching
physical times and integrates delta_My * angular_rate over one complete cycle.
Negative work is damping-like; positive work is driving-like. It reports
C_rate = integral(delta_My*rate dt)/integral(rate^2 dt), and a local fit
of offset + stiffness*angle + C*rate. Acceleration and displacement are
collinear in a single-frequency sinusoid; the rate term also includes wake
phase lag. These are effective cycle coefficients, not separately identified
instantaneous damping, added inertia and wake-memory effects.

Uniform-time interpolation avoids weighting adaptive solver timesteps equally.
Global force vectors are transformed back into body coordinates; My is
unchanged by rotation about y. Forces and moments use rim-centre origin.

This pilot does not cover 0–180 degree attitudes, other speeds, spin about the
cap axis, arbitrary moving COM origins, or continuous tumbling. The viewer's
~820 deg/s default peak is outside this experiment's sampled peak rates.
No global correction is enabled in the drop model from this single-angle test.

## Commands

```sh
# Create and check a fresh mesh before any solve.
docker compose -f cfd/compose.yaml run --rm solver \
  '/usr/bin/python3 /scripts/quick_rotation_mesh.py --case /case/NEW/mesh --rise .06 --thickness .001 --surface-size .01 --sectors 32'
.venv/bin/python cfd/cap_sweep.py setup cfd/cases/NEW --angles 60 --iterations 200
# Run checkMesh -allGeometry -allTopology and require Mesh OK, then simpleFoam.
.venv/bin/python cfd/rotation_pilot.py setup cfd/cases/NEW/a060 cfd/cases/NEW/small --amplitude 5
# Likewise fixed (0 degrees), large (15 degrees); run pimpleFoam in each.
.venv/bin/python cfd/rotation_pilot.py report cfd/cases/NEW
.venv/bin/python cfd/plot_rotation_pilot.py cfd/cases/NEW
```

## Completed fast trial (2026-10-04)

All three transient runs finished at 0.5 s. Solver wall times: fixed 287 s,
small 318 s, large 320 s, run concurrently (mesh/setup attempts excluded).
At the second cycle the effective torque-rate coefficients were
-2.34516e-4 and -2.48856e-4 N m / (rad/s), respectively, differing by 6.1%.
Cycle work differences were -0.1410 mJ and -1.3467 mJ, both damping-like.
Local offset + displacement + rate fits had torque RMS residuals of
0.0246 and 0.2005 mN m. These differences do not replace a timestep check:
numerical damping and a not-yet-periodic wake remain possible contributors.
At 100 deg/s, the rate term alone corresponds to approximately -0.42 mN m
under these sampled conditions; displacement/acceleration contributions
are additional and must not be mistaken for pure rate damping.

Results: `rotation-summary.json`, `rotation.png`, raw fields and forces under
`cfd/cases/rotation-quick32`. The existing drop viewer is unchanged; these
coefficients are limited to this angle/speed/frequency/reference-point test.
