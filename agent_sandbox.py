"""ZIP validation and Docker IPC. No submitted code is imported in the web process."""
import io
import json
import math
import os
import selectors
import shutil
import stat
import subprocess
import time
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

IMAGE='skysailor-agent:v1'
MAX_ARCHIVE=20*1024*1024
MAX_EXPANDED=100*1024*1024

class AgentError(Exception): pass

def available():
    if not shutil.which('docker'):return False
    try:
        p=subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=4)
        return p.returncode==0
    except (OSError,subprocess.TimeoutExpired):return False

def extract_archive(data, destination):
    if len(data)>MAX_ARCHIVE:raise AgentError('ZIP은 20MB 이하여야 합니다.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries=archive.infolist()
            if len(entries)>256 or sum(i.file_size for i in entries)>MAX_EXPANDED:raise AgentError('압축 해제 크기 100MB / 파일 256개 제한을 초과했습니다.')
            seen=set()
            for item in entries:
                p=PurePosixPath(item.filename)
                mode=item.external_attr>>16
                if p.is_absolute() or '..' in p.parts or '\\' in item.filename or '\x00' in item.filename or not p.parts or str(p) in seen:raise AgentError('허용되지 않는 ZIP 경로입니다.')
                if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR):raise AgentError('링크 및 특수 파일은 허용되지 않습니다.')
                if item.flag_bits&1:raise AgentError('암호화된 ZIP은 지원하지 않습니다.')
                seen.add(str(p))
            if 'agent.py' not in seen:raise AgentError('ZIP 최상위에 agent.py가 필요합니다.')
            if 'requirements.txt' in seen:
                req=archive.read('requirements.txt').decode('utf-8')
                allowed={'numpy','numpy==2.5.3','torch','torch==2.8.0'}
                if any(l.strip() and not l.lstrip().startswith('#') and l.strip() not in allowed for l in req.splitlines()):raise AgentError('공통 환경은 numpy 2.5.3, torch 2.8.0만 지원합니다. 추가 설치는 허용하지 않습니다.')
            destination.mkdir(parents=True,exist_ok=False)
            for item in entries:
                target=destination/item.filename
                if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item) as source,target.open('wb') as dest:shutil.copyfileobj(source,dest)
                target.chmod(0o444)
            for d in [destination,*destination.rglob('*')]:
                if d.is_dir():d.chmod(0o755)
    except AgentError:raise
    except (zipfile.BadZipFile,OSError,UnicodeError,RuntimeError,ValueError) as exc:raise AgentError('ZIP을 읽을 수 없습니다.') from exc

class DockerAgent:
    def __init__(self,path,action_size=2):
        self.action_size=action_size
        self.name='skysailor-agent-'+uuid4().hex
        self.proc=None;self.sequence=0;self.buffer=b'';self.selector=selectors.DefaultSelector()
        self.deadline=time.monotonic()+60
        command=['docker','run','--rm','-i','--name',self.name,'--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','1g',
            '--memory-swap','1g','--cpus','1','--ulimit','nofile=128:128','--ulimit','core=0:0',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--mount',f'type=bind,src={path.resolve()},dst=/agent,readonly',IMAGE]
        try:
            self.proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
            self.selector.register(self.proc.stdout,selectors.EVENT_READ)
            self.request({'kind':'reset'},20)
        except Exception:
            self.close();raise
    def request(self,message,timeout):
        self.sequence+=1;message['id']=self.sequence
        try:self.proc.stdin.write((json.dumps(message)+'\n').encode())
        except (BrokenPipeError,OSError) as exc:raise AgentError('Agent 프로세스가 종료되었습니다.') from exc
        end=min(self.deadline,time.monotonic()+timeout)
        while b'\n' not in self.buffer:
            remaining=end-time.monotonic()
            if remaining<=0 or not self.selector.select(remaining):raise AgentError('Agent 시간 제한 초과: 초기화 20초 / 행동 0.25초 / 비행 60초.')
            chunk=os.read(self.proc.stdout.fileno(),8192)
            if not chunk:raise AgentError('Agent가 응답 없이 종료됐습니다.')
            self.buffer+=chunk
            if len(self.buffer)>16384:raise AgentError('Agent 응답 크기 제한을 초과했습니다.')
        line,self.buffer=self.buffer.split(b'\n',1)
        try:reply=json.loads(line)
        except (ValueError,UnicodeError) as exc:raise AgentError('Agent 응답 형식 오류') from exc
        if not isinstance(reply,dict) or reply.get('id')!=self.sequence:raise AgentError('Agent 응답 순서 오류')
        if reply.get('error'):raise AgentError(str(reply['error'])[:400])
        return reply.get('action')
    def act(self,observation):
        action=self.request({'kind':'act','observation':observation.tolist()},.25)
        if not isinstance(action,list) or len(action)!=self.action_size or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1 for v in action):raise AgentError(f'act()는 [-1,1] 범위의 유한한 {self.action_size}개 수를 반환해야 합니다.')
        return action
    def close(self):
        try:subprocess.run(['docker','rm','-f',self.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        except (OSError,subprocess.TimeoutExpired):pass
        if self.proc:
            try:self.proc.kill();self.proc.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):pass
            for stream in (self.proc.stdin,self.proc.stdout):
                if stream:stream.close()
        self.selector.close()
