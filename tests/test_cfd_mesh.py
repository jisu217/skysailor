"""Check the custom CFD subdivision preserves volume and conformal faces."""
from collections import Counter
from pathlib import Path
import subprocess
import sys
import numpy as np


def test_tet_to_hex_conserves_volume_and_shared_faces(tmp_path):
    mesh = tmp_path/'mesh.msh'
    # Two tetrahedra sharing the z=0 triangle; no boundary at the shared face.
    points = ['0 0 0','1 0 0','0 1 0','0 0 1','0 0 -1']
    faces = [(1,2,4),(2,3,4),(3,1,4),(1,5,2),(2,5,3),(3,5,1)]
    elements = [f'{i+1} 2 2 1 1 '+ ' '.join(map(str,f)) for i,f in enumerate(faces)]
    elements += ['7 4 2 10 1 1 2 3 4','8 4 2 10 1 1 3 2 5']
    mesh.write_text('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n5\n'+ '\n'.join(f'{i+1} {p}' for i,p in enumerate(points))+'\n$EndNodes\n$Elements\n8\n'+'\n'.join(elements)+'\n$EndElements\n')
    subprocess.run([sys.executable,str(Path(__file__).parents[1]/'cfd/tets_to_hex.py'),str(mesh)],check=True,capture_output=True)
    lines=mesh.with_name('mesh-hex.msh').read_text().splitlines()
    a=lines.index('$Nodes');b=lines.index('$EndNodes');c=lines.index('$Elements');d=lines.index('$EndElements')
    xyz={int(row[0]):np.array(row[1:],float) for row in (line.split() for line in lines[a+2:b])}
    elems=[list(map(int,line.split())) for line in lines[c+2:d]]
    boundary={tuple(sorted(e[-4:])) for e in elems if e[1]==3}
    hexes=[e[-8:] for e in elems if e[1]==5]
    assert len(hexes)==8 and len(xyz)==23
    local_faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    uses=Counter();volumes=[]
    for h in hexes:
        volume=0
        for f in local_faces:
            ids=[h[j] for j in f];uses[tuple(sorted(ids))]+=1
            p,q,r,s=[xyz[i] for i in ids]
            volume+=(np.dot(p,np.cross(q,r))+np.dot(p,np.cross(r,s)))/6
        volumes.append(volume)
    assert min(volumes)>0
    assert np.isclose(sum(volumes),1/3)
    assert set(uses.values())=={1,2}
    assert {face for face,count in uses.items() if count==1}==boundary
