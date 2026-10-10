from pathlib import Path
import json,trimesh
import os
if not os.environ.get("STL_ONLY"):
 from OCP.STEPControl import STEPControl_Reader
 from OCP.BRepMesh import BRepMesh_IncrementalMesh
 from OCP.StlAPI import StlAPI_Writer
r=Path(__file__).resolve().parent
for key in (['aaed','jake'] if os.environ.get('STL_ONLY') else ['im','aaed','jake']):
 parts=[]
 for p in sorted((r/key/'original').rglob('*')):
  if p.suffix.lower() not in ['.step','.stl']:continue
  if p.suffix.lower()=='.step':
   reader=STEPControl_Reader();reader.ReadFile(str(p));reader.TransferRoots();shape=reader.OneShape();BRepMesh_IncrementalMesh(shape,.15,False,.15,True);dst=r/key/(p.stem+'.stl');writer=StlAPI_Writer();writer.Write(shape,str(dst));m=trimesh.load(dst,force='mesh')
  else:m=trimesh.load(p,force='mesh')
  dims=m.extents.tolist();m.apply_translation(-m.bounds.mean(axis=0))
  parts.append(dict(name=p.stem,dimensions=dims,vertices=m.vertices.round(4).tolist(),faces=m.faces.tolist(),source=str(p.relative_to(r))))
 (r/key/'meshes.json').write_text(json.dumps(parts,separators=(',',':')))
 print(key,[(p['name'],len(p['faces'])) for p in parts])
