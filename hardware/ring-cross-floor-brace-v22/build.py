from pathlib import Path
import json,re,shutil
import trimesh
out=Path(__file__).resolve().parent;src=out.parent/'ring-cross-lower-arch-slots-v21'
base=trimesh.load(src/'ring-print.stl',force='mesh');base.process(validate=True)
# Span the 188mm opening, with 0.5mm overlap into the existing ring at each end.
bars=[]
for size in ([189,4,2],[4,189,2]):
 b=trimesh.creation.box(size);b.apply_translation([0,0,1]);bars.append(b)
ring=trimesh.boolean.union([base]+bars,engine='manifold')
assert ring.is_volume and ring.is_watertight and len(ring.split())==1
ring.export(out/'ring-print.stl')
parts=[ring]
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','mid-ring-assembled.stl']:
 m=trimesh.load(src/name,force='mesh');m.process(validate=True);parts.append(m)
 hit=trimesh.boolean.intersection([ring,m],engine='manifold');assert not len(hit.faces) or abs(hit.volume)<.001
for name in ['arch-A-top-slot-assembled.stl','arch-B-bottom-slot-assembled.stl','arch-A-top-slot-print.stl','arch-B-bottom-slot-print.stl','mid-ring-assembled.stl','mid-ring-print.stl']:shutil.copy2(src/name,out/name)
assembly=trimesh.util.concatenate(parts);total=sum(m.volume for m in parts)/1000
html=(src/'preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()})+html[b:]
html=re.sub(r'<h1>.*?</h1>','<h1>바닥 십자 보강대 · 폭 4mm × 두께 2mm</h1>',html)
html=re.sub(r'<small>.*?</small>',f'<small>바닥 z=0~2mm · 아치와 같은 방향 · 전체 {total:.2f}cm³</small>',html)
html=re.sub(r'<details>.*?</details>','<details><summary>ⓘ</summary><p>아래 링 안쪽을 가로지르는 십자 보강대를 추가했습니다.<br>두 막대 모두 폭 4mm, 두께 2mm. 중앙도 전체 두께 2mm.<br>바닥 z=0~2mm, 양끝은 링과 일체형으로 연결.<br>최신 아치 아래 슬롯을 포함한 v21 형상을 유지했습니다.<br>전체 삼각형 표시, 스무딩 없음.</p></details>',html)
html=re.sub(r'const counts=\[[^\]]+\]','const counts='+json.dumps([len(m.faces)*3 for m in parts]),html);(out/'preview.html').write_text(html)
spec={'brace_width_mm':4,'brace_thickness_mm':2,'brace_z_mm':[0,2],'added_cm3':(ring.volume-base.volume)/1000,'total_cm3':total,'connected_base':True,'arch_collision_mm3':0,'smooth_shading':False}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec,indent=2))
