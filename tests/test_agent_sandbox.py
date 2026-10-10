import io
import zipfile
import pytest
from agent_sandbox import extract_archive,AgentError

def bundle(files):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        for n,b in files.items():z.writestr(n,b)
    return data.getvalue()

def test_valid_package(tmp_path):
    extract_archive(bundle({'agent.py':'class Agent: pass','requirements.txt':'numpy==2.5.3\n','weights/a.bin':b'abc'}),tmp_path/'agent')
    assert (tmp_path/'agent'/'weights/a.bin').read_bytes()==b'abc'

@pytest.mark.parametrize('files',[{'../escape.py':'x','agent.py':'x'},{'/agent.py':'x'},{'agent.py':'x','requirements.txt':'evil-package'},{'other.py':'x'}])
def test_reject_invalid(tmp_path,files):
    with pytest.raises(AgentError):extract_archive(bundle(files),tmp_path/'agent')

def test_reject_symlink(tmp_path):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        info=zipfile.ZipInfo('agent.py');info.external_attr=0o120777<<16;z.writestr(info,'/etc/passwd')
    with pytest.raises(AgentError):extract_archive(data.getvalue(),tmp_path/'agent')
