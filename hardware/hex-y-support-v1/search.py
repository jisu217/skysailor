from pathlib import Path
import numpy as np,trimesh
src=Path('hardware/hex-compact-no-posts-v1/build.py')
ns={'__file__':str(src.resolve())};exec(src.read_text().split('R=15')[0],ns)
base=ns['base'];place=ns['place'];overlap=ns['overlap']
for r in [14,13,12,11,10]:
 units=[{k:place(v,i,r) for k,v in base.items()} for i in range(3)]
 collisions=[]
 for i,j in [(0,1),(0,2),(1,2)]:
  for ka in ['part','worm','motor']:
   for kb,b in units[j].items():
    v=overlap(units[i][ka],b)
    if v>1e-6:collisions.append((i,ka,j,kb,round(float(v),5)))
 print(r,collisions,flush=True)
 if collisions:break
