from pathlib import Path
import trimesh as t,numpy as np,math,json,re,shutil,zipfile
out=Path(__file__).resolve().parent;root=out.parent;src=root/'ring-380-dual-drive-rib-sockets';kit=root/'rib-eight-eye032-connector'
def box(d,p):
 m=t.creation.box(d);m.apply_translation(p);return m
floor=t.creation.annulus(r_min=187,r_max=190,height=1,sections=1440);floor.apply_translation([0,0,.5])
wall=t.creation.annulus(r_min=189,r_max=190,height=1.05,sections=1440);wall.apply_translation([0,0,1.475])
parts=[floor,wall];cuts=[]
R=214.7;alpha=math.asin(190/215);zc=2-math.sqrt(215**2-190**2)
for i in range(8):
 a=i*math.pi/4;rad=np.array([math.cos(a),math.sin(a),0]);width=np.array([-math.sin(a),math.cos(a),0]);tangent=-rad*math.cos(alpha)+np.array([0,0,math.sin(alpha)]);normal=np.cross(tangent,width)
 tip=rad*(R*math.sin(alpha))+np.array([0,0,zc+R*math.cos(alpha)])
 mat=np.eye(4);mat[:3,:3]=np.column_stack([width,normal,tangent]);mat[:3,3]=tip-.8*tangent
 shell=box([5,2.6,4],[0,0,2]);slot=box([3.4,1,4],[0,0,2.8]);shell.apply_transform(mat);slot.apply_transform(mat);parts.append(shell);cuts.append(slot)
ring=t.boolean.difference([t.boolean.union(parts,engine='manifold')]+cuts,engine='manifold')
assert ring.is_volume and len(ring.split())==1
ring.export(out/'ring-with-8-sockets.stl')
rot=ring.copy();rot.apply_transform(t.transformations.rotation_matrix(math.pi/8,[0,0,1]))
quarter=t.boolean.intersection([rot,box([200,200,20],[100,100,8])],engine='manifold')
assert quarter.is_volume and len(quarter.split())==1
quarter.export(out/'ring-quarter-print.stl')
meshes=[ring]
for name in [f'rib-{i}-assembled.stl' for i in range(1,9)]+['crown-pin-assembled.stl','crown-cap-assembled.stl']:
 shutil.copy2(src/name,out/name);meshes.append(t.load(out/name))
assembly=t.util.concatenate(meshes);assembly.export(out/'assembly-preview.stl')
s=(src/'preview.html').read_text();a=s.index('const data=');b=s.index(';\nif(!window.THREE)',a)
s=s[:a]+'const data='+json.dumps({'vertices':assembly.vertices.tolist(),'faces':assembly.faces.tolist()},separators=(',',':'))+s[b:]
s=re.sub(r'const counts=\[.*?\];counts','const counts='+json.dumps([len(m.faces)*3 for m in meshes])+';counts',s)
s=re.sub(r'color:\[[^\]]+\]\[i\]','color:[0x85c9de,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0x9fd8b0,0xc7a1dd,0xf0b66b,0xf0b66b][i]',s)
s=re.sub(r'<h1>.*?</h1>','<h1>Ø380 · 리브 8개 상부 프레임</h1>',s)
s=re.sub(r'<small>.*?</small>','<small>외곽 링 + 리브 소켓 8개 + 리브 0.6×3mm + 꼭대기 원판·사각핀·원형 캡 · 중앙 십자판과 구동부 제외</small>',s)
s=re.sub(r'<nav>.*?</nav>','<nav><a href="upper-frame-parts.zip" download>분리 부품 ZIP</a><a href="assembly-preview.stl" download>조립 형상 STL (미리보기용)</a></nav>',s,flags=re.S)
a=s.index('function cylX(');b=s.index('scene.add(new T.HemisphereLight',a);s=s[:a]+s[b:]
s=s.replace('구동부 확대','전체 프레임').replace('target.set(3,0,4);d=95;az=-1.1;el=.8','target.set(0,0,48);d=820;az=-1.1;el=.48')
s=re.sub(r'<title>.*?</title>','<title>리브 8개 상부 프레임</title>',s)
(out/'preview.html').write_text(s)
printdir=out/'print-parts';printdir.mkdir(exist_ok=True);shutil.copy2(out/'ring-quarter-print.stl',printdir/'ring-quarter-print.stl')
for n in ['rib-eye-0deg.stl','rib-eye-45deg.stl','lower-square-pin.stl','upper-square-cap.stl']:shutil.copy2(kit/n,printdir/n)
(printdir/'READ-ME.txt').write_text('상부 프레임만 구성한 부품입니다.\n링 1/4 4개, 평면 리브 0도 4개 + 45도 4개, 꼭대기 사각핀 1개와 원형 캡 1개.\n링 네 조각은 맞대어 접착하는 구조입니다. 리브는 평평한 띠로 출력한 뒤 구부려 조립합니다.\n조립 형상 STL은 미리보기용이며 통째로 출력하지 않습니다.\n중앙 십자판, 받침, 구동부는 포함하지 않습니다. 리브 소켓은 기존 조립 리브 끝 위치에 맞췄습니다. 출력 끼움은 실물 확인이 필요합니다.\n')
with zipfile.ZipFile(out/'upper-frame-parts.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in printdir.iterdir():z.write(p,p.name)
(out/'inspection.json').write_text(json.dumps({'quarter_dimensions_mm':quarter.extents.tolist(),'assembly_bounds_mm':assembly.bounds.tolist(),'ring_single_watertight_solid':ring.is_watertight,'rib_count':8},indent=2))
(root/'model-viewer/current.json').write_text(json.dumps({'model':out.name,'note':'외곽 링 + 8개 리브 + 꼭대기 결합부 / 상부 프레임만'},ensure_ascii=False))
print(quarter.extents,assembly.bounds)
