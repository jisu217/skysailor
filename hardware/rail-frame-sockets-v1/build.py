from pathlib import Path
import trimesh,numpy as np,json
out=Path(__file__).resolve().parent
rim=trimesh.load(out.parent/'rail-dome-rim-v1/rim-L5x5-t1.6.stl',force='mesh')
x=trimesh.load(out.parent/'rail-dome-x-upright-v1/X-ribs.stl',force='mesh')
for m in [rim,x]:m.process(validate=True)
def box(size,center,angle):
 m=trimesh.creation.box(size);m.apply_translation(center);m.apply_transform(trimesh.transformations.rotation_matrix(angle,[0,0,1]));return m
def union(ms):return trimesh.boolean.union(ms,engine='manifold')
angles=np.pi/4+np.arange(4)*np.pi/2
x=trimesh.boolean.intersection([x,trimesh.creation.cylinder(radius=110,height=120,sections=512)],engine='manifold')
tabs=[box([8,3,3],[113,0,2],a) for a in angles]
x=union([x]+tabs)
blocks=[box([9,6,5.6],[114.5,0,1.7],a) for a in angles]
frame=union([rim]+blocks)
# Open-top, open-inner-side slots; 0.2mm side/end/bottom clearance.
slots=[box([8.2,3.4,12],[113.1,0,6.3],a) for a in angles]
frame=trimesh.boolean.difference([frame]+slots,engine='manifold')
for name,m in [('rim-with-sockets',frame),('X-with-tabs',x)]:
 m.process(validate=True);assert m.is_volume and m.is_watertight and len(m.split())==1
 m.export(out/(name+'.stl'))
collision=trimesh.boolean.intersection([frame,x],engine='manifold');vol=abs(collision.volume) if len(collision.faces) else 0
assert vol<1e-5,vol
m=trimesh.util.concatenate([frame,x])
html=(out.parent/'rail-open-frame-v1/assembly-preview.html').read_text();a=html.index('const data=');b=html.index(';\nif(!window.THREE)',a)
html=html[:a]+'const data='+json.dumps({'vertices':np.round(m.vertices,5).tolist(),'faces':m.faces.tolist()})+html[b:]
html=html.replace('04 · 둘레 틀 + X자 프레임','05 · 위에서 끼우는 X자 프레임').replace('rim-X-frame.stl','rim-with-sockets.stl').replace('>STL</a>','>틀 STL</a><a href="X-with-tabs.stl" download>X자 STL</a>')
a=html.index('<details>');b=html.index('</details>',a)+len('</details>')
html=html[:a]+'<details><summary>ⓘ</summary><p>별도 부품 두 개: 둘레 틀과 X자 보강대. 네 끝에 8 × 3 × 3mm 돌기를 추가했습니다. 위에서 내리면 위·안쪽이 열린 홈에 들어갑니다. 옆면과 바깥 끝, 바닥에 0.2mm 여유를 주었습니다. 들어올림 방지는 아직 없습니다.<br>드래그 회전 · 휠 확대. 출력 맞춤은 실물 확인이 필요합니다.</p></details>'+html[b:]
# Two materials on exact full meshes; no triangle reduction.
needle='g.computeVertexNormals();scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,metalness:.12,roughness:.48,flatShading:true,side:T.DoubleSide})));'
replacement='g.computeVertexNormals();g.addGroup(0,'+str(len(frame.faces)*3)+',0);g.addGroup('+str(len(frame.faces)*3)+','+str(len(x.faces)*3)+',1);const mats=[0x85c9de,0xf0b66b].map(color=>new T.MeshStandardMaterial({color,metalness:.12,roughness:.48,flatShading:true,side:T.DoubleSide}));scene.add(new T.Mesh(g,mats));'
assert needle in html;html=html.replace(needle,replacement)
(out/'assembly-preview.html').write_text(html)
(out/'specs.json').write_text(json.dumps({'tab_mm':[8,3,3],'clearance_mm':.2,'overlap_mm3':vol,'frame_triangles':len(frame.faces),'X_triangles':len(x.faces)},indent=2));print('Two watertight parts; overlap mm3:',vol)
