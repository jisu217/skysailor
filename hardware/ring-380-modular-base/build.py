from pathlib import Path
import trimesh,numpy as np,math,json,re
out=Path(__file__).resolve().parent;root=out.parent
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
# Ring wall and floor only, independent of old arms and arches.
floor=trimesh.creation.annulus(r_min=187,r_max=190,height=1,sections=1440);floor.apply_translation([0,0,.5])
wall=trimesh.creation.annulus(r_min=189,r_max=190,height=1.05,sections=1440);wall.apply_translation([0,0,1.475])
parts=[floor,wall]
all_slots=[]
# Inward sockets for future flat 6 x 1 mm arm ends. Open toward center.
# Slot width 6.4, height 1.4; socket lower/upper skins 1 mm.
for i in range(4):
 shell=box([5,8,3],[187.5,0,1.5])
 void=box([4.5,6.4,1.4],[186.75,0,1.5])
 shell=trimesh.boolean.difference([shell,void],engine='manifold')
 turn=trimesh.transformations.rotation_matrix(i*math.pi/2,[0,0,1]);shell.apply_transform(turn);void.apply_transform(turn);all_slots.append(void);parts.append(shell)
# Short sloping sleeves follow the existing arch tangent (~62 degrees).
# Local X: width across rib, Y: thickness, Z: insertion direction.
angle=math.asin(190/215)
for i in range(8):
 a=i*math.pi/4
 tangent=np.array([-math.cos(a)*math.cos(angle),-math.sin(a)*math.cos(angle),math.sin(angle)])
 width=np.array([-math.sin(a),math.cos(a),0.])
 normal=np.cross(tangent,width)
 rotation=np.eye(4);rotation[:3,:3]=np.column_stack([width,normal,tangent])
 sleeve=box([5,2.6,4],[0,0,2])
 slot=box([3.4,1,4],[0,0,2.8]) # 0.8 mm blind bottom, open upper end
 sleeve=trimesh.boolean.difference([sleeve,slot],engine='manifold')
 sleeve.apply_transform(rotation);sleeve.apply_translation([188.3*math.cos(a),188.3*math.sin(a),.8]);parts.append(sleeve)
 slot.apply_transform(rotation);slot.apply_translation([188.3*math.cos(a),188.3*math.sin(a),.8]);all_slots.append(slot)
ring=trimesh.boolean.union(parts,engine='manifold')
ring=trimesh.boolean.difference([ring]+all_slots,engine='manifold')

# Divide at diagonals, so every quarter has one complete socket.
rot=ring.copy();rot.apply_transform(trimesh.transformations.rotation_matrix(math.pi/8,[0,0,1]))
quarter=trimesh.boolean.intersection([rot,box([200,200,10],[100,100,4])],engine='manifold')
quarter.merge_vertices(digits_vertex=5)
quarter.update_faces(quarter.nondegenerate_faces());quarter.update_faces(quarter.unique_faces());quarter.remove_unreferenced_vertices();quarter.fill_holes()
assert quarter.is_volume and quarter.is_watertight and len(quarter.split())==1
assert max(quarter.extents[:2])<256
quarter.export(out/'ring-quarter-print.stl')
assembled=[]
for i in range(4):
 q=quarter.copy();q.apply_transform(trimesh.transformations.rotation_matrix(-math.pi/8+i*math.pi/2,[0,0,1]));q.export(out/f'ring-quarter-{i+1}-assembled.stl');assembled.append(q)
# Standalone center seat, without residual cross arms or arches.
seat=trimesh.creation.annulus(r_min=2.5,r_max=5.5,height=1,sections=256);seat.apply_translation([0,0,.5])
w=trimesh.creation.annulus(r_min=4.5,r_max=5.5,height=8,sections=256);w.apply_translation([0,0,5])
seat=trimesh.boolean.union([seat,w],engine='manifold')
for a in np.arange(4)*math.pi/2:
 h=trimesh.creation.cylinder(radius=.6,height=5,sections=64);h.apply_transform(trimesh.geometry.align_vectors([0,0,1],[math.cos(a),math.sin(a),0]));h.apply_translation([5*math.cos(a),5*math.sin(a),7.5]);seat=trimesh.boolean.difference([seat,h],engine='manifold')
assert seat.is_volume and seat.is_watertight
seat.export(out/'center-seat-print.stl')
meshes=assembled+[seat];display=trimesh.util.concatenate(meshes)
s=(root/'ring-380-center-seat-11/preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':display.vertices.tolist(),'faces':display.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'<h1>.*?</h1>','<h1>4분할 링 + 별도 중앙 받침</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>팔 소켓 길이 5mm / 외벽 0.8mm · 리브 소켓 8개 / 구멍 3.4 × 1mm · 링 접합 잠금은 후속 설계</small>',s)
s=s.replace('frame-seat-11-hole-5.stl','ring-quarter-print.stl').replace('STL 다운로드','링 ¼ STL').replace('</nav>','<a href="center-seat-print.stl" download>중앙 받침 STL</a></nav>')
old='scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0x85c9de,roughness:.4,flatShading:true})));'
new='let offset=0;const counts='+json.dumps([len(m.faces)*3 for m in meshes])+''';counts.forEach((count,i)=>{const geom=g.clone();geom.setDrawRange(offset,count);offset+=count;scene.add(new T.Mesh(geom,new T.MeshStandardMaterial({color:[0x85c9de,0x9fd8b0,0xf0b66b,0xc7a1dd,0xe7e9ef][i],roughness:.45,flatShading:true}))) });'''
assert old in s;s=s.replace(old,new)
(out/'preview.html').write_text(s)
print(json.dumps({'quarter_dimensions_mm':quarter.extents.tolist(),'quarter_PLA_g':quarter.volume*.00124,'seat_PLA_g':seat.volume*.00124,'socket_mm':[6.4,1.4],'ring_join':'plain butt ends; connector not yet designed'}))
