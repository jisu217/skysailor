"""Export saved OpenFOAM cell-centred U and p, without spatial interpolation.
Run writeCellCentres on a060 first. Other cases must have identical meshes.
Pressure p is kinematic gauge pressure; multiply by density for Pa.
"""
from pathlib import Path
import hashlib,json,re
import numpy as np
from cap_sweep import history
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'cfd/cases/cap60-sweep-v3'
out=ROOT/'web/dist/cap/fields'
out.mkdir(parents=True,exist_ok=True)
def field(path,width):
    text=path.read_text()
    match=re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\(',text)
    if not match:raise ValueError(f'Expected nonuniform ASCII field: {path}')
    count=int(match[1]);body=text[match.end():].split(';',1)[0]
    data=np.fromstring(body.replace('(',' ').replace(')',' '),sep=' ')
    assert data.size==count*width and np.isfinite(data).all(),path
    return data.reshape(count,width)
def fingerprint(case):
    return [hashlib.sha256((case/'constant/polyMesh'/name).read_bytes()).hexdigest() for name in ['points','faces','owner','neighbour']]
reference=source/'a060';mesh=fingerprint(reference)
centres=field(reference/'300/C',3)
centres.astype('<f4').tofile(out/'centres.bin')
manifest={'count':len(centres),'coordinates':'body axes, rim centre in metres','format':'little-endian float32','centres':'centres.bin','fields_layout':['Ux_m_s','Uy_m_s','Uz_m_s','gauge_pressure_Pa'],'source':'cfd/cases/cap60-sweep-v3','cases':[]}
# Boundary faces point out of the fluid and into the solid: force on solid = p * Sf.
poly=reference/'constant/polyMesh'
def mesh_body(name):
    return (poly/name).read_text().split('}',1)[1].strip().split('(',1)[1].rsplit(')',1)[0]
points=np.fromstring(mesh_body('points').replace('(',' ').replace(')',' '),sep=' ').reshape(-1,3)
faces=[list(map(int,m.split())) for m in re.findall(r'\d+\(([^)]+)\)',mesh_body('faces'))]
owner=np.fromstring(mesh_body('owner'),sep=' ',dtype=int)
boundary=(poly/'boundary').read_text()
patch=re.search(r'dome\s*\{([^}]+)',boundary)[1]
start=int(re.search(r'startFace\s+(\d+)',patch)[1]);count=int(re.search(r'nFaces\s+(\d+)',patch)[1])
face_centres=[];area_vectors=[]
for face in faces[start:start+count]:
    vertices=points[face];base=vertices.mean(axis=0)
    cross=np.cross(vertices-base,np.roll(vertices,-1,axis=0)-base)/2
    weights=np.linalg.norm(cross,axis=1)
    face_centres.append(np.average((vertices+np.roll(vertices,-1,axis=0)+base)/3,axis=0,weights=weights))
    area_vectors.append(cross.sum(axis=0))
face_centres=np.array(face_centres);area_vectors=np.array(area_vectors)
manifest['surface_count']=count
manifest['surface_layout']=['cx_m','cy_m','cz_m','fx_N','fy_N','fz_N','pressure_Pa','area_m2']
for case in sorted(source.glob('a[0-9]*')):
    assert fingerprint(case)==mesh,'Mesh mismatch; cell indices not shared'
    saved=max((p for p in case.iterdir() if p.is_dir() and p.name.isdigit() and (p/'U').exists()),key=lambda p:float(p.name))
    meta=json.loads((case/'metadata.json').read_text());u=field(saved/'U',3);p=field(saved/'p',1)*meta['air_density']
    assert len(u)==len(p)==len(centres)
    assert re.search(r'dome\s*\{\s*type\s+zeroGradient\s*;', (saved/'p').read_text()),'Surface pressure reconstruction requires zeroGradient'
    face_pressure=p[owner[start:start+count],0]
    face_forces=area_vectors*face_pressure[:,None]
    surface_file=case.name+'-surface.bin'
    np.column_stack([face_centres,face_forces,face_pressure,np.linalg.norm(area_vectors,axis=1)]).astype('<f4').tofile(out/surface_file)
    print(case.name,'pressure force sum',face_forces.sum(axis=0))
    values=np.column_stack([u,p]);file=case.name+'.bin';values.astype('<f4').tofile(out/file)
    # Check binary layout and pressure conversion through a round trip.
    np.testing.assert_allclose(np.fromfile(out/file,dtype='<f4').reshape(-1,4),values,rtol=1e-6,atol=1e-6)
    force_history=history(case,'force');moment_history=history(case,'moment')
    force=force_history[np.isclose(force_history[:,0],float(saved.name))][-1,1:4]
    moment=moment_history[np.isclose(moment_history[:,0],float(saved.name))][-1,1:4]
    manifest['cases'].append(dict(surface_file=surface_file,pressure_force_body_N=face_forces.sum(axis=0).tolist(),force_body_N=force.tolist(),torque_origin_body_Nm=moment.tolist(),angle=meta['angle_deg'],iteration=int(saved.name),speed=meta['speed_m_s'],density=meta['air_density'],file=file,converged=False,pressure_min=float(p.min()),pressure_max=float(p.max()),max_speed=float(np.linalg.norm(u,axis=1).max())))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(f'Exported {len(centres)} cells × {len(manifest["cases"])} cases to {out}')
