from pathlib import Path
import trimesh,numpy as np,json,re
out=Path(__file__).resolve().parent
source=out.parent/'ring-380-contour-sliders'
base=trimesh.load(out.parent/'ring-380-eight-ribs-pillar/ring-380-eight-ribs-pillar.stl',force='mesh')
z=base.vertices[:,2].copy();base.vertices[:,2]=np.where(z<=2,z/2,z-1)
# Printed slider is translated +1.2 relative to assembled coordinates.
slider=trimesh.load(source/'linked-slider-print.stl',force='mesh');slider.apply_translation([0,0,-1.2])
z=slider.vertices[:,2].copy();slider.vertices[:,2]=np.where(z>1,z-1,z)
for m in [base,slider]:
 assert m.is_watertight and m.is_volume
for dx in [-15,0,15]:
 m=slider.copy();m.apply_translation([dx,0,0]);hit=trimesh.boolean.intersection([base,m],engine='manifold')
 assert hit.is_empty or abs(hit.volume)<1e-5
base.export(out/'frame.stl')
printed=slider.copy();printed.apply_translation([0,0,1.2]);printed.export(out/'linked-slider-print.stl')
meshes=[base,slider];assembly=trimesh.util.concatenate(meshes);assembly.export(out/'assembly.stl')
s=(source/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=s.replace('ㅗ자 밀착형 슬라이더 · 삼각 보강','바닥 1mm · 밀착형 슬라이더')
s=s.replace('중심 간격 50mm · 쉘 / 아래판 두께 1mm','링 / +자 바닥 1mm · 중심 간격 50mm · 슬라이더 두께 1mm')
s=re.sub(r'const counts=\[[^\]]+\]', 'const counts='+json.dumps([len(m.faces)*3 for m in meshes]),s)
(out/'preview.html').write_text(s)
print(json.dumps({'frame_g':base.volume*.00124,'slider_g':slider.volume*.00124,'total_g':assembly.volume*.00124,'floor_mm':1}))
