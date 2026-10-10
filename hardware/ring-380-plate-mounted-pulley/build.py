from pathlib import Path
import trimesh,numpy as np,json,re,math
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-ball-plate-50'
base=trimesh.load(src/'frame-raised-seat.stl',force='mesh')
body=trimesh.load(src/'ball-rod-plate-50.stl',force='mesh')
parts=[base]
for a in np.arange(4)*math.pi/2:
 eye=trimesh.creation.annulus(r_min=.8,r_max=2.5,height=2,sections=96)
 eye.apply_transform(trimesh.geometry.align_vectors([0,0,1],[-math.sin(a),math.cos(a),0]))
 eye.apply_translation([184*math.cos(a),184*math.sin(a),2.5]);parts.append(eye)
frame=trimesh.boolean.union(parts,engine='manifold');assert frame.is_watertight and frame.is_volume
frame.export(out/'frame-four-anchors.stl')
s=(src/'preview.html').read_text();assembly=trimesh.util.concatenate([frame,body])
a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(frame.faces)*3,len(body.faces)*3]),s)
s=re.sub(r'<h1>.*?</h1>','<h1>+자 끝 고정점 4개 · 아래판 모터 풀리 1개</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>끝 고정 구멍 Ø1.6mm × 4 · 아래판 위 모터/풀리 임시 배치 · 실 감기 경로는 미확정</small>',s)
insertion='''
// Single motor and pulley on the moving lower plate: conceptual envelopes.
const motor=new T.Mesh(new T.BoxGeometry(8,12,8),new T.MeshStandardMaterial({color:0x566579}));motor.position.set(12,0,-23.83);scene.add(motor);
function cyl(radius,height,z,color){const mesh=new T.Mesh(new T.CylinderGeometry(radius,radius,height,64),new T.MeshStandardMaterial({color}));mesh.rotation.x=Math.PI/2;mesh.position.set(12,0,z);scene.add(mesh)}
cyl(1,3,-18.4,0xb8c6d1);cyl(4,3,-16.5,0x94a3b8);cyl(5,0.7,-18.0,0x94a3b8);cyl(5,0.7,-15.0,0x94a3b8);
'''
pos=s.index('scene.add(new T.HemisphereLight');s=s[:pos]+insertion+s[pos:]
s=s.replace('href="assembly.stl"','href="frame-four-anchors.stl"')
(out/'preview.html').write_text(s)
print('Prior cable drive removed by rebuilding from ball/plate baseline. Four frame anchors and one plate-mounted motor/pulley shown.')
