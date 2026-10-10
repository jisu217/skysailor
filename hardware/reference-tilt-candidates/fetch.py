from pathlib import Path
import urllib.request,json,zipfile,io,concurrent.futures
root=Path(__file__).resolve().parent
jobs=[]
for key,repo,branch in [('im','I-M-Robotics-Lab/Ball-Balancing-Robot','main'),('jake','schwertJake/Ball-On-Plate-Machine','master')]:
 t=json.load(urllib.request.urlopen(f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1'))
 for f in t['tree']:
  p=f['path']
  if p.lower().endswith(('.step','.stl')) or p in ['LICENSE.txt','LICENSE','README.md']:
   jobs.append((key,p,'https://raw.githubusercontent.com/'+repo+'/'+branch+'/'+urllib.parse.quote(p)))
jobs += [('aaed',p,'https://raw.githubusercontent.com/aaedmusa/Ball-Balancer-V2/main/'+urllib.parse.quote(p)) for p in ['STL Files.zip','CAD.zip','Bill of Materials.xlsx','3RPS Parallel Manipulator Inverse Kinematic Equations.pdf']]
def get(job):
 key,p,url=job;dst=root/key/'original'/p;dst.parent.mkdir(parents=True,exist_ok=True);d=urllib.request.urlopen(url,timeout=45).read();dst.write_bytes(d)
 if p=='STL Files.zip':
  z=zipfile.ZipFile(io.BytesIO(d))
  for n in z.namelist():
   if n.endswith('.stl'):(dst.parent/Path(n).name).write_bytes(z.read(n))
 return key,p,len(d)
for x in concurrent.futures.ThreadPoolExecutor(max_workers=6).map(get,jobs):print(x)
