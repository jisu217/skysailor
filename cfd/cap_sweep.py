"""Mass-independent fixed spherical-cap loads. Run setup/report with Python + numpy.
Angles are between incoming air velocity and body +z (rim to apex).
All force and torque vectors are body coordinates, torque about rim centre.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import shutil
import numpy as np


def shift_to_com(force, torque, com):
    return np.asarray(torque) - np.cross(np.asarray(com), np.asarray(force))


def setup(root, angles, speed, iterations):
    if not math.isfinite(speed) or speed <= 0 or iterations < 200:
        raise ValueError('Require positive finite speed and at least 200 iterations')
    if not angles or any(not math.isfinite(x) or not 0 <= x <= 180 for x in angles) or len(set(angles)) != len(angles):
        raise ValueError('Require unique finite angles in [0,180]')
    mesh = root / 'mesh'
    meta = json.loads((mesh / 'mesh-metadata.json').read_text())
    for angle in angles:
        case = root / f'a{angle:03g}'
        if case.exists():
            raise FileExistsError(case)
        shutil.copytree(mesh / 'constant', case / 'constant')
        for folder in ['0', 'system']:
            shutil.copytree(Path(__file__).parent / 'templates' / folder, case / folder)
        shutil.copy2(Path(__file__).parent / 'templates/constant/transportProperties', case / 'constant/transportProperties')
        shutil.copy2(Path(__file__).parent / 'templates/constant/turbulenceProperties', case / 'constant/turbulenceProperties')
        theta = math.radians(angle)
        flow = np.array([-math.sin(theta), 0, math.cos(theta)])
        lift = np.array([math.cos(theta), 0, math.sin(theta)])
        vec = lambda v: '(' + ' '.join(f'{x:.12g}' for x in v) + ')'
        u = vec(speed * flow)
        k = 1.5 * (.01 * speed)**2
        omega = math.sqrt(k) / (.09**.25 * .024)
        specs = [('U', '[0 1 -1 0 0 0 0]', u, 'noSlip', True),
                 ('p', '[0 2 -2 0 0 0 0]', '0', 'zeroGradient', False),
                 ('k', '[0 2 -2 0 0 0 0]', str(k), 'kLowReWallFunction', False),
                 ('omega', '[0 0 -1 0 0 0 0]', str(omega), 'omegaWallFunction', False),
                 ('nut', '[0 2 -1 0 0 0 0]', '0', 'nutUSpaldingWallFunction', False)]
        for name, dims, value, wall, vector in specs:
            if name == 'U': bc = f'type freestream; freestreamValue uniform {value}; value uniform {value};'
            elif name == 'p': bc = 'type freestreamPressure; freestreamValue uniform 0; value uniform 0;'
            elif name == 'nut': bc = 'type calculated; value uniform 0;'
            else: bc = f'type inletOutlet; inletValue uniform {value}; value uniform {value};'
            body = '\n'.join(f'{patch} {{ {bc} }}' for patch in ['inlet', 'outlet', 'sides'])
            body += f'\ndome {{ type {wall}; value uniform {value}; }}'
            cls = 'volVectorField' if vector else 'volScalarField'
            (case / '0' / name).write_text(f'FoamFile {{version 2.0; format ascii; class {cls}; object {name};}}\ndimensions {dims};\ninternalField uniform {value};\nboundaryField {{\n{body}\n}}\n')
        area = math.pi * .12**2
        (case / 'system/controlDict').write_text(f'''FoamFile {{version 2.0; format ascii; class dictionary; object controlDict;}}
application simpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1;
writeControl timeStep; writeInterval {iterations}; purgeWrite 1;
writeFormat ascii; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 8; runTimeModifiable true;
functions {{
 loads {{ type forces; libs ("libforces.so"); patches (dome); rho rhoInf; rhoInf 1.225; CofR (0 0 0); writeControl timeStep; writeInterval 1; }}
 drag {{ type forceCoeffs; libs ("libforces.so"); patches (dome); rho rhoInf; rhoInf 1.225; CofR (0 0 0); dragDir {vec(flow)}; liftDir {vec(lift)}; pitchAxis (0 1 0); magUInf {speed}; lRef .24; Aref {area}; writeControl timeStep; writeInterval 1; }}
 yPlus {{ type yPlus; libs ("libfieldFunctionObjects.so"); writeControl writeTime; }}
}}
''')
        p = case / 'system/fvSolution'
        p.write_text(p.read_text().replace('SIMPLE {', 'SIMPLE { pRefCell 0; pRefValue 0;'))
        metadata = dict(meta, angle_deg=angle, speed_m_s=speed, air_density=1.225,
                        nu=1.5e-5, reynolds=speed*.24/1.5e-5, reference_area_m2=area,
                        moment_origin_m=[0,0,0], incoming_air_unit_body=flow.tolist(),
                        mass_kg=None, com_body_m=None, solver='simpleFoam steady RANS kOmegaSST',
                        iterations_requested=iterations,
                        limitations=['Assumed 1 mm wall', 'Coarse pilot mesh; no mesh/domain independence',
                        'No unsteady wake statistics', 'No ballast/support aerodynamics',
                        'Iteration averages are not physical time averages'])
        (case / 'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
        (case / 'case.foam').touch()


def history(case, name):
    records = {}
    for file in sorted(case.glob(f'postProcessing/loads/**/{name}.dat')):
        for line in file.read_text().splitlines():
            if not line.strip() or line.startswith('#'): continue
            vals = [float(x) for x in line.replace('(', ' ').replace(')', ' ').split()]
            # OpenFOAM forces emits time, total, pressure, viscous vectors.
            records[vals[0]] = vals[1:4]
    return np.array([[t, *records[t]] for t in sorted(records)])


def report(root):
    results=[]
    geometry=json.loads((root/'mesh/mesh-metadata.json').read_text()) if (root/'mesh/mesh-metadata.json').exists() else {}
    for case in sorted(root.glob('a*')):
        if not case.is_dir(): continue
        meta=json.loads((case/'metadata.json').read_text())
        f=history(case,'force'); m=history(case,'moment')
        if len(f)<100 or len(m)!=len(f): continue
        if not np.array_equal(f[:,0],m[:,0]): raise ValueError('Force/moment time mismatch')
        values=np.column_stack([f[:,1:],m[:,1:]])
        tail=values[-100:]; mean=tail.mean(axis=0)
        qA=.5*meta['air_density']*meta['speed_m_s']**2*meta['reference_area_m2']
        scales=np.array([qA]*3+[qA*.24]*3)
        std=tail.std(axis=0); drift=abs(tail[:50].mean(axis=0)-tail[50:].mean(axis=0))
        limits=np.maximum(.02*abs(mean),scales*np.array([.001]*3+[.0001]*3))
        stable=bool(len(f)>=200 and np.all(std<limits) and np.all(drift<limits))
        log=(case/'log.solver').read_text(); block=re.split(r'\nTime = ',log)[-1]; residuals={}
        for name,initial in re.findall(r'Solving for (\w+), Initial residual = ([\deE.+-]+)',block): residuals.setdefault(name,float(initial))
        residual_pass=all(residuals.get(name,1)<limit for name,limit in [('p',1e-3),('Ux',1e-4),('Uy',1e-4),('Uz',1e-4),('k',1e-3),('omega',1e-3)])
        mesh_pass='Mesh OK' in (case/'log.checkMesh').read_text()
        finished=bool(log.rstrip().endswith('End') and f[-1,0]>=meta['iterations_requested'])
        yplus=None
        yfiles=sorted(case.glob('postProcessing/yPlus/**/yPlus.dat'))
        if yfiles:
            rows=[line.split() for file in yfiles for line in file.read_text().splitlines() if line.strip() and not line.startswith('#')]
            if rows:
                row=max(rows,key=lambda v:float(v[0]));yplus=dict(iteration=float(row[0]),patch=row[1],minimum=float(row[2]),maximum=float(row[3]),average=float(row[4]))
        ok=finished and mesh_pass and stable and residual_pass
        theta=math.radians(meta['angle_deg'])
        result=dict(angle_deg=meta['angle_deg'],speed_m_s=meta['speed_m_s'],iterations=len(f),
            force_body_N=mean[:3].tolist(),torque_origin_body_Nm=mean[3:].tolist(),
            force_coeff_body=(mean[:3]/qA).tolist(),moment_coeff_body=(mean[3:]/(qA*.24)).tolist(),
            cd=float(np.dot(mean[:3],meta['incoming_air_unit_body'])/qA),
            cl=float(np.dot(mean[:3],[math.cos(theta),0,math.sin(theta)])/qA),
            last_100_std=std.tolist(),last_100_half_drift=drift.tolist(),
            mesh_pass=mesh_pass,loads_stable=stable,residual_pass=residual_pass,
            residuals=residuals,solver_finished=finished,y_plus=yplus,
            status='single_mesh_converged_not_validated' if ok else 'preliminary_not_converged',
            usable_for_dynamics=False)
        (case/'loads-summary.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
    (root/'loads.json').write_text(json.dumps(dict(reference='body axes; rim centre origin; incoming air angle to +z',
        geometry={k:geometry.get(k) for k in ['diameter_m','rise_m','shell_thickness_m']},
        warning='Pilot steady RANS; no physical-time averaging or mesh independence; do not use as validated lookup table.',
        results=results),indent=2)+'\n')
    with (root/'loads.csv').open('w') as out:
        writer=csv.writer(out);writer.writerow(['angle_deg','speed_m_s','Fx_N','Fy_N','Fz_N','Mx_Nm','My_Nm','Mz_Nm','Cd','Cl','status'])
        for r in results:writer.writerow([r['angle_deg'],r['speed_m_s'],*r['force_body_N'],*r['torque_origin_body_Nm'],r['cd'],r['cl'],r['status']])
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['setup','report']);p.add_argument('root',type=Path)
    p.add_argument('--angles',type=float,nargs='+',default=[0,30,60,90,120,150,180]);p.add_argument('--speed',type=float,default=1.6);p.add_argument('--iterations',type=int,default=300)
    a=p.parse_args()
    if a.action=='setup':setup(a.root,a.angles,a.speed,a.iterations)
    else:report(a.root)
