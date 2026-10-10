from pathlib import Path
import trimesh,numpy as np,json,zipfile
out=Path(__file__).resolve().parent
root=out.parent
parts={}
def add(name,path,x,y,flip=False):
 m=trimesh.load(path)
 if flip:m.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 m.apply_translation([-m.bounds[:,0].mean()+x,-m.bounds[:,1].mean()+y,-m.bounds[0,2]])
 assert m.is_watertight and len(m.split())==1
 parts[name]=m
add('lower-frame',root/'hex-string-holes-v1/lower-frame.stl',-36,-15)
add('upper-frame',root/'hex-string-holes-v1/upper-frame.stl',32,-15,True)
for i,x in enumerate([-50,-30,-10]):
 add(f'spool-lower-{i+1}',root/'spool-thin16-v1/lower-print.stl',x,32)
 add(f'spool-upper-{i+1}',root/'spool-thin16-v1/upper-print.stl',x,54)
for i,x in enumerate([15,30,45]):
 add(f'worm-body-{i+1}',root/'split-worm-r12-v1/worm-body-print.stl',x,32)
 add(f'support-pin-{i+1}',root/'split-worm-r12-v1/support-pin-print.stl',x,54)
for a,(ka,ma) in enumerate(parts.items()):
 assert abs(ma.bounds[0,2])<1e-6
 for kb,mb in list(parts.items())[a+1:]:
  separation=np.maximum(ma.bounds[0,:2]-mb.bounds[1,:2],mb.bounds[0,:2]-ma.bounds[1,:2])
  assert separation.max()>=3,(ka,kb,separation)
for name,m in parts.items():
 q=m.copy();q.apply_translation([-q.bounds[:,0].mean(),-q.bounds[:,1].mean(),0]);q.export(out/(name+'.stl'))
whole=trimesh.util.concatenate(list(parts.values()));bounds=whole.bounds.copy()
whole.apply_translation([128,128,0]);assert np.all(whole.bounds[0,:2]>=0) and np.all(whole.bounds[1,:2]<=256)
whole.export(out/'all-parts-arranged.stl')
(out/'layout.json').write_text(json.dumps({'part_count':len(parts),'bed_mm':[256,256],'footprint_mm':(bounds[1]-bounds[0]).tolist(),'parts':list(parts),'checks':['14 closed single-body components','all bottoms at Z=0','XY bounding boxes separated by at least 3mm','all parts inside 256mm square']},indent=2))
src=root/'generated-worm-pair-v1'
s=(src/'viewer-template.html').read_text().replace('generated-worm-pair','print-string-holes')
s=s.replace('운동으로 생성한 웜 치형 · 시험 설계','실 고정 구멍 추가 · 총 14개').replace('24:1 동시 생성 · 축 간격 8.5 mm · 출력 여유 0.08 mm','판 각 1 · 스풀 조각 6 · 웜 몸통 3 · 지지 축 3')
a=s.index(' <label class="form-label">');b=s.index(' <div class="text-small" data-status>',a);s=s[:a]+s[b:]
a=s.index(' meshes.worm.geometry.translate');b=s.index(' const ambient=',a);s=s[:a]+s[b:]
s=s.replace('distance=75','distance=220').replace('Math.min(90','Math.min(450')
s=s.replace("name==='base'||name==='top'","name.endsWith('frame')").replace("name==='worm'","name.startsWith('worm')")
s=s.replace(" const ambient="," const grid=new T.GridHelper(256,32);grid.rotation.x=Math.PI/2;grid.position.z=-.03;scene.add(grid);\n const ambient=")
s=s.replace('function render(){','function render(){grid.material.color.copy(color(\'--foreground\'));grid.material.transparent=true;grid.material.opacity=.12;')
(out/'viewer-template.html').write_text(s)
ns={'__file__':str(src/'viewer.py'),'out':out,'canonical':parts}
exec('from pathlib import Path\nimport numpy as np,trimesh,json,base64,gzip\n'+ 'def pack(a,delta=False):'+(src/'viewer.py').read_text().split('def pack(a,delta=False):')[1],ns)
print((out/'layout.json').read_text())

import runpy
runpy.run_path(str(out.parent/'revision-workbench-v1/fullscreen.py'))['apply'](out/'assembly-preview.html')
