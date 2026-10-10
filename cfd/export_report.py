"""Copy measured results to the dashboard's static report; no model calibration."""
import json,shutil
from pathlib import Path
from assess import assess
root=Path(__file__).resolve().parents[1];dest=root/'web/src/cfd';cases=[]
for name in ['coarse','fine','layered-v6','layered-refined','tilt-minus10','tilt-plus10']:
 case=root/'cfd/cases'/name
 if not (case/'result.json').exists():continue
 result=json.loads((case/'result.json').read_text());out=dest/name;out.mkdir(exist_ok=True)
 for filename in ['result.json','convergence.png','pressure.png','velocity.png']:
  shutil.copy2(case/filename,out/filename)
 label={'coarse':'기존 기본 격자','fine':'기존 세분 격자','layered-v6':'경계층 · 직립','layered-refined':'경계층 세분 · 직립','tilt-minus10':'경계층 · −10°','tilt-plus10':'경계층 · +10°'}[name]
 cases.append(dict(name=name,label=label,result=result))
comparison='계산 진행 중인 격자는 민감도 판정에서 제외합니다. 두 계산 완료 후 비교합니다.'
pair=[c for c in cases if c['name'] in ['layered-v6','layered-refined']]
if len(pair)<2:pair=[c for c in cases if c['name'] in ['coarse','fine']]
if len(pair)==2 and all(c['result']['solver_finished'] for c in pair):
 a,b=[c['result'] for c in pair];difference=abs(a['mean_cd_last_100']-b['mean_cd_last_100'])/abs(b['mean_cd_last_100'])
 comparison=f'{pair[0]["label"]} / {pair[1]["label"]} Cd 차이: {difference:.2%}. '+('두 계산의 수치 수렴 기준을 통과했습니다. 완전한 격자 독립성 증명은 아닙니다.' if all(c['result']['status']=='single_mesh_converged_not_validated' for c in pair) else '미수렴 계산이 포함되어 있어 격자 독립성을 판정할 수 없습니다.')
assessment=assess({c['name']:c['result'] for c in cases})
(dest/'assessment.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+'\n')
(dest/'report.json').write_text(json.dumps(dict(cases=cases,comparison_note=comparison,assessment=assessment,baseline=json.loads((root/'cfd/baseline.json').read_text())),ensure_ascii=False,indent=2)+'\n')
print(comparison)
