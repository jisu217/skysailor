"""Create a physical-time URANS case on an existing, checked mesh."""
import argparse
import json
from pathlib import Path
import re
import shutil


def create(source, target, duration=.03, max_co=.7, max_dt=.001):
    source, target = Path(source), Path(target)
    if target.exists():
        raise ValueError('Use a new case directory')
    if 'Mesh OK' not in (source/'log.checkMesh').read_text():
        raise ValueError('Source mesh did not pass all checks')
    if not (source/'log.solver').read_text().rstrip().endswith('End'):
        raise ValueError('Wait for source solver to finish')
    if min(duration,max_co,max_dt)<=0:
        raise ValueError('Duration, Courant limit and time step must be positive')
    times=[p for p in source.iterdir() if p.is_dir() and re.fullmatch(r'\d+(\.\d+)?',p.name) and float(p.name)>0]
    latest=max(times,key=lambda p:float(p.name))
    for folder in ['constant','system']:
        shutil.copytree(source/folder,target/folder)
    (target/'0').mkdir()
    for field in ['U','p','k','omega','nut']:
        shutil.copy2(latest/field,target/'0'/field)
    shutil.copy2(source/'log.checkMesh',target/'log.checkMesh')
    p=target/'system/fvSchemes'
    s=p.read_text().replace('default steadyState','default backward').replace('bounded Gauss','Gauss')
    p.write_text(s)
    (target/'system/fvSolution').write_text('''FoamFile { version 2.0; format ascii; class dictionary; object fvSolution; }
solvers {
 p { solver GAMG; tolerance 1e-7; relTol 0.02; smoother GaussSeidel; }
 pFinal { $p; relTol 0; }
 "(U|k|omega)" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.01; }
 "(U|k|omega)Final" { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0; }
}
PIMPLE { momentumPredictor yes; nOuterCorrectors 2; nCorrectors 2; nNonOrthogonalCorrectors 1; }
''')
    p=target/'system/controlDict';s=p.read_text()
    replacements={'application':'pimpleFoam','endTime':str(duration),'deltaT':'0.00005','purgeWrite':'2','timePrecision':'10'}
    for key,value in replacements.items():s=re.sub(r'\b'+key+r'\s+[^;]+;',key+' '+value+';',s,count=1)
    s=re.sub(r'writeControl\s+timeStep;', 'writeControl adjustableRunTime;',s,count=1)
    s=re.sub(r'writeInterval\s+[^;]+;', 'writeInterval 0.01;',s,count=1)
    s+=f'\nadjustTimeStep yes;\nmaxCo {max_co};\nmaxDeltaT {max_dt};\n'
    p.write_text(s)
    metadata=json.loads((source/'metadata.json').read_text())
    metadata.pop('linear_solver_refinement',None)
    metadata.update(solver='pimpleFoam / transient incompressible URANS kOmegaSST',time_mode='physical',duration_s=duration,max_co=max_co,max_delta_t_s=max_dt,time_scheme='backward',initial_solution={'case':source.name,'iteration':float(latest.name)},limitations=['Fixed dome only; payload and cables excluded','URANS models turbulence; this is not DNS or LES','Warm-start transient must be discarded before statistics','Time-step, grid and domain independence remain unverified'])
    (target/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (target/'case.foam').touch()
    print('URANS ready',target,'end time',duration,'s')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('target');p.add_argument('--duration',type=float,default=.03);p.add_argument('--max-co',type=float,default=.7);p.add_argument('--max-dt',type=float,default=.001);a=p.parse_args()
    create(a.source,a.target,a.duration,a.max_co,a.max_dt)
