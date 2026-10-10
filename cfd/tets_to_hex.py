"""Conformal barycentric subdivision: each tetrahedron becomes four hexahedra.
Boundary triangles become three quads. Shared entity centres are deduplicated.
"""
import sys
from pathlib import Path
import numpy as np
p=Path(sys.argv[1]);lines=p.read_text().splitlines();a=lines.index('$Nodes');b=lines.index('$EndNodes');c=lines.index('$Elements');d=lines.index('$EndElements')
nodes={int(t[0]):np.array(t[1:],float) for t in (l.split() for l in lines[a+2:b])}
elements=[list(map(int,l.split())) for l in lines[c+2:d]];centres={}
def centre(*ids):
 key=tuple(sorted(ids))
 if key not in centres:
  n=len(nodes)+1;nodes[n]=np.mean([nodes[i] for i in ids],axis=0);centres[key]=n
 return centres[key]
out=[]
for t in elements:
 tags=t[3:3+t[2]];vs=t[3+t[2]:]
 if t[1]==2:
  for i in range(3):
   x,y,z=[vs[(i+j)%3] for j in range(3)]
   out.append([0,3,len(tags),*tags,x,centre(x,y),centre(x,y,z),centre(z,x)])
 elif t[1]==4:
  for i in range(4):
   x,y,z,w=[vs[(i+j)%4] for j in range(4)]
   if np.linalg.det(np.array([nodes[y]-nodes[x],nodes[z]-nodes[x],nodes[w]-nodes[x]]))<0:y,z=z,y
   v=[x,centre(x,y),centre(x,y,z),centre(x,z),centre(x,w),centre(x,y,w),centre(x,y,z,w),centre(x,z,w)]
   out.append([0,5,len(tags),*tags,*v])
 else:out.append(t)
new=lines[:a+1]+[str(len(nodes))]+[f'{i} '+ ' '.join(map(str,xyz)) for i,xyz in nodes.items()]+lines[b:c+1]+[str(len(out))]+[' '.join(map(str,[i,*t[1:]])) for i,t in enumerate(out,1)]+lines[d:]
p.with_name('mesh-hex.msh').write_text('\n'.join(new)+'\n');print('Hex mesh elements:',len(out))
