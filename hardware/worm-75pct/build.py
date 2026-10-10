from pathlib import Path
import trimesh,numpy as np,json,base64
out=Path(__file__).resolve().parent
m=trimesh.load(out.parent/'worm-v2-short/worm-v2-short-bore-1.20mm.stl')
inner=np.linalg.norm(m.vertices[:,:2],axis=1)<.601
m.apply_scale(.75)
m.vertices[inner,:2]/=.75
assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
m.export(out/'worm-6x6mm-bore-1.2mm.stl')
w=trimesh.load(out.parent/'gear-75pct/wheel-24t-75pct-2mm.stl')
w.apply_translation([0,0,-1])
C=10.05
vol=[]
for phi in np.linspace(0,2*np.pi,25)[:-1]:
 a=m.copy();a.apply_transform(trimesh.transformations.rotation_matrix(phi,[0,0,1]));a.apply_transform(np.array([[0,0,1,-3],[1,0,0,-C],[0,1,0,0],[0,0,0,1]]))
 b=w.copy();b.apply_transform(trimesh.transformations.rotation_matrix(-phi/24,[0,0,1]))
 v=trimesh.boolean.intersection([a,b],engine='manifold');vol.append(float(v.volume) if len(v.faces) else 0)
spec=dict(diameter_mm=6,length_mm=6,root_diameter_mm=4.5,bore_mm=1.2,pitch_mm=1.875,starts=1,centre_distance_mm=C,max_interference_mm3=max(vol),sampled_poses=24)
(out/'dimensions.json').write_text(json.dumps(spec,indent=2))
sm=m.simplify_quadric_decimation(face_count=9000)
data={k:base64.b64encode(np.asarray(a,dtype=t).tobytes()).decode() for k,a,t in [('v',sm.vertices,'<f4'),('f',sm.faces,'<u4')]}
s=(out.parent/'gear-75pct/viewer-template.html').read_text().replace('gear-small','worm-small').replace('24T 기어 · Ø15.82 × 2 mm','웜기어 · Ø6 × 6 mm').replace('중심 구멍 Ø3.6 mm','축 구멍 Ø1.2 · 피치 1.875 mm').replace('축소한 24개 이빨 기어','축소한 웜기어').replace('distance=32','distance=23').replace("design:'gear-75pct',diameter_mm:15.824,thickness_mm:2,bore_mm:3.6","design:'worm-75pct',diameter_mm:6,length_mm:6,bore_mm:1.2,pitch_mm:1.875").replace('camera.lookAt(0,0,1)','camera.lookAt(0,0,3)').replace('1+distance*Math.sin(pitch)','3+distance*Math.sin(pitch)')
Path('/Users/cykim/.codex/visualizations/2026/10/04/01a105f3-6969-7332-a6aa-bcec01881978/worm-75pct.html').write_text(s.replace('__DATA__',json.dumps(data)))
print(spec)
