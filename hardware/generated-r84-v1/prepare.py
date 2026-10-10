from pathlib import Path
import trimesh,numpy as np
p=Path(__file__).resolve().parent
s=1+.5/7.9119722843
code=(p.parent/'generated-gap2-v1/generate.py').read_text().replace('C=8.5;LEAD=1.875;TIP=7.9119722843;RINNER=6.5',f'C=9.0;SCALE={s};LEAD=1.875*SCALE;TIP=8.4119722843;RINNER=7.0')
code=code.replace('x+3-LEAD','x+3*SCALE-LEAD').replace('.8625-np.abs(phase)','.8625-np.abs(phase)/SCALE').replace('np.abs(x)-3)','np.abs(x)-3*SCALE)').replace('worm_length_mm=6','worm_length_mm=6*SCALE')
(p/'generate.py').write_text(code)
w=trimesh.load(p.parent/'generated-gap2-v1/worm-with-journal.stl');w.apply_scale([1,1,s]);w.export(p/'worm-with-journal.stl')
code=(p.parent/'generated-gap2-v1/audit.py').read_text().replace('from generate import grid,clearance','from generate import grid,clearance,SCALE').replace('[0,0,1,-3]','[0,0,1,-3*SCALE]').replace('[1,0,0,-8.5]','[1,0,0,-9]').replace('abs(x)<2.98','abs(x)<2.98*SCALE')
(p/'audit.py').write_text(code)
