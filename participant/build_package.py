"""Run after npm --prefix web run build. Explicit allowlist excludes credentials/logs."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1]
files=[root/p for p in ['pyproject.toml','uv.lock','clover.py','leaf.py','dome.py','rail.py','b_control.py','rail_strategy.py','hanging.py','rail_env.py','dashboard.py','training_dashboard.py','benchmark.py','manual_arena.py','agent_sandbox.py','cap_drop.py','data/wind/measured.json','web/src/cap/loads.json','web/src/cap/rotation_damping.json','experiments/train_rail.py']]
files+=list((root/'participant'/'direct-example').glob('*'))
files+=list((root/'participant'/'hanging-example').glob('*'))
files+=list((root/'sandbox').glob('*'))+list((root/'participant'/'python-example').glob('*'))
files+=list((root/'participant').glob('*.html'))
files+=list((root/'participant').glob('*.py'))+list((root/'participant').glob('*.txt'))+list((root/'web/dist').rglob('*'))
with zipfile.ZipFile(root/'participant-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:
  if p.is_file():z.write(p,str(p.relative_to(root)))
