from pathlib import Path
import trimesh as tm,numpy as np,json,zipfile,xml.etree.ElementTree as E,re
src=Path(__file__).resolve().parent;out=src/'print-kit';out.mkdir(exist_ok=True)
parts=[];report=[]
for name,cx,cy in [('body',108,111),('rack',108,149),('cap',170,111),('worm',171,149)]:
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
(out/'PRINT-NOTES.txt').write_text('615 웜 지지축 유격 v2 시험품\n하부, 상부, 랙, 웜 총 4부품. 이번 수정은 웜만 재출력하면 됩니다. 기존 스냅 몸통과 랙은 유지. 웜 치형 Ø9x8/리드2.5 및 모터 구멍 Ø1.2 유지. 지지축 Ø3→2.8, 전체 길이13→15, 축방향 한쪽 틈0.1→0.3mm.\n조립: 하부 슬롯 안내핀과 웜 받침 기둥 위로 랙 슬롯을 내려 넣는다. 웜을 받침에 얹고 상부 몸통을 맞춤핀에 맞춰 덮는다. 상부를 수직으로 누르면 외부 탄성 걸쇠 네 곳이 걸린다. 분리할 때는 걸쇠를 바깥으로 조금씩 벌리고 상부를 들어 올린다. 모터는 뒤에서 상부 받침으로 넣어 웜 축에 연결한다. 모터 축 크기는 실측 확인. 모터 앞뒤 빠짐 방지는 시험 시 밴드 등을 추가한다.\n출력 방향: 하부와 랙 평평한 바닥 아래, 상부는 뒤집어서 윗면 아래, 웜은 축 수직. 웜 브림 및 하단 돌출부 서포트 필요. 상부 모터 받침/걸림턱는 슬라이스 미리보기에서 서포트 검토.\n범용 3MF에는 위치와 방향만 포함. Bambu Studio에서 A1/PLA Basic과 레이어·서포트 설정을 선택한다. 시작값 0.12mm 레이어, 벽3줄은 제안이며 검증된 프로필이 아니다.\n걸쇠·가이드·베어링 면은 출력 후 유격 조정 필요할 수 있다. 모터 Ø6x15, 축 Ø1.2는 임시 규격. PLA 걸쇠 반복 굽힘 시 파손 가능. 억지로 끼우지 말고 물림/유격 조정. 토크/마찰/내구성 미검증, 감속기/위치센서 미포함.\n')
(out/'layout.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(src/'615-actuator-print-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,p.name)
# A review-only preview, preserving the original assembly viewer.
previewdir=src.parent/'615-worm-clearance-v2-print-layout';previewdir.mkdir(exist_ok=True)
s=(src.parent/'central-xy-print-kit/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':allmesh.vertices.tolist(),'faces':allmesh.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for _,m in parts])+';counts',s)
s=re.sub(r'<h1>.*?</h1>','<h1>615 웜 지지축 유격 v2 · 출력 배치</h1>',s);s=re.sub(r'<small>.*?</small>','<small>하부·랙 바닥 아래 / 상부 뒤집음 / 웜 수직 · mm · 웜 브림·서포트 확인 · 범용 3MF, 슬라이서 설정 미포함</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="../615-worm-clearance-v2/print-kit/615-actuator-print-layout.3mf" download>배치 3MF</a><a href="../615-worm-clearance-v2/615-actuator-print-kit.zip" download>전체 ZIP</a></nav>',s,flags=re.S)
s=s.replace('el=1.0,d=190','el=.8,d=170').replace('new T.Vector3(68,29,3)','new T.Vector3(120,125,3)').replace("target.set(3,0,4);d=95","target.set(120,125,3);d=170").replace('구동부 확대','전체 배치')
(previewdir/'preview.html').write_text(s)
print(json.dumps({'layout_extents_mm':allmesh.extents.tolist(),'parts':report,'3mf_bytes':(out/'615-actuator-print-layout.3mf').stat().st_size},indent=2))
# Round-trip validation with a separate reader.
scene=tm.load(out/'615-actuator-print-layout.3mf');assert len(scene.geometry)==4;assert np.allclose(scene.bounds,allmesh.bounds,atol=1e-4)
print('3MF round-trip: four objects, bounds and units consistent.')
