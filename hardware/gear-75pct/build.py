from pathlib import Path
import json, base64
import numpy as np
import trimesh

out = Path(__file__).resolve().parent
mesh = trimesh.load(out.parent / 'gear-test-v1/wheel-24t.stl')
mesh.apply_translation([-mesh.bounds[:, 0].mean(), -mesh.bounds[:, 1].mean(), -mesh.bounds[0, 2]])
inner = np.linalg.norm(mesh.vertices[:, :2], axis=1) < 1.81
mesh.vertices[:, :2] *= .75
mesh.vertices[:, 2] *= .5
mesh.vertices[inner, :2] /= .75
assert mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split()) == 1
assert np.allclose(mesh.extents, [15.823945, 15.823945, 2], atol=.001)
assert np.allclose(np.linalg.norm(mesh.vertices[inner, :2], axis=1), 1.8, atol=.00001)
mesh.export(out / 'wheel-24t-75pct-2mm.stl')
spec = dict(teeth=24, diameter_mm=float(mesh.extents[0]), thickness_mm=2, bore_mm=3.6,
            xy_scale=.75, z_scale=.5, compatible_with_original_worm=False,
            watertight=bool(mesh.is_watertight), volume_mm3=float(mesh.volume))
(out / 'dimensions.json').write_text(json.dumps(spec, indent=2))
preview = mesh.simplify_quadric_decimation(face_count=10000)
data = {key: base64.b64encode(np.asarray(val, dtype=dtype).tobytes()).decode()
        for key, val, dtype in [('v', preview.vertices, '<f4'), ('f', preview.faces, '<u4')]}
target = Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/gear-75pct.html')
target.write_text((out / 'viewer-template.html').read_text().replace('__DATA__', json.dumps(data)))
assert target.stat().st_size < 1000000
print(json.dumps(spec))
