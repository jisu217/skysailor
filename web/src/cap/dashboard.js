const $=id=>document.getElementById(id);
const fields=[['shell_g','껍질 질량 g',4,.5,100],['ballast_g','무게추 질량 g',6,.5,100],['com_x_mm','무게중심 X mm',0,-100,100],['com_y_mm','무게중심 Y mm',0,-100,100],['com_z_mm','무게중심 Z mm',-40,-200,60],['height','시작 높이 m',5,.5,10],['tilt','초기 기울기 °',10,0,180],['wind_x','바람 X m/s',0,-3,3],['wind_y','바람 Y m/s',0,-3,3]];
for(const [key,label,value,min,max] of fields){const item=document.createElement('label');item.textContent=label;const input=document.createElement('input');Object.assign(input,{name:key,type:'number',value,min,max,step:'any',required:true});if(key.startsWith('com_')){input.removeAttribute('min');input.removeAttribute('max');}item.append(input);$('base-inputs').append(item);const option=new Option(label,key);$('variable').add(option);}
$('variable').value='com_z_mm';
const presets={shell_g:'2, 4, 8, 16',ballast_g:'2, 6, 12, 24',com_x_mm:'0, 5, 10, 20',com_y_mm:'0, 5, 10, 20',com_z_mm:'-80, -40, 0, 30',height:'1, 3, 5, 8',tilt:'0, 5, 15, 30',wind_x:'0, 0.5, 1, 2',wind_y:'0, 0.5, 1, 2'};
$('variable').onchange=()=>{$('values').value=presets[$('variable').value];};
let results=[],selected=-1,busy=false,sweepLabel='',sweepKey='';
const color=r=>r.parameters.rotation_damping?'#96dfc3':'#ff967f';
const svg=(content,w=760,h=260)=>`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="시뮬레이션 결과 그래프">${content}</svg>`;
function plotChart(){
 const key=$('metric').value,valid=results.filter(r=>!r.error);if(!valid.length){$('comparison-chart').textContent='계산 결과를 기다리고 있습니다.';return;}
 const xs=valid.map(r=>r.value),ys=valid.map(r=>r.summary[key]);let lo=Math.min(...xs),hi=Math.max(...xs);if(lo===hi){lo-=1;hi+=1;}const ymax=Math.max(...ys,1e-6)*1.1;
 const x=v=>62+(v-lo)/(hi-lo)*664,y=v=>215-v/ymax*185;let parts='';
 for(let i=0;i<=4;i++){const yy=215-i*185/4;parts+=`<path d="M62 ${yy}H726" stroke="#30424a"/><text x="8" y="${yy+4}">${(ymax*i/4).toFixed(2)}</text>`;}
 for(const value of [...new Set(xs)])parts+=`<text text-anchor="middle" x="${x(value)}" y="239">${value}</text>`;
 for(const r of valid){const index=results.indexOf(r);parts+=`<circle class="dot" data-index="${index}" cx="${x(r.value)}" cy="${y(r.summary[key])}" r="${index===selected?8:5}" fill="${color(r)}" stroke="${index===selected?'white':'#15222a'}" stroke-width="2"><title>${sweepLabel} ${r.value}, 감쇠 ${r.parameters.rotation_damping?'켜짐':'꺼짐'}: ${r.summary[key].toFixed(3)}</title></circle>`;}
 $('comparison-chart').innerHTML=svg(parts);$('comparison-chart').querySelectorAll('[data-index]').forEach(e=>e.onclick=()=>select(Number(e.dataset.index)));
}
function trace(id,getValue){
 const valid=results.filter(r=>!r.error);if(!valid.length)return;const xmax=Math.max(...valid.map(r=>r.summary.duration)),ymax=Math.max(1,...valid.flatMap(r=>r.frames.map(getValue)));const x=t=>45+t/xmax*300,y=v=>150-v/ymax*125;
 let content=`<path d="M45 20V150H350" fill="none" stroke="#526971"/><text x="6" y="25">${ymax.toFixed(1)}</text><text x="25" y="154">0</text><text x="45" y="175">0 s</text><text x="295" y="175">${xmax.toFixed(2)} s</text>`;
 for(const r of [...valid.filter(r=>r!==results[selected]),results[selected]].filter(Boolean)){content+=`<polyline fill="none" stroke="${color(r)}" stroke-opacity="${r===results[selected]?1:.18}" stroke-width="${r===results[selected]?2.5:1}" points="${r.frames.map(f=>`${x(f.t)},${y(getValue(f))}`).join(' ')}"/>`;}
 $(id).innerHTML=svg(content,380,190);
}
function select(index){selected=index;const r=results[index];if(!r||r.error)return;const label=`${sweepLabel} = ${r.value} · 감쇠 ${r.parameters.rotation_damping?'켜짐':'꺼짐'}`;$('selected-title').textContent=label;$('replay').href='/?'+new URLSearchParams(Object.entries(r.parameters).map(([k,v])=>[k,String(Number(v))]));document.querySelectorAll('#rows tr').forEach((row,i)=>row.classList.toggle('selected',i===index));plotChart();trace('height-plot',f=>f.com[2]);trace('tilt-plot',f=>f.tilt);}
function render(){
 $('rows').replaceChildren();results.forEach((r,i)=>{const row=document.createElement('tr');const cell=document.createElement('td');const button=document.createElement('button');button.textContent=`${sweepLabel} = ${r.value}`;button.disabled=Boolean(r.error);button.onclick=()=>select(i);cell.append(button);row.append(cell);const s=r.summary;const values=r.error?[r.parameters.rotation_damping?'켜짐':'꺼짐',r.error,'—','—','—','실패']:[r.parameters.rotation_damping?'켜짐':'꺼짐',s.duration.toFixed(2)+' s',s.max_tilt.toFixed(1)+'°',s.peak_spin_deg_s.toFixed(0)+'°/s',s.horizontal_distance.toFixed(3)+' m',s.termination==='ground'?'지면 도달':'8초 종료'];for(const value of values){const td=document.createElement('td');td.textContent=value;row.append(td);}$('rows').append(row);});
 const valid=results.filter(r=>!r.error);$('overview').innerHTML=`<div><small>완료 조건</small><strong>${valid.length}개</strong></div><div><small>최대 기울기 90° 초과</small><strong>${valid.filter(r=>r.summary.max_tilt>90).length}개</strong></div><div><small>지면 도달</small><strong>${valid.filter(r=>r.summary.termination==='ground').length}개</strong></div>`;
 $('export').disabled=!valid.length;if(selected<0&&valid.length)selected=results.indexOf(valid[0]);if(selected>=0)select(selected);else plotChart();
}
async function run(){
 if(busy||!$('compare-form').reportValidity())return;const variable=$('variable').value,field=fields.find(f=>f[0]===variable),raw=$('values').value.split(',').map(v=>v.trim()),values=[...new Set(raw.map(Number))];const modes=$('damping').value==='both'?[true,false]:[$('damping').value==='on'];
 if(raw.some(v=>!v)||values.some(v=>!Number.isFinite(v)||(!variable.startsWith('com_')&&(v<field[3]||v>field[4])))||values.length*modes.length>24){$('progress').textContent=`값은 ${field[3]} ~ ${field[4]} 범위이며, 감쇠 비교를 포함해 최대 24개 조건입니다.`;return;}
 const base=Object.fromEntries(fields.map(([k])=>[k,Number($('compare-form').elements[k].value)]));base.seconds=8;busy=true;$('compare').disabled=true;results=[];selected=-1;sweepLabel=field[1];sweepKey=variable;render();
 for(const value of values)for(const enabled of modes){const parameters={...base,[variable]:value,rotation_damping:enabled};$('progress').textContent=`${results.length+1} / ${values.length*modes.length} 계산 중…`;
 try{const response=await fetch('/api/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(parameters)});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));results.push({...data,value});}catch(error){results.push({parameters,value,error:error.message});}render();}
 busy=false;$('compare').disabled=false;$('progress').textContent=`${results.length}개 조건 계산 완료${results.some(r=>r.error)?' · 실패한 조건은 표를 확인하세요.':''}`;
}
$('compare-form').onsubmit=e=>{e.preventDefault();run();};$('metric').onchange=plotChart;
$('export').onclick=()=>{const header=[...fields.map(f=>f[0]),'rotation_damping','duration_s','max_tilt_deg','peak_spin_deg_s','horizontal_distance_m','termination'];const lines=[header.join(','),...results.filter(r=>!r.error).map(r=>[...fields.map(f=>r.parameters[f[0]]),r.parameters.rotation_damping,r.summary.duration,r.summary.max_tilt,r.summary.peak_spin_deg_s,r.summary.horizontal_distance,r.summary.termination].join(','))];const url=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='cap-comparison.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
run();
