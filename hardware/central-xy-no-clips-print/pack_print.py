from pathlib import Path
import trimesh as tm,numpy as np,json,zipfile,xml.etree.ElementTree as E
src=Path(__file__).resolve().parent;out=src/'print-kit';out.mkdir(exist_ok=True)
def pack(label,layout):
 parts=[];report=[]
 for idx,(name,cx,cy) in enumerate(layout):
  m=tm.load(src/(name+'.stl'),force='mesh')
  if name=='worm':m.apply_transform(tm.geometry.align_vectors([1,0,0],[0,0,1]))
  if name=='cap' or 'pivot-pin' in name:m.apply_transform(tm.transformations.rotation_matrix(np.pi,[1,0,0]))
  m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
  assert m.is_volume and len(m.split())==1,name
  m.export(out/(name+'-print.stl'));m.apply_translation([cx,cy,0]);parts.append((name+'-'+str(idx+1),m))
  report.append({'part':name,'bounds_mm':m.bounds.tolist(),'dimensions_mm':m.extents.tolist()})
 for i,(_,a) in enumerate(parts):
  for _,b in parts[i+1:]:
   overlap=np.minimum(a.bounds[1,:2],b.bounds[1,:2])-np.maximum(a.bounds[0,:2],b.bounds[0,:2]);assert np.any(overlap<0),(label,i)
 allmesh=tm.util.concatenate([m for _,m in parts]);allmesh.export(out/(label+'.stl'))
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
 with zipfile.ZipFile(out/(label+'.3mf'),'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
  z.writestr('3D/3dmodel.model',E.tostring(root,encoding='utf-8',xml_declaration=True))
 scene=tm.load(out/(label+'.3mf'));assert len(scene.geometry)==len(parts) and np.allclose(scene.bounds,allmesh.bounds,atol=1e-4)
 assert np.all(allmesh.bounds[0,:2]>=5) and np.all(allmesh.bounds[1,:2]<=251)
 (out/(label+'-layout.json')).write_text(json.dumps(report,indent=2))
 print(label,len(parts),'objects',allmesh.extents.tolist())
 return parts
layout=[]
for y in [70,120,170]:
 for name,x in [('body',55),('cap',119),('rack',178),('worm',221)]:layout.append((name,x,y))
a=pack('actuators-3x',layout)
b=pack('supports',[('fixed-base',92,105),('moving-top',203,68),('moving-bottom',203,115)]+[('front-pivot-pin',195+i*14,155) for i in range(3)]+[('rear-pivot-pin',195+i*14,173) for i in range(3)])
(out/'ASSEMBLY.txt').write_text((src/'ASSEMBLY.txt').read_text())
with zipfile.ZipFile(src/'central-xy-no-clips-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,p.name)
# Optional print-layout view in the same model viewer.
parts=a
h=(src.parent/'central-xy-print-kit/preview.html').read_text()
import re
mesh=tm.util.concatenate([m for _,m in parts]);start=h.index('const data=');end=h.index(';\nif(!window.THREE)',start)
h=h[:start]+'const data='+json.dumps({'vertices':mesh.vertices.tolist(),'faces':mesh.faces.tolist()},separators=(',',':'))+h[end:]
h=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for _,m in parts])+';counts',h)
h=re.sub(r'<h1>.*?</h1>','<h1>걸쇠 없는 액추에이터 × 3 · A1 출력 배치</h1>',h)
h=re.sub(r'<small>.*?</small>','<small>12부품 · 하부/랙 바닥 아래 · 덮개 뒤집음 · 웜 축 수직 · 웜 서포트 검토</small>',h)
h=re.sub(r'<nav>.*?</nav>','<nav><a href="print-kit/actuators-3x.3mf" download>액추에이터 3MF</a><a href="print-kit/supports.3mf" download>중앙 구조물 3MF</a></nav>',h,flags=re.S)
h=h.replace('el=1.0,d=190','el=.9,d=520').replace('new T.Vector3(68,29,3)','new T.Vector3(128,120,3)').replace('target.set(3,0,4);d=95','target.set(128,120,3);d=520')
(src/'print-preview.html').write_text(h)
