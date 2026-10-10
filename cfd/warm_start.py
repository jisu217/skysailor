"""Reuse a finished solution on the identical mesh, keeping new boundary conditions."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('target');a=p.parse_args()
source,target=Path(a.source),Path(a.target)
if (target/'postProcessing').exists():raise RuntimeError('Target already has results')
if not (source/'log.solver').read_text().rstrip().endswith('End'):raise RuntimeError('Source is still running')
for name in ['points','faces','owner','neighbour','boundary']:
    digest=lambda root:hashlib.sha256((root/'constant/polyMesh'/name).read_bytes()).digest()
    if digest(source)!=digest(target):raise RuntimeError('Warm start requires identical meshes')
times=[p for p in source.iterdir() if p.is_dir() and p.name.replace('.','',1).isdigit() and float(p.name)>0]
latest=max(times,key=lambda p:float(p.name))
prepared={}
for field in ['U','p','k','omega','nut']:
    old=(latest/field).read_text();new=(target/'0'/field).read_text()
    prepared[field]=old[:old.index('boundaryField')]+new[new.index('boundaryField'):]
for field,text in prepared.items():(target/'0'/field).write_text(text)
metadata=json.loads((target/'metadata.json').read_text())
metadata['initial_solution']=dict(case=source.name,iteration=float(latest.name),note='Internal fields reused; target boundary conditions retained')
(target/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('Warm start:',source.name,latest.name,'->',target.name)
