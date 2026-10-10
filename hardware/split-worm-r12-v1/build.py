from pathlib import Path
import trimesh,numpy as np,json,runpy
out=Path(__file__).resolve().parent
S=1+.5/7.9119722843;L=6*S;END=11.1*S
src=out.parent/'generated-worm-pair-v1'
def cyl(r,h,z):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=192);m.apply_translation([0,0,z]);return m
body=trimesh.load(out.parent/'worm-75pct/worm-6x6mm-bore-1.2mm.stl');body.apply_scale([1,1,S])
socket=cyl(.9,1.8,L-.7)
body=trimesh.boolean.difference([body,socket],engine='manifold')
pin=trimesh.boolean.union([cyl(1.2,END-L,(END+L)/2),cyl(.8,1.6,L-.7)],engine='manifold')
# peg spans L-1.5..L+0.1, socket floor L-1.6
for name,m in [('worm-body',body),('support-pin',pin)]:
 assert m.is_watertight and len(m.split())==1
 m.export(out/(name+'-assembled.stl'))
 q=m.copy()
 if name=='support-pin':q.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 q.apply_translation([0,0,-q.bounds[0,2]]);q.export(out/(name+'-print.stl'))
inter=trimesh.boolean.intersection([body,pin],engine='manifold');assert not len(inter.faces) or abs(inter.volume)<1e-5
trimesh.util.concatenate([body,pin]).export(out/'worm-assembled.stl')
(out/'parameters.json').write_text(json.dumps({'worm_lead_mm':1.875*S,'worm_body_length_mm':L,'total_length_mm':END,'journal_radius_mm':1.2,'journal_hole_radius_mm':1.4,'peg_diameter_mm':1.6,'socket_diameter_mm':1.8,'peg_length_mm':1.5,'socket_depth_mm':1.6,'motor_bore_mm':1.2,'retention':'adhesive; circular locating pin, no axial snap lock','checks':['both parts closed single bodies','no overlapping volume','print bottoms Z0']},indent=2))
ns={'out':out,'canonical':{'worm-body':body,'support-pin':pin}}
s=(out.parent/'spool-flat-key-v1/viewer-template.html').read_text().replace('spool-flat-key','split-worm-r12').replace('1단계 · 평평한 출력면과 더 뚜렷한 D자','웜 2분할 · 지지 축 반지름 1.2mm').replace('축 구멍 Ø3.4 · 결합 길이 0.9mm · 옆면 여유 0.1mm','몸통 + 접착식 지지 축 · 모터 구멍 Ø1.2 유지').replace('위 조각 벌려보기','지지 축 벌려보기').replace("meshes['upper-part']","meshes['support-pin']")
(out/'viewer-template.html').write_text(s)
exec('from pathlib import Path\nimport numpy as np,trimesh,json,base64,gzip\ndef pack(a,delta=False):'+(src/'viewer.py').read_text().split('def pack(a,delta=False):')[1],ns)
runpy.run_path(str(out.parent/'revision-workbench-v1/fullscreen.py'))['apply'](out/'assembly-preview.html')
