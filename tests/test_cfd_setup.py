import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_tilted_setup_rotates_flow_and_force_axes(tmp_path):
    (tmp_path / 'mesh-metadata.json').write_text(json.dumps({'cells': 1}))
    subprocess.run([sys.executable, str(ROOT / 'cfd/setup_layered.py'), str(tmp_path), '--tilt', '10', '--iterations', '1234'], check=True)
    control = (tmp_path / 'system/controlDict').read_text()
    assert re.search(r'endTime\s+1234;', control)
    drag = list(map(float, re.search(r'dragDir\s*\(([^)]+)\)', control)[1].split()))
    lift = list(map(float, re.search(r'liftDir\s*\(([^)]+)\)', control)[1].split()))
    assert drag[0] < -.17 and drag[2] > .98
    assert lift[0] > .98 and lift[2] > .17
    velocity = (tmp_path / '0/U').read_text()
    assert '(-0.277837084267 0 1.57569240482)' in velocity
    assert 'sides {type inletOutlet;' in velocity
