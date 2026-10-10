"""Read-only training telemetry; incomplete files are tolerated during writes."""
import csv
import json
import math
import time
from pathlib import Path


def read_run(path):
    def read_json(name):
        try:
            value = json.loads((path / name).read_text())
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}
    status = read_json('status.json')
    episodes = []
    try:
        with (path / 'episodes.monitor.csv').open() as stream:
            for row in csv.DictReader(line for line in stream if not line.startswith('#')):
                try:
                    reward, length, elapsed = float(row['r']), int(row['l']), float(row['t'])
                    if not all(map(math.isfinite, (reward, elapsed))) or length < 0: continue
                    episodes.append(dict(reward=reward, duration=length * .02, elapsed=elapsed))
                except (ValueError, TypeError, KeyError):
                    continue
    except OSError:
        pass
    updated = status.get('updated_unix')
    stale = status.get('status') == 'training' and (not updated or time.time() - updated > 120)
    checkpoints = [p.name for p in sorted((path / 'checkpoints').glob('*.zip'))]
    return dict(id=path.name, status=status, stale=stale, config=read_json('config.json'),
                episodes=episodes, checkpoints=checkpoints, policy_saved=(path / 'policy.zip').is_file(),
                evaluation=read_json('evaluation.json'))


def list_runs(root):
    return [read_run(p) for p in sorted(root.glob('rl-*')) if p.is_dir() and not p.is_symlink()]
