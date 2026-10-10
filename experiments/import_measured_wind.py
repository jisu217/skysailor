"""Extract 10-second sonic windows with gaps limited to 0.2s, without scaling or detrending."""
from pathlib import Path
import csv,json,hashlib,datetime
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'data/wind/raw/hopper_mike_combined.csv'
rows=list(csv.DictReader(source.open()))
t=np.array([datetime.datetime.fromisoformat(r['timestamp_utc']).timestamp() for r in rows])
v=np.array([[float(r['mike_'+a] or 'nan') for a in 'uvw'] for r in rows])
candidates=[]
for i in range(0,len(t)-100,10):
 j=int(np.searchsorted(t,t[i]+10-1e-5));tt=t[i:j+1];vv=v[i:j+1]
 if len(tt)>2 and abs(tt[-1]-tt[0]-10)<1e-4 and np.all(np.isfinite(vv)) and np.all((np.diff(tt)>0)&(np.diff(tt)<.20001)):
  candidates.append((i,float(np.linalg.norm(vv,axis=1).mean()),float(vv[:,2].mean())))
if not candidates:raise ValueError('No contiguous measured interval')
choices=[('gentle','이 자료 중 풍속이 가장 낮은 구간',min(candidates,key=lambda c:c[1])),('up','평균 상승 성분이 가장 큰 구간',max(candidates,key=lambda c:c[2])),('down','평균 하강 성분이 가장 큰 구간',min(candidates,key=lambda c:c[2]))]
clips={}
for key,label,(i,speed,w) in choices:
 j=int(np.searchsorted(t,t[i]+10-1e-5));vv=v[i:j+1];clips[key]=dict(label=label,start_utc=rows[i]['timestamp_utc'],time_s=np.round(t[i:j+1]-t[i],6).tolist(),velocity_m_s=vv.tolist(),max_sample_gap_s=float(np.diff(t[i:j+1]).max()),mean_speed=speed,mean_w=w,min_w=float(vv[:,2].min()),max_w=float(vv[:,2].max()))
meta_path=ROOT/'data/wind/source-metadata.json'
if not meta_path.exists():
 import urllib.request
 meta_path.write_bytes(urllib.request.urlopen('https://zenodo.org/api/records/18268508').read())
meta=json.loads(meta_path.read_text())
data=dict(source_url='https://doi.org/10.5281/zenodo.18268508',source_file=source.name,source_md5=hashlib.md5(source.read_bytes()).hexdigest(),license='CC-BY-4.0',authors=meta['metadata']['creators'],site='Falkenberg, Germany',sensor='METEK USA-1 (mike)',height_m=50,sample_hz=10,axes='X east, Y north, Z up',processing='Reference sonic mike_u/v/w only. Published filtered dataset; 10-second windows; reject gaps >0.2s; candidate starts every 10 rows; bridge <=0.2s gaps linearly; no amplitude scaling or mean removal. Linear interpolation at simulation times. Not representative of 0–3m winds; spatially uniform replay.',clips=clips)
expected=next(f['checksum'].split(':')[1] for f in meta['files'] if f['key']==source.name)
assert data['source_md5']==expected
(ROOT/'data/wind/measured.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(ROOT/'data/wind/source-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
for k,v in clips.items():print(k,{a:b for a,b in v.items() if a not in ('time_s','velocity_m_s')})
