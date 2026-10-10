from pathlib import Path
import trimesh,numpy as np,json,re,shutil
out=Path(__file__).resolve().parent;src=out.parent/'ring-380-dual-worm-xy'
def box(d,p):
 m=trimesh.creation.box(extents=d);m.apply_translation(p);return m
def cx(r,l,x,z=5.5):
 m=trimesh.creation.cylinder(radius=r,height=l,sections=96);m.apply_transform(trimesh.geometry.align_vectors([0,0,1],[1,0,0]));m.apply_translation([x,0,z]);return m
def lower(m):
 c=m.copy();c.apply_transform(np.array([[0,1,0,0],[1,0,0,0],[0,0,-1,1],[0,0,0,1.]]));return c
base=trimesh.load(src/'fixed-frame-dual-racks.stl',force='mesh')
moving=trimesh.load(src/'moving-discs-worm-clearance.stl',force='mesh')
worm=trimesh.load(src/'worm-assembled.stl',force='mesh');wy=trimesh.load(src/'lower-y-worm-assembled.stl',force='mesh')
clips=[]
for x in [-7,2]:
 # 1mm shell, 0.1mm radial clearance, top insertion mouth 5.4mm.
 c=trimesh.boolean.intersection([cx(4.1,2.4,x),box([3,10,7],[x,0,6.8])],engine='manifold')
 c=trimesh.boolean.difference([c,cx(3.1,3,x),box([3,5.4,5],[x,0,10])],engine='manifold')
 clips.append(c)
# Rear stop with open wire notch, 0.2mm from nominal motor rear face.
stop=box([1,7.4,3],[-10.2,0,4.7])
stop=trimesh.boolean.difference([stop,box([2,3,3],[-10.2,0,6])],engine='manifold');clips.append(stop)
upper=trimesh.boolean.union(clips,engine='manifold');mounts=trimesh.util.concatenate([upper,lower(upper)])
moving=trimesh.boolean.union([moving,upper,lower(upper)],engine='manifold')
assert moving.is_watertight and moving.is_volume and len(moving.split())==1
checks=[]
for dx,dy in [(0,0),(5,0),(-5,0),(0,5),(0,-5),(3.5,3.5),(-3.5,-3.5)]:
 m=mounts.copy();m.apply_translation([dx,dy,0]);h=trimesh.boolean.intersection([base,m],engine='manifold');v=0 if h.is_empty else abs(h.volume);assert v<.001;checks.append([dx,dy,v])
for part in [worm,wy,cx(3,15,-2),lower(cx(3,15,-2))]:
 h=trimesh.boolean.intersection([moving,part],engine='manifold');assert h.is_empty or abs(h.volume)<.001
moving.export(out/'moving-discs-motor-clips.stl')
for name in ['fixed-frame-dual-racks.stl','worm-assembled.stl','lower-y-worm-assembled.stl','worm-bore-1.20mm.stl']:shutil.copy2(src/name,out/name)
meshes=[base,moving,worm,wy];assembly=trimesh.util.concatenate(meshes)
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts', 'const counts='+json.dumps([len(m.faces)*3 for m in meshes])+';counts',s)
s=re.sub(r'<h1>.*?</h1>','<h1>상부 X + 하부 Y · 615 모터 고정 클립</h1>',s)
s=s.replace('</small>',' · 모터당 클립 2개 / 벽 1mm / 내경 6.2mm / 후면 스토퍼</small>',1)
s=s.replace('</nav>','<a href="moving-discs-motor-clips.stl" download>모터 고정대 포함 이동판 STL</a></nav>',1)
(out/'preview.html').write_text(s)
(out/'checks.json').write_text(json.dumps({'mount_frame_collision_checks':checks,'moving_watertight':True,'moving_components':1},indent=2))
print('Complete: clips and rear stops on both discs; mount clearance checks passed.',flush=True)
