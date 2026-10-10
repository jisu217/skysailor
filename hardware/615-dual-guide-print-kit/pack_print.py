from pathlib import Path
import trimesh as tm,numpy as np,json,zipfile,xml.etree.ElementTree as E,re
src=Path(__file__).resolve().parent;out=src/'print-kit';out.mkdir(exist_ok=True)
parts=[];report=[]
for name,cx,cy in [('body',85,90),('cap',120,90),('worm',155,90),('nut-upper',85,135),('nut-lower',125,135)]:
 m=tm.load(src/(name+'.stl'),force='mesh')
 if True:m.apply_transform(tm.geometry.align_vectors([1,0,0],[0,0,1]))
 m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
 assert m.is_watertight and m.is_volume and len(m.split())==1
 m.export(out/(name+'-print.stl'))
 m.apply_translation([cx,cy,0]);parts.append((name,m));report.append({'part':name,'bounds_mm':m.bounds.tolist(),'dimensions_mm':m.extents.tolist()})
for i,(_,a) in enumerate(parts):
 for _,b in parts[i+1:]:
  overlap=np.minimum(a.bounds[1,:2],b.bounds[1,:2])-np.maximum(a.bounds[0,:2],b.bounds[0,:2]);assert np.any(overlap<0)
allmesh=tm.util.concatenate([m for _,m in parts]);allmesh.export(out/'615-dual-guide-print-layout.stl')
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
with zipfile.ZipFile(out/'615-dual-guide-print-layout.3mf','w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',E.tostring(root,encoding='utf-8',xml_declaration=True))

notes=(src/'ASSEMBLY.txt').read_text()
(out/'ASSEMBLY.txt').write_text(notes)
(out/'layout.json').write_text(json.dumps(report,indent=2))
scene=tm.load(out/'615-dual-guide-print-layout.3mf')
assert len(scene.geometry)==5 and np.allclose(scene.bounds,allmesh.bounds,atol=1e-4)
assert allmesh.bounds[0,0]>=0 and allmesh.bounds[1,0]<256 and allmesh.bounds[0,1]>=0 and allmesh.bounds[1,1]<256
with zipfile.ZipFile(src/'615-dual-guide-print-kit.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(out.iterdir()):z.write(p,p.name)
print(json.dumps({'footprint_mm':allmesh.extents.tolist(),'objects':5,'all_watertight':True,'round_trip_3mf':'passed','parts':report},indent=2))
