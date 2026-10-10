from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json,os
ROOT=Path(__file__).resolve().parent.parent
STATE=ROOT/'model-viewer/current.json'
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
 def do_GET(self):
  if self.path.split('?')[0]=='/api/state':
   data=json.loads(STATE.read_text());data['models']=[p.parent.name for p in sorted(ROOT.glob('*/preview.html'))]
   data['revisions']={n:(ROOT/n/'preview.html').stat().st_mtime_ns for n in data['models']}
   blob=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(blob);return
  super().do_GET()
 def log_message(self,*args):pass
if __name__=='__main__':
 print('Model viewer: http://127.0.0.1:8767/model-viewer/',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8767),Handler).serve_forever()
