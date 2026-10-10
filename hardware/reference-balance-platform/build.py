from pathlib import Path
import trimesh,json,re
out=Path(__file__).resolve().parent
names=['central_pivot_3d','plate_universal_joint_mount_3d','plate_rod_end_mount_3d','servo_arm_3d'];meshes=[];report=[]
for i,n in enumerate(names):
 m=trimesh.load(out/'original'/(n+'.stl'),force='mesh')
 report.append({'part':n,'dimensions_mm':m.extents.tolist(),'watertight':bool(m.is_watertight)})
 m.apply_translation([-m.bounds.mean(axis=0)[0]+i*65,-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
 meshes.append(m)
assembly=trimesh.util.concatenate(meshes)
s=(out.parent/'central-xy-print-kit/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a);s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for m in meshes])+';counts',s)
s=re.sub(r'<h1>.*?</h1>','<h1>공개 모델 원본 부품 · Balance platform parts</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>분리 배치: 중앙 피벗 / 판의 유니버설 관절 마운트 / 봉 끝 마운트 / 서보 암 · 원본 크기 유지, 위치만 변경 · 완성 조립도가 아님 · Flavia Sofia Diaz Follegatti, 2026 · CC BY 4.0</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="https://data.mendeley.com/datasets/638z9y6dd9/1" target="_blank">원 출처·라이선스</a>'+''.join('<a href="original/'+n+'.stl" download>'+n+'</a>' for n in names)+'<a href="original/balancing_plate_laser_cut.dxf" download>판 도면 DXF</a></nav>',s,flags=re.S)
s=s.replace('el=1.0,d=190','el=.65,d=390').replace('new T.Vector3(68,29,3)','new T.Vector3(95,0,35)')
(out/'preview.html').write_text(s);(out/'inspection.json').write_text(json.dumps(report,indent=2))
(out/'ATTRIBUTION.txt').write_text('Balance platform parts\nAuthor: Flavia Sofia Diaz Follegatti (2026)\nDOI: 10.17632/638z9y6dd9.1\nSource: https://data.mendeley.com/datasets/638z9y6dd9/1\nLicense: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/\nOriginal files preserved unchanged in original/. Preview translates meshes for separated inspection only; no geometric scaling or edits.\nDownloaded archive contains 4 STL + 1 DXF; advertised editable Fusion file absent. No complete assembly or bill of materials supplied in this archive.\n')
(out.parent/'model-viewer/current.json').write_text(json.dumps({'model':out.name,'note':'공개 원본 4부품 분리 보기 · CC BY 4.0 · 완성 조립 모델 아님'},ensure_ascii=False))
print(report)
