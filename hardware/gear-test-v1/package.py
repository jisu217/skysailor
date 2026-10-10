from pathlib import Path
import trimesh,zipfile
r=Path(__file__).resolve().parent
layout={'base':(0,0),'motor-saddle':(0,50),'wheel-24t':(38,50),'locking-key':(67,0),'retainer':(67,25),'worm-1.20mm':(67,38)}
parts=[]
for name,(x,y) in layout.items():
 m=trimesh.load(r/(name+'.stl'));m.apply_translation([x,y,0]);parts.append(m)
plate=trimesh.util.concatenate(parts);assert len(plate.split())==6;plate.export(r/'print-all-parts.stl')
with zipfile.ZipFile(r/'gear-test-v1-print-files.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in layout:z.write(r/(name+'.stl'),name+'.stl')
 for name in ['print-all-parts.stl','ASSEMBLY.txt','dimensions.json','validation.json']:z.write(r/name,name)
v=Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/gear-test-rig.html')
v.write_text((r/'viewer-template.html').read_text().replace('__MESH_DATA__',(r/'viewer-meshes.json').read_text()))
assert v.stat().st_size<1000000
print('Plate size',plate.extents,'viewer bytes',v.stat().st_size)
