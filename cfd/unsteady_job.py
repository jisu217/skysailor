"""Bounded background CFD job with atomic dashboard snapshots and final plots."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import time
import tempfile
from datetime import datetime,timezone
from unsteady_stats import snapshot
from field_plots import render_fields


def publish(case, dest, state, started, code=None):
    data=snapshot(case)
    data.update(job_state=state,updated_at=datetime.now(timezone.utc).isoformat(),wall_elapsed_s=time.monotonic()-started,job_start_physical_s=JOB_START_TIME,exit_code=code)
    frames=[p for p in (case/'postProcessing/planes').glob('*') if p.is_dir() and list(p.glob('*.raw'))]
    if frames:data['latest_saved_field_s']=max(float(p.name) for p in frames)
    if (dest/'field.json').exists():data['displayed_field_s']=json.loads((dest/'field.json').read_text())['time_s']
    temp=dest/'live.tmp';temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(dest/'live.json')
    return data


def fields(case,dest):
    data=snapshot(case)
    frames=[]
    for folder in (case/'postProcessing/planes').glob('*'):
        if not folder.is_dir():continue
        try:physical_time=float(folder.name)
        except ValueError:continue
        if physical_time<data['physical_time_s'] or (data['solver_finished'] and physical_time<=data['physical_time_s']):
            raw=list(folder.glob('*.raw'))
            if any(p.name.startswith('p_') or p.name.endswith('_p.raw') for p in raw) and any(p.name.startswith('U_') or p.name.endswith('_U.raw') for p in raw):frames.append(folder)
    if not frames:return
    folder=max(frames,key=lambda p:float(p.name));field_time=float(folder.name)
    # Freeze a completed plane before plotting while the solver keeps writing.
    with tempfile.TemporaryDirectory(prefix='clover-field-') as tmp:
        temp=Path(tmp);shutil.copytree(folder,temp/'postProcessing/planes'/folder.name)
        render_fields(temp,data['metadata'],{'status':f'URANS / t = {field_time:g} s / unvalidated'})
        for name in ['pressure.png','velocity.png']:
            shutil.copy2(temp/name,dest/(name+'.tmp'));(dest/(name+'.tmp')).replace(dest/name)
    (dest/'field.tmp').write_text(json.dumps({'time_s':field_time})+'\n');(dest/'field.tmp').replace(dest/'field.json')



if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--duration',type=float,default=2.25);p.add_argument('--deadline',type=float);p.add_argument('--snapshot-only',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];case=(root/a.case).resolve();dest=root/'web/src/cfd/unsteady';dest.mkdir(exist_ok=True)
    lock=(case/'job.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=time.monotonic();JOB_START_TIME=snapshot(case)['physical_time_s']
    if a.snapshot_only:
        fields(case,dest);publish(case,dest,'pilot_complete',started);raise SystemExit(0)
    data=snapshot(case)
    if not data['solver_finished']:raise RuntimeError('Existing solver must finish before continuation')
    if a.duration<=data['physical_time_s']:raise ValueError('End time must exceed current time')
    control=case/'system/controlDict';s=control.read_text();s=re.sub(r'endTime\s+[^;]+;',f'endTime {a.duration};',s,count=1)
    s=re.sub(r'stopAt\s+[^;]+;', 'stopAt endTime;',s,count=1)
    # Keep disk usage bounded: 2 volume fields; 0.05 s plane snapshots.
    s=re.sub(r'writeInterval\s+[^;]+;','writeInterval 0.05;',s,count=1);control.write_text(s)
    meta=data['metadata'];meta['duration_s']=a.duration;meta['wall_deadline_unix']=a.deadline;meta['wall_budget_s']=3600 if a.deadline else None;meta['experiment_mode']='short_trial' if a.deadline else 'long_statistics';(case/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    (case/'job.pid').write_text(str(os.getpid())+'\n')
    container_name=f'skysailor-urans-{os.getpid()}'
    (case/'job-container.txt').write_text(container_name+'\n')
    command=['docker','compose','-f',str(root/'cfd/compose.yaml'),'run','--rm','--name',container_name,'solver',f'cd {shlex.quote("/case/"+case.name)} && pimpleFoam >> log.solver 2>&1']
    proc=subprocess.Popen(command,cwd=root)
    last_field=None;next_fields=0;budget_stop=False
    try:
        while proc.poll() is None:
            if a.deadline and time.time()>=a.deadline-60 and not budget_stop:
                text=control.read_text();control.write_text(re.sub(r'stopAt\s+[^;]+;', 'stopAt writeNow;',text,count=1));budget_stop=True
            if a.deadline and time.time()>=a.deadline-10:
                subprocess.run(['docker','stop','--time','2',container_name],check=False,timeout=5)
                proc.wait(timeout=3)
                break
            if (case/'STOP').exists():
                subprocess.run(['docker','stop',container_name],check=False)
                proc.wait(timeout=30)
                publish(case,dest,'stopped',started,proc.returncode)
                raise SystemExit(0)
            current=publish(case,dest,'running',started)
            field=current.get('latest_saved_field_s')
            # The solver's .raw output may be incomplete while writing; retry later.
            if field and field!=last_field and time.monotonic()>next_fields:
                try:fields(case,dest);last_field=field
                except (ValueError,OSError):pass
                next_fields=time.monotonic()+60
            time.sleep(10)
        if proc.returncode==0:
            fields(case,dest)
        state=('finished' if snapshot(case)['physical_time_s']>=a.duration-1e-8 else 'stopped') if proc.returncode==0 else 'failed'
        if budget_stop:state='budget_reached'
        final=publish(case,dest,state,started,proc.returncode)
        (case/'unsteady-result.json').write_text(json.dumps(final,indent=2)+'\n')
    except Exception as exc:
        # Stop only the container created by this job.
        if proc.poll() is None:
            subprocess.run(['docker','stop',container_name],check=False)
            proc.wait(timeout=30)
        try:publish(case,dest,'monitor_failed',started)
        finally:raise
