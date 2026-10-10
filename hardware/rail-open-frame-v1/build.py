from pathlib import Path
import trimesh,numpy as np,json
out=Path(__file__).resolve().parent
src=out.parent/'rail-dome-x-upright-v1'
rim=trimesh.load(out.parent/'rail-dome-rim-v1/rim-L5x5-t1.6.stl',force='mesh')
x=trimesh.load(src/'X-ribs.stl',force='mesh')
for m in [rim,x]:m.process(validate=True)
m=trimesh.boolean.union([rim,x],engine='manifold');m.process(validate=True)
assert m.is_volume and m.is_watertight and len(m.split())==1
m.export(out/'rim-X-frame.stl')
html=(src/'assembly-preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':np.round(m.vertices,5).tolist(),'faces':m.faces.tolist()})+html[b:]
html=html.replace('03 · 돔 곡면 X자 보강대','04 · 둘레 틀 + X자 프레임').replace('레일 구조 · 얕은 돔','레일 구조 · 열린 프레임').replace('dome-rim-X-ribs.stl','rim-X-frame.stl')
a=html.index('<details>');b=html.index('</details>',a)+len('</details>')
html=html[:a]+'<details><summary>ⓘ</summary><p>돔의 얇은 면을 제거했습니다. 외경 240mm의 ㄴ자 둘레 틀(5 × 5mm, 두께 1.6mm)과 곡면을 따라 휘어진 X자 보강대(폭 1.6mm, 수직 돌출 5mm)만 남았습니다. 보강대 끝은 틀 아래로 조금 돌출됩니다.<br>드래그: 회전 · 휠: 확대<br>스무딩 없음. 중앙축·레일은 아직 없습니다. STL은 조립 좌표이며 출력 방향과 서포트는 별도 검토가 필요합니다.</p></details>'+html[b:]
(out/'assembly-preview.html').write_text(html)
spec={'watertight':bool(m.is_watertight),'connected_solids':len(m.split()),'triangles':len(m.faces),'bounds_mm':m.bounds.tolist()};(out/'specs.json').write_text(json.dumps(spec,indent=2));print(spec)
