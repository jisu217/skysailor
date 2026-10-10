# 24 cm × 6 cm spherical cap: mass-independent load experiment

The cap is fixed and rigid. The outer surface is a spherical cap of radius
150 mm, apex z=60 mm, rim radius 120 mm in the z=0 plane. Concentric inner
surface assumes 1 mm wall thickness. Ballast and supports are excluded.

Body origin O is the rim centre. +z points towards the apex. Incoming air
velocity is U*(-sin(alpha),0,cos(alpha)). Thus alpha=0 means air enters the
concavity; alpha=180 faces the convex exterior. This angle uses **incoming air**,
not the object's velocity through still air (which has the opposite sign).

Save all components of F and M_O in body axes. For any chosen COM position r_G,
M_G = M_O - cross(r_G,F). Mass is absent from this calculation. For other
azimuths rotate the force and torque vectors about body z first, then shift to
COM. Ballast mass, COM and inertia tensor are inputs to subsequent rigid-body
dynamics, not to this static CFD table.

`layer_mesh.py` now accepts --rise and --thickness (defaults remain 40 mm/1 mm).
`cap_sweep.py setup ROOT` clones ROOT/mesh/constant to fresh angle cases and
configures all external boundaries as freestream, including reverse inflow.
It refuses to overwrite existing angle cases. Default angles: 0,30,...,180;
speed: 1.6 m/s; 300 SIMPLE iterations. Use checkMesh -allGeometry -allTopology
and verify the literal `Mesh OK` before running simpleFoam.

`cap_sweep.py report ROOT` exports loads.json and loads.csv from the direct
OpenFOAM forces object's total force and moment columns, not coefficient-axis
conventions. The last 100 iteration mean, standard deviation and half-window
drift are diagnostic solver-iteration statistics, **not physical-time averages**.
All six components must stabilize and pressure/velocity/turbulence residuals
must pass before a case is marked single-mesh converged. No result in this pilot
is automatically enabled for dynamics: mesh, domain, velocity dependence and
unsteady wake validation remain necessary.

The cylinder extends radially 0.96 m and from z=-0.96 to 1.92 m. Its mesh has
preferential refinement above the cap; oblique/reverse-flow wake resolution
requires further independent assessment. RANS uses kOmegaSST with assumed 1%
inlet turbulence and 24 mm turbulence length. This is a pilot, not a verified
laminar/transition model at Re=25,600.

Outputs and raw fields live in cfd/cases/. Failed mesh attempts are retained
for diagnosis and never run through the flow solver.

To evaluate a chosen COM after the sweep (example only: 1 cm sideways,
5 cm below the rim), without rerunning CFD:

```sh
.venv/bin/python cfd/rebase_cap_loads.py cfd/cases/cap60-sweep-v3/loads.json \
  --com .01 0 -.05 --azimuth 0 --out outputs/cap60-example-com.csv
```

`--azimuth` rotates canonical incoming air and both load vectors about body +z.
COM stays in the original body axes. This uses axisymmetric geometry; it does
not imply that the offset ballast mass distribution is axisymmetric. Source
convergence status is retained in every output row.

## First completed pilot (2026-10-04, Asia/Seoul)

The accepted run is `cfd/cases/cap60-sweep-v3`: 140,400 cells, 40 azimuthal
sectors, 3 mm target surface mesh, 0.5 mm first boundary layer. All seven
cases pass full checkMesh. All solvers finish: 300 iterations per angle,
with 0 degrees extended to 1,000. **None passes the combined load-stability
and residual criteria.** The outputs are preliminary iteration summaries,
not a converged aerodynamic lookup table or physical-time averages.

| Incoming-air angle | Cd | My at rim centre (mN m) |
|---:|---:|---:|
| 0 | 1.4694 | 0.03134 |
| 30 | 1.5640 | -0.42222 |
| 60 | 0.9053 | -0.61435 |
| 90 | 0.1119 | 0.63106 |
| 120 | 0.3691 | 1.28920 |
| 150 | 0.7670 | 1.51633 |
| 180 | 0.9266 | 0.00433 |

Full vectors, residuals, load drift and y+ are in `loads.json` and each
`loads-summary.json`. `loads.csv` is the compact table; `loads.png` shows
all angles and their iteration histories. The example COM export under
`outputs/cap60-example-com.csv` uses (0.01,0,-0.05) m solely as a demonstration,
not a chosen design. No existing dashboard or drop model was calibrated.

Further work before dynamic use: extend steady iterations and assess the
remaining drift; use fixed-body transient CFD with physical-time averaging
where a steady solution does not settle; check mesh/domain and speed
sensitivity. Solver-iteration oscillations alone do not prove physical
vortex shedding.

## Saved cell-field viewer

`/flow.html` displays saved, nonconverged `U` and `p` at cell centres for
0,30,...,180 degrees. Source fields remain in each case's last saved iteration.
The 0-degree snapshot is iteration 1000, other angles are iteration 300.
These are NOT physical-time samples or the load table's iteration averages.

To regenerate viewer data, run OpenFOAM `postProcess -func writeCellCentres
-latestTime` on a060, then `.venv/bin/python cfd/export_cap_fields.py`.
The exporter verifies that all seven mesh fingerprints match and exports
little-endian float32 centres and Ux,Uy,Uz,p into `web/dist/cap/fields/`.
OpenFOAM kinematic pressure is multiplied by 1.225 kg/m³ to obtain gauge Pa.
All 140,400 cells are exported; display thinning selects actual cells without
interpolation. The nearby domain and slab filters control display only.

Gold particles use nearest-cell velocities from the full nearby mesh (KD tree),
with forward Euler advection of the frozen field and recycling at region exit,
mid-shell crossing or age expiry. This is illustrative flow motion, not a
transient CFD solution or accurate particle transport calculation. Colour is
reserved for velocity arrows; particles are gold. Magnitudes outside the
98th-percentile display range saturate; cell readouts retain original values.
