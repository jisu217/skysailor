from pathlib import Path
import trimesh as tm,numpy as np,json,zipfile,xml.etree.ElementTree as E,re
src=Path(__file__).resolve().parent;out=src/'print-kit';out.mkdir(exist_ok=True)
parts=[];report=[]
for name,cx,cy in [('body',108,111),('rack',108,139),('cap',150,111),('worm',151,139)]:
 m=tm.load(src/(name+'.stl'),force='mesh')
 if name=='worm':m.apply_transform(tm.geometry.align_vectors([1,0,0],[0,0,1]))
 if name=='cap':m.apply_transform(tm.transformations.rotation_matrix(np.pi,[1,0,0]))
 m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
 assert m.is_watertight and m.is_volume and len(m.split())==1
 m.export(out/(name+'-print.stl'))
 m.apply_translation([cx,cy,0]);parts.append((name,m));report.append({'part':name,'bounds_mm':m.bounds.tolist(),'dimensions_mm':m.extents.tolist()})
for i,(_,a) in enumerate(parts):
 for _,b in parts[i+1:]:
  overlap=np.minimum(a.bounds[1,:2],b.bounds[1,:2])-np.maximum(a.bounds[0,:2],b.bounds[0,:2]);assert np.any(overlap<0)
allmesh=tm.util.concatenate([m for _,m in parts]);allmesh.export(out/'615-actuator-print-layout.stl')
ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';E.register_namespace('',ns)
def elem(tag,attrs={},parent=None):
 e=E.Element('{'+ns+'}'+tag,{k:str(v) for k,v in attrs.items()});
 if parent is not None:parent.append(e)
 return e
root=elem('model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'});res=elem('resources',parent=root);build=elem('build',parent=root)
for i,(name,m) in enumerate(parts,1):
 o=elem('object',{'id':i,'type':'model','name':name},res);mesh=elem('mesh',parent=o);vs=elem('vertices',parent=mesh);fs=elem('triangles',parent=mesh)
 for x,y,z in m.vertices:elem('vertex',{'x':f'{x:.6f}','y':f'{y:.6f}','z':f'{z:.6f}'},vs)
 for a,b,c in m.faces:elem('triangle',{'v1':a,'v2':b,'v3':c},fs)
 elem('item',{'objectid':i},build)
with zipfile.ZipFile(out/'615-actuator-print-layout.3mf','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',E.tostring(root,encoding='utf-8',xml_declaration=True))
(out/'PRINT-NOTES.txt').write_text('615 슬롯형 액추에이터 시험 출력\n\n615-actuator-print-layout.3mf: 단위 mm, 별도 오브젝트 4개, 위치와 방향 포함. Bambu Studio 프린터/재료/서포트 설정과 G-code는 포함하지 않은 범용 3MF입니다.\n동일 배치 STL과 방향을 맞춘 개별 STL도 포함합니다.\n\n배치: 몸체·랙은 평평한 바닥 아래, 덮개는 뒤집어 평평한 윗면 아래, 웜은 축 방향 수직. 모두 바닥 Z=0.\nA1 / PLA Basic 시험 시작값: 0.12mm 레이어, 벽 3줄. 기존 본인의 PLA Basic 프리셋을 사용하세요.\n웜: 작은 축 끝으로 서므로 브림과 하단 돌출부 서포트 필요. 나선 표면 서포트는 제거 흔적이 맞물림에 영향을 줄 수 있으니 슬라이스 미리보기에서 확인.\n몸체: 모터 받침과 가로 브리지 아래 처짐 여부를 확인하고 필요 시 서포트 추가. 가이드와 베어링 접촉면은 제거 후 다듬기.\n랙·덮개: 현재 방향으로 시작. 실제 서포트 필요 여부는 슬라이서에서 확인.\n\n아직 출력/동력 전달 검증 전 시험품입니다. 모터 축 Ø1.2, 모터 Ø6x15는 실측 확인. M1.6 나사 4개와 모터 고정 밴드 별도. 위치센서/감속기는 미포함.\n')
(out/'layout.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(src/'615-actuator-print-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,p.name)
# A review-only preview, preserving the original assembly viewer.
previewdir=src.parent/'615-slotted-worm-print-layout';previewdir.mkdir(exist_ok=True)
s=(src.parent/'central-xy-print-kit/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':allmesh.vertices.tolist(),'faces':allmesh.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for _,m in parts])+';counts',s)
s=re.sub(r'<h1>.*?</h1>','<h1>615 액추에이터 · 4부품 출력 배치</h1>',s);s=re.sub(r'<small>.*?</small>','<small>몸체·랙 바닥 아래 / 덮개 뒤집음 / 웜 수직 · mm · 웜 브림·서포트 확인 · 범용 3MF, 슬라이서 설정 미포함</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="../615-slotted-worm-actuator/print-kit/615-actuator-print-layout.3mf" download>배치 3MF</a><a href="../615-slotted-worm-actuator/615-actuator-print-kit.zip" download>전체 ZIP</a></nav>',s,flags=re.S)
s=s.replace('el=1.0,d=190','el=.8,d=170').replace('new T.Vector3(68,29,3)','new T.Vector3(120,125,3)').replace("target.set(3,0,4);d=95","target.set(120,125,3);d=170").replace('구동부 확대','전체 배치')
(previewdir/'preview.html').write_text(s)
print(json.dumps({'layout_extents_mm':allmesh.extents.tolist(),'parts':report,'3mf_bytes':(out/'615-actuator-print-layout.3mf').stat().st_size},indent=2))
# Round-trip validation with a separate reader.
scene=tm.load(out/'615-actuator-print-layout.3mf');assert len(scene.geometry)==4;assert np.allclose(scene.bounds,allmesh.bounds,atol=1e-4)
print('3MF round-trip: four objects, bounds and units consistent.')
