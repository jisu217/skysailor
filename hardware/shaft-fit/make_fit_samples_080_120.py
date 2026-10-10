from pathlib import Path
import json
import numpy as np
import trimesh

OUT = Path(__file__).resolve().parent
DIAMETERS = [0.80, 0.90, 1.00, 1.10, 1.20]
SEGMENTS = {'0':'abcdef', '2':'abged', '3':'abgcd', '4':'fgbc', '5':'afgcd', '6':'afgecd', '7':'abc', '8':'abcdefg', '9':'abcdfg', '1':'bc'}

def box(x,y,z,sx,sy,sz):
    m = trimesh.creation.box(extents=[sx,sy,sz])
    m.apply_translation([x+sx/2,y+sy/2,z+sz/2])
    return m

def digit(n,x,y):
    # Raised seven-segment text, minimum stroke 0.5 mm.
    coords={'a':(.25,2.5,1.5,.5),'g':(.25,1.25,1.5,.5),'d':(.25,0,1.5,.5),
            'f':(0,1.5,.5,1.25),'b':(1.5,1.5,.5,1.25),
            'e':(0,.25,.5,1.25),'c':(1.5,.25,.5,1.25)}
    return [box(x+coords[s][0],y+coords[s][1],.5,coords[s][2],coords[s][3],.46) for s in SEGMENTS[n]]

def sample(d):
    base=box(0,0,0,14,5.6,.6)
    hub=trimesh.creation.cylinder(radius=2.5,height=4,sections=128)
    hub.apply_translation([2.8,2.8,2])
    text=[]
    label=f'{d:.2f}'
    text += digit(label[0],5.7,1.3)
    text += [box(7.95,1.3,.5,.5,.5,.46)]
    text += digit(label[2],8.7,1.3)
    text += digit(label[3],11.2,1.3)
    solid=trimesh.boolean.union([base,hub,*text],engine='manifold')
    hole=trimesh.creation.cylinder(radius=d/2,height=6,sections=96)
    hole.apply_translation([2.8,2.8,2])
    result=trimesh.boolean.difference([solid,hole],engine='manifold')
    assert result.is_watertight and result.is_winding_consistent and result.volume>0
    assert len(result.split())==1
    # Verify a clear, full-depth bore in the resulting mesh.
    for z in [.1,.6,1.1,2,3.9]:
        section=result.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
        loops=section.discrete
        radii=[np.linalg.norm(p[:,:2]-[2.8,2.8],axis=1) for p in loops]
        assert any(np.all(r >= (d/2)*np.cos(np.pi/96)-1e-6) and np.all(r <= d/2+1e-6) for r in radii), (d,z)
    return result

parts=[]
report=[]
for i,d in enumerate(DIAMETERS):
    m=sample(d)
    name=f'shaft-fit-{d:.2f}mm.stl'
    m.export(OUT/name)
    report.append({'file':name,'hole_diameter_mm':d,'watertight':bool(m.is_watertight),'volume_mm3':float(m.volume)})
    m.apply_translation([i*18,0,0])
    parts.append(m)
combined=trimesh.util.concatenate(parts)
combined.export(OUT/'shaft-fit-080-to-120mm.stl')
assert len(combined.split())==5
(OUT/'validation-080-to-120.json').write_text(json.dumps(report,indent=2)+'\n')
print('Created five labelled, watertight samples. Combined dimensions:',combined.extents)
