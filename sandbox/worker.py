"""Trusted wire adapter INSIDE the untrusted Agent container. Host validates every reply."""
import contextlib
import importlib.util
import json
import sys

wire = sys.stdout
sys.path.insert(0, '/agent')
agent = None
for line in sys.stdin:
    request = json.loads(line)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if request['kind'] == 'reset':
                spec = importlib.util.spec_from_file_location('agent', '/agent/agent.py')
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                agent = module.Agent()
                agent.reset()
                result = None
            else:
                import numpy as np
                result = np.asarray(agent.act(np.asarray(request['observation'], dtype=np.float32))).tolist()
        reply = {'id': request['id'], 'action': result}
    except Exception as exc:
        reply = {'id': request['id'], 'error': (type(exc).__name__ + ': ' + str(exc))[:400]}
    wire.write(json.dumps(reply, allow_nan=False) + '\n')
    wire.flush()
