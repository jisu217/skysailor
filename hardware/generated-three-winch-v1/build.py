from pathlib import Path
import runpy,json,numpy as np,trimesh
out=Path(__file__).resolve().parent
src=runpy.run_path(str(out.parent/'generated-worm-pair-v1/viewer.py'))
cyl=src['cyl'];pack=src['pack'];canonical=src['canonical']
# Circular base, alternating three winches and three pillars on hexagonal directions.
radius=17
base=cyl(27.5,2,-2.6)
parts={'base':base};fixed=[base];moving=[]
for i in range(3):
 a=i*2*np.pi/3
 mat=trimesh.transformations.rotation_matrix(a,[0,0,1]);mat[:3,3]=[radius*np.cos(a),radius*np.sin(a),0]
 for name,m in canonical.items():
  q=m.copy();q.apply_transform(mat);parts[f'{name}-{i}']=q
  if name in ['lower-support','bearing']:fixed.append(q)
  if name in ['part','worm']:moving.append((f'{name}-{i}',q))
 riser=trimesh.creation.box([1.4,6,1.7]);riser.apply_translation([7.2,-8.5,-.8]);riser.apply_transform(mat);fixed.append(riser)
 a+=np.pi/3
 post=cyl(2.5,10.2,3.5);post.apply_translation([24*np.cos(a),24*np.sin(a),0]);fixed.append(post)
body=trimesh.boolean.union(fixed,engine='manifold');parts['base']=body
for i in range(3):
 for name in ['lower-support','bearing']:del parts[f'{name}-{i}']
checks=[]
for name,m in moving:
 inter=trimesh.boolean.intersection([body,m],engine='manifold');checks.append([name+' / body',abs(inter.volume) if len(inter.faces) else 0])
for i in range(3):
 for j in range(i+1,3):
  for na in canonical:
   for nb in canonical:
    def placed(n,k):
     q=canonical[n].copy();a=k*2*np.pi/3;t=trimesh.transformations.rotation_matrix(a,[0,0,1]);t[:3,3]=[radius*np.cos(a),radius*np.sin(a),0];q.apply_transform(t);return q
    aa=placed(na,i);bb=placed(nb,j)
    if np.all(aa.bounds[1]>bb.bounds[0]) and np.all(bb.bounds[1]>aa.bounds[0]):
     v=trimesh.boolean.intersection([aa,bb],engine='manifold');checks.append([f'{na}-{i} / {nb}-{j}',abs(v.volume) if len(v.faces) else 0])
(out/'checks.json').write_text(json.dumps(checks,indent=2))
print('collisions',[(n,v) for n,v in checks if v>1e-5],flush=True)
q=body.copy();q.apply_translation([0,0,3.6]);q.export(out/'base-with-supports.stl')
D={}
for name,m in parts.items():D[name]={'v':pack(m.vertices),'f':pack(m.faces,True)}
s=(out.parent/'generated-worm-pair-v1/viewer-template.html').read_text()
s=s.replace('generated-worm-pair','generated-three-winch').replace('운동으로 생성한 웜 치형 · 시험 설계','원판 위 3개 윈치 · 육각 배치').replace('24:1 동시 생성 · 축 간격 8.5 mm · 출력 여유 0.08 mm','원판 Ø55 mm · 120° 간격 · 기어 중심 반경 17 mm')
start=s.index(' meshes.worm.geometry.translate');end=s.index(' const ambient=',start)
s=s[:start]+s[end:]
a=s.index(' <label class="form-label">');b=s.index(' <div class="text-small" data-status>',a);s=s[:a]+s[b:]
s=s.replace('distance=75','distance=110').replace('Math.min(90','Math.min(180').replace("name==='worm'||name.startsWith('motor')","name.startsWith('worm')||name.startsWith('motor')")
s=s.replace('__DATA__',json.dumps(D))
old=(out.parent/'hex-spools-r7-v1/assembly-preview.html').read_text();head=old[:old.index('<div id=')];(out/'assembly-preview.html').write_text(head+s+'</html>')
print('done',flush=True)
