from pathlib import Path
import json, shutil
import trimesh as t
out=Path(__file__).resolve().parent
src=out.parent/'615-worm-bore10'
m=t.load(src/'worm.stl');(out/'worm.json').write_text(json.dumps({'vertices':m.vertices.tolist(),'faces':m.faces.tolist()},separators=(',',':')))
shutil.copy2(src/'worm-bore-1.0mm-print.stl',out/'worm-print.stl')
s=(out.parent/'615-worm-clearance-v2'/'preview.html').read_text()
s=s.replace('<title>615 슬롯형 웜 액추에이터 시험품</title>','<title>615 모터 · 웜기어 개선</title>')
a=s.index('<div id="view">');b=s.index('<script src=',a)
s=s[:a]+'''<div id="view"></div><header><h2>615 모터 + 웜기어</h2><p>회색: 모터·축 · 보라: 웜기어</p><button id="angle">사선</button><button id="top">위에서</button><button id="side">옆에서</button></header><aside><b>모터와 웜 배치 검토</b><p>모터: Ø6 × 15mm<br>웜 치형: Ø9 × 8mm<br>웜 전체 길이: 15mm<br>지지축: Ø2.8mm<br>웜 축 구멍: Ø1.0mm<br>리드: 2.5mm</p><p>기존 조립 위치를 유지했습니다.<br>모터 앞면–웜 끝 간격: 1.5mm</p><small>모터 축은 기존 명목 Ø1.2mm 표현입니다. 실제 축 지름과 출력된 구멍의 끼움은 출력 시험으로 확인합니다.</small><p><a href="worm-print.stl" download>웜 출력 STL · 구멍 Ø1.0</a></p></aside><div id="status">모델 불러오는 중…</div>''' +s[b:]
s=s.replace('d=170,target=new T.Vector3(-3,0,5)','d=120,target=new T.Vector3(-8,0,6)')
a=s.index('function update(');b=s.index("$('angle').onclick",a)
s=s[:a]+'''fetch('worm.json').then(r=>r.json()).then(data=>{let g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(data.vertices.flat(),3));g.setIndex(data.faces.flat());g=g.toNonIndexed();g.computeVertexNormals();scene.add(new T.Mesh(g,new T.MeshStandardMaterial({color:0xc19aef,roughness:.5,flatShading:true,side:T.DoubleSide})));render();$('status').textContent='드래그: 회전 · 휠 버튼 드래그: 이동 · 스크롤: 확대'}).catch(e=>$('status').textContent='불러오기 실패: '+e.message);
''' +s[b:]
(out/'preview.html').write_text(s)
(out.parent/'model-viewer'/'current.json').write_text(json.dumps({'model':out.name,'note':'모터와 Ø1.0 구멍 웜기어만 배치'},ensure_ascii=False))
