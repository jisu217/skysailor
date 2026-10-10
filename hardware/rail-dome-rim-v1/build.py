from pathlib import Path
import trimesh,numpy as np,json
out=Path(__file__).resolve().parent
src=out.parent/'rail-dome-v1'
dome=trimesh.load(src/'dome-240x40-shell1mm.stl',force='mesh');dome.merge_vertices();dome.process(validate=True)
# L section, outside envelope 5 x 5 mm, both legs 1.6 mm.
profile=np.array([[115,0],[120,0],[120,5],[118.4,5],[118.4,1.6],[115,1.6],[115,0]])
rim=trimesh.creation.revolve(profile,sections=512);rim.fix_normals()
assert rim.is_watertight and rim.is_volume
combined=trimesh.boolean.union([dome,rim],engine='manifold');combined.process(validate=True)
assert combined.is_watertight and combined.is_volume and len(combined.split())==1
rim.export(out/'rim-L5x5-t1.6.stl');combined.export(out/'dome-with-L-rim.stl')
html=(src/'assembly-preview.html').read_text()
a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':np.round(combined.vertices,5).tolist(),'faces':combined.faces.tolist()})+html[b:]
html=html.replace('01 · 얕은 돔','02 · 돔 + ㄴ자 테두리').replace('지름 240 mm · 높이 40 mm · 두께 1 mm','지름 240 mm · 테두리 5 × 5 mm · 틀 두께 1.6 mm').replace('dome-240x40-shell1mm.stl','dome-with-L-rim.stl')
html=html.replace('정확한 반구보다 낮은 구면 돔입니다.','돔 둘레에 ㄴ자 단면의 틀을 일체형으로 붙였습니다. 외경 240mm를 유지하며 안쪽으로 5mm, 위로 5mm입니다. 두 다리 두께는 각각 1.6mm이고 안쪽 빈 단면은 3.4 × 3.4mm입니다. 틀은 돔과 만나는 부분에서 합쳐집니다.<br>정확한 반구보다 낮은 구면 돔입니다.')
html=html.replace('roughness:.48,side:T.DoubleSide','roughness:.48,flatShading:true,side:T.DoubleSide')
(out/'assembly-preview.html').write_text(html)
spec={'outer_diameter_mm':240,'rim_section_width_mm':5,'rim_section_height_mm':5,'rim_wall_mm':1.6,'direction':'inward and upward from outer lower edge','combined_watertight':bool(combined.is_watertight),'connected_solids':len(combined.split()),'triangles':len(combined.faces)}
(out/'specs.json').write_text(json.dumps(spec,indent=2));print(json.dumps(spec))
