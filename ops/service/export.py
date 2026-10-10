"""Run a scenario through the pipeline and write a replay file for the screen prototype.

python -m ops.service.export --out prototypes/data/replay.js [--spacing 250 --quality 0.95 --seed 0]

The file sets `window.OPS_REPLAY` so prototypes/c-uas-ops.html can load it from disk (file://)
without a server. Coordinates are ENU metres; the prototype shifts them into its own frame.
For a live picture use the local server instead: python -m ops.service.server
"""
import argparse
import json
from pathlib import Path

import numpy as np

from ops.service.session import Session, _xyz


def build(spacing=250.0, quality=0.95, seed=0):
    s = Session(spacing, quality, seed)
    frames = []
    while (f := s.step_sim()) is not None:
        frames.append(f)
    pts = [x['pos'][:2] for f in frames for x in f['truth']]
    pts += [n.pos[:2] for n in s.sc.nodes]+[list(z.center) for z in s.sc.reference.zones]
    lo, hi = np.min(pts, axis=0)-150, np.max(pts, axis=0)+150
    return dict(meta=s.meta(bounds=[*_xyz(lo), *_xyz(hi)]), frames=frames)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='prototypes/data/replay.js')
    ap.add_argument('--spacing', type=float, default=250.0)
    ap.add_argument('--quality', type=float, default=0.95)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args()
    data = build(a.spacing, a.quality, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('window.OPS_REPLAY = '+json.dumps(data, ensure_ascii=False, separators=(',', ':'))+';\n', encoding='utf-8')
    print(f'{out}: {len(data["frames"])} frames, {out.stat().st_size/1e3:.0f} kB')


if __name__ == '__main__':
    main()
