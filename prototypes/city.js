// City-scale tactical view for ① 기기 성능 and ② 표적 판단, styled like the globe (EBS palette).
// The ground is flat (OSM roads, building footprints, water, parks; no building heights); only the
// domes and targets stand in the air, with stalks to the ground so altitude reads at a glance.
// Buildings are extruded from OSM heights (height, else levels × 3.3 m); buildings without either get a
// type/footprint estimate and are drawn fainter, so a guessed height never looks like a measured one.
// Coordinates: scenario ENU metres around the city anchor. three.js: x = east, y = up, z = −north.
// Map data © OpenStreetMap contributors, ODbL 1.0.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { TOK, TYPE, affiliation } from './symbols.js';
import { makeModel, makeDome, addModelLights } from './models.js';

const C = {
  ground: '#0a1426', water: '#040d1e', park: '#0d1f2c',
  wall: [0x16, 0x24, 0x3b], roof: [0x1d, 0x30, 0x4f], roofLine: '#3f6593', estRoofLine: '#28405e',
  minor: '#203a5a', mid: '#365b86', major: '#4f7fb4', grid: '#15263d',
  pop: '#a08660',
};
// overlay styling follows prototypes/symbology.html (symbols.js): line-only, colour = threat level
const LAYERS = { coverage: '관측 범위', rays: '방향선', fp: '낙하 예측', pop: '인구' };
const LAYER_DEFAULT = { nodes: { coverage: true, rays: true, fp: false, pop: false }, targets: { coverage: true, rays: false, fp: true, pop: false } };
const V = (e, n, up = 0) => new THREE.Vector3(e, up, -n);

function pairs(flat, out) {                               // polyline [x,y,x,y…] → segment pairs at y=0
  for (let i = 2; i < flat.length; i += 2) out.push(flat[i-2], 0, -flat[i-1], flat[i], 0, -flat[i+1]);
  return out;
}

function fillGeometry(rings) {                            // flat rings → one triangulated geometry
  const pos = [];
  for (const r of rings) {
    const pts = [];
    for (let i = 0; i < r.length; i += 2) pts.push(new THREE.Vector2(r[i], r[i+1]));
    if (pts.length > 2 && pts[0].equals(pts[pts.length-1])) pts.pop();
    if (pts.length < 3) continue;
    for (const [a, b, c] of THREE.ShapeUtils.triangulateShape(pts, [])) {
      for (const k of [a, b, c]) pos.push(pts[k].x, 0, -pts[k].y);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return g;
}

// extruded buildings → one geometry with baked wall shading (light from the north-west)
function buildingGeometry(list) {
  const pos = [], col = [], roof = [];
  const L = new THREE.Vector2(-0.6, 0.8).normalize();
  const [wr, wg, wb] = C.wall.map((v) => v/255), [rr, rg, rb] = C.roof.map((v) => v/255);
  for (const b of list) {
    const h = b[0], pts = [];
    for (let i = 2; i < b.length; i += 2) pts.push(new THREE.Vector2(b[i], b[i+1]));
    if (pts.length > 2 && pts[0].equals(pts[pts.length-1])) pts.pop();
    if (pts.length < 3) continue;
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i], q = pts[(i+1)%pts.length], n = new THREE.Vector2(q.y-p.y, p.x-q.x).normalize();
      const k = 0.62+0.38*Math.abs(n.dot(L));
      for (const [x, y, z] of [[p.x, 0, p.y], [q.x, 0, q.y], [q.x, h, q.y], [p.x, 0, p.y], [q.x, h, q.y], [p.x, h, p.y]]) {
        pos.push(x, y, -z);
        const top = y > 0 ? 1 : 0.55;                              // walls darken toward the street
        col.push(wr*k*top, wg*k*top, wb*k*top);
      }
      roof.push(p.x, h, -p.y, q.x, h, -q.y);
    }
    for (const [a, b2, c] of THREE.ShapeUtils.triangulateShape(pts, [])) {
      for (const k of [a, b2, c]) { pos.push(pts[k].x, h, -pts[k].y); col.push(rr, rg, rb); }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  const r = new THREE.BufferGeometry();
  r.setAttribute('position', new THREE.Float32BufferAttribute(roof, 3));
  return { mass: g, roof: r };
}

// MGRS grid reference (WGS84 UTM, 1 m); checked against the mgrs reference library
export function mgrs(lat, lon) {
  const a = 6378137, f = 1/298.257223563, e2 = f*(2-f), ep2 = e2/(1-e2), k0 = 0.9996, D = Math.PI/180;
  const zone = Math.floor((lon+180)/6)+1, l0 = ((zone-1)*6-180+3)*D, p = lat*D;
  const N = a/Math.sqrt(1-e2*Math.sin(p)**2), T = Math.tan(p)**2, Cc = ep2*Math.cos(p)**2, A = Math.cos(p)*(lon*D-l0);
  const e4 = e2*e2, e6 = e4*e2;
  const M = a*((1-e2/4-3*e4/64-5*e6/256)*p-(3*e2/8+3*e4/32+45*e6/1024)*Math.sin(2*p)+(15*e4/256+45*e6/1024)*Math.sin(4*p)-(35*e6/3072)*Math.sin(6*p));
  const E = k0*N*(A+(1-T+Cc)*A**3/6+(5-18*T+T*T+72*Cc-58*ep2)*A**5/120)+500000;
  let No = k0*(M+N*Math.tan(p)*(A*A/2+(5-T+9*Cc+4*Cc*Cc)*A**4/24+(61-58*T+T*T+600*Cc-330*ep2)*A**6/720));
  if (lat < 0) No += 1e7;
  const band = 'CDEFGHJKLMNPQRSTUVWX'[Math.min(19, Math.floor((lat+80)/8))];
  const colL = ['STUVWXYZ', 'ABCDEFGH', 'JKLMNPQR'][zone%3][Math.floor(E/1e5)-1];
  const rowL = 'ABCDEFGHJKLMNPQRSTUV'[(Math.floor(No/1e5)+(zone%2 ? 0 : 5))%20];
  const d = (v) => String(Math.floor(v%1e5)).padStart(5, '0');
  return `${zone}${band} ${colL}${rowL} ${d(E)} ${d(No)}`;
}

const flatMat = (color, order, opacity = 1) => {
  const m = new THREE.MeshBasicMaterial({ color, toneMapped: false, depthTest: false, depthWrite: false, transparent: opacity < 1, opacity, side: THREE.DoubleSide });
  return { m, order };
};

export async function createCity({ host, onPick, onNode, base = 'data/city/' }) {
  // DOM: one wrap (canvas + labels + toolbar) moved between the ① and ② stages
  const wrap = document.createElement('div');
  wrap.className = 'city-wrap';
  wrap.innerHTML = `<canvas class="city-canvas" tabindex="0" aria-label="도시 상황도: 드래그 회전, Shift·오른쪽 드래그 이동, 휠 확대, 방향키 회전"></canvas>
    <div class="city-maplabels"></div>
    <div class="city-labels"></div>
    <div class="city-tools">
      <span class="city-name"></span>
      <div class="view-switch" role="group" aria-label="보기 각도"><button type="button" data-tilt="top" aria-pressed="false">위에서</button><button type="button" data-tilt="tilt" aria-pressed="true">기울여</button></div>
      <button type="button" class="city-reset" aria-label="작전 지역 전체 보기">↺</button>
    </div>
    <div class="city-layers" role="group" aria-label="레이어">${Object.entries(LAYERS).map(([k, v]) => `<button type="button" data-layer="${k}" aria-pressed="false">${v}</button>`).join('')}
    </div>
    <div class="city-compass" aria-hidden="true"><i class="n"></i><i class="w"></i><span class="wtxt num"></span></div>
    <div class="city-foot"><div class="city-scale"><i></i><span class="num"></span></div><span class="city-coord num"></span></div>
    <div class="city-legend"></div>
    <div class="city-attr">© OpenStreetMap contributors</div>`;
  host.append(wrap);
  const canvas = wrap.querySelector('canvas'), labels = wrap.querySelector('.city-labels'), mapLabels = wrap.querySelector('.city-maplabels');

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 5, 60000);
  const controls = new OrbitControls(camera, canvas);
  Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, screenSpacePanning: false, minDistance: 150, maxDistance: 12000, maxPolarAngle: 1.48, zoomSpeed: 0.8, rotateSpeed: 0.6, keyPanSpeed: 0 });
  // same feel as the globe: drag rotates (all the way round, tilt to near the horizon);
  // Shift/Ctrl/⌘ + drag or right drag pans; two fingers zoom and pan
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  canvas.addEventListener('keydown', (e) => {
    const az = { ArrowLeft: 0.12, ArrowRight: -0.12 }[e.key], pol = { ArrowUp: -0.08, ArrowDown: 0.08 }[e.key];
    if (az === undefined && pol === undefined) return;
    const off = camera.position.clone().sub(controls.target), sph = new THREE.Spherical().setFromVector3(off);
    sph.theta += az || 0; sph.phi = THREE.MathUtils.clamp(sph.phi+(pol || 0), 0.001, controls.maxPolarAngle);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(sph));
    e.preventDefault();
  });

  const lineMats = [];
  const fat = (positions, color, width, order, opacity = 1) => {
    const m = new LineMaterial({ color, linewidth: width, worldUnits: false, toneMapped: false, depthTest: false, depthWrite: false, transparent: true, opacity });
    lineMats.push(m);
    const o = new LineSegments2(new LineSegmentsGeometry().setPositions(positions), m);
    o.renderOrder = order;
    return o;
  };

  // ---- static city layers ----
  const cities = {};
  let city = null, cityKey = null;
  async function loadCity(key) {
    if (cities[key]) return cities[key];
    const d = await fetch(`${base}${key}.json`).then((r) => { if (!r.ok) throw new Error(`${key}: ${r.status}`); return r.json(); });
    const g = new THREE.Group();
    const add = (geo, { m, order }) => { const o = new THREE.Mesh(geo, m); o.renderOrder = order; g.add(o); };
    const S = d.half*3;
    add(new THREE.PlaneGeometry(S*2, S*2).rotateX(-Math.PI/2), flatMat(C.ground, 0));
    add(fillGeometry(d.water), flatMat(C.water, 1));
    add(fillGeometry(d.parks), flatMat(C.park, 2));
    for (const [cls, color, w, order] of [['minor', C.minor, 0.8, 3], ['mid', C.mid, 1.3, 4], ['major', C.major, 2.0, 5]]) {
      const p = []; for (const r of d.roads[cls]) pairs(r, p);
      if (p.length) g.add(fat(p, color, w, order));
    }
    // buildings: measured heights solid-ish, estimated ones fainter
    const mats = [];
    for (const [est, opacity, line, lineOp, order] of [[0, 0.62, C.roofLine, 0.6, 6], [1, 0.3, C.estRoofLine, 0.4, 7]]) {
      const { mass, roof } = buildingGeometry(d.buildings.filter((b) => b[1] === est));
      const mm = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity, side: THREE.DoubleSide, toneMapped: false, depthWrite: true });
      const lm = new THREE.LineBasicMaterial({ color: line, transparent: true, opacity: lineOp, toneMapped: false });
      const m = new THREE.Mesh(mass, mm), l = new THREE.LineSegments(roof, lm);
      m.renderOrder = order; l.renderOrder = order;
      g.add(m, l);
      mats.push({ mm, lm, opacity, lineOp });
    }
    const hs = d.height_stats, total = hs.measured+hs.levels+hs.estimated;
    cities[key] = { group: g, data: d, mats, measuredShare: (hs.measured+hs.levels)/total };
    return cities[key];
  }

  // ---- dynamic overlay ----
  const dyn = new THREE.Group();
  scene.add(dyn);
  // 3D target models: own scene, drawn after the city with a cleared depth buffer so buildings never hide
  // them; constant on-screen size; positions eased between pipeline updates
  const modelScene = new THREE.Scene();
  addModelLights(modelScene);
  const models = new Map();
  const DIM = 0.35;                                    // opacity of the other domes while one is selected
  const MODEL_PX = { balloon: 40, drone: 26, bird: 32, unknown: 26, dome: 46 };
  const domes = new Map();
  function syncDomes(nodes, sel) {
    const seen = new Set();
    for (const n of nodes) {
      seen.add(n.id);
      let m = domes.get(n.id);
      if (!m) { const obj = makeDome(); modelScene.add(obj); m = { obj, cls: 'dome', target: new THREE.Vector3() }; domes.set(n.id, m); }
      m.target.copy(V(n.e, n.n, n.alt)); m.obj.position.copy(m.target);
      m.obj.userData.setStatus(n.q > 0.8 ? TOK.friend : TOK.q(n.q));
      m.obj.userData.setTilt(Math.min(60, n.tilt || 0)*Math.PI/180);
      const dim = sel && sel !== n.id ? DIM : 1;
      if (m.dim !== dim) { m.dim = dim; m.obj.traverse((o) => { if (o.material) { o.material.transparent = true; o.material.opacity = (o.material.userData.base ??= o.material.opacity)*dim; } }); }
    }
    for (const [id, m] of domes) if (!seen.has(id)) { modelScene.remove(m.obj); domes.delete(id); }
  }
  function syncModels(tracks) {
    const seen = new Set();
    for (const t of tracks) {
      seen.add(t.id);
      let m = models.get(t.id);
      if (!m || m.cls !== t.cls) {
        if (m) modelScene.remove(m.obj);
        const obj = makeModel(t.cls);
        obj.position.copy(V(t.e, t.n, t.alt));
        modelScene.add(obj);
        m = { obj, cls: t.cls, target: new THREE.Vector3() }; models.set(t.id, m);
      }
      m.target.copy(V(t.e, t.n, t.alt));
      if (Math.hypot(t.vx, t.vy) > 0.5 && t.cls !== 'balloon') m.yaw = Math.atan2(t.vy, t.vx);
      m.obj.userData.led?.material.color.set(TOK.level[t.level] || TOK.level.LOW);
      const fade = t.status === 'tentative' ? 0.45 : 1;
      if (m.fade !== fade) { m.fade = fade; m.obj.traverse((o) => { if (o.material) { o.material.transparent = true; o.material.opacity = (o.material.userData.base ??= o.material.opacity)*fade; } }); }
    }
    for (const [id, m] of models) if (!seen.has(id)) { modelScene.remove(m.obj); models.delete(id); }
  }
  function stepModels(now) {
    const H = canvas.clientHeight, k = 2*Math.tan(camera.fov*Math.PI/360)/Math.max(1, H), t = now/1000;
    for (const m of domes.values()) {
      m.obj.scale.setScalar(MODEL_PX.dome*camera.position.distanceTo(m.obj.position)*k/m.obj.userData.size);
      m.obj.userData.animate?.(t);
    }
    for (const m of models.values()) {
      if (m.obj.position.distanceTo(m.target) > 60) m.obj.position.copy(m.target); else m.obj.position.lerp(m.target, 0.3);
      if (m.yaw !== undefined) m.obj.rotation.y += Math.atan2(Math.sin(m.yaw-m.obj.rotation.y), Math.cos(m.yaw-m.obj.rotation.y))*0.15;
      const d = camera.position.distanceTo(m.obj.position);
      m.obj.scale.setScalar(MODEL_PX[m.cls]*d*k/m.obj.userData.size);
      m.obj.userData.animate?.(t);
    }
  }
  const popTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const x = c.getContext('2d'), gr = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  })();
  function clearDyn() {
    pulsing = [];
    for (const o of [...dyn.children]) {
      dyn.remove(o);
      o.geometry?.dispose();
      if (o.material) { const i = lineMats.indexOf(o.material); if (i >= 0) lineMats.splice(i, 1); o.material.dispose(); }
    }
  }
  const circle = (e, n, r, up = 0, seg = 96) => {
    const p = [];
    for (let i = 0; i < seg; i++) {
      const a0 = i/seg*Math.PI*2, a1 = (i+1)/seg*Math.PI*2;
      p.push(e+r*Math.cos(a0), up, -(n+r*Math.sin(a0)), e+r*Math.cos(a1), up, -(n+r*Math.sin(a1)));
    }
    return p;
  };
  const dashed = (a, b, dash = 12, gap = 10) => {      // segment a→b split into dashes (world metres)
    const p = [], L = a.distanceTo(b), d = new THREE.Vector3().subVectors(b, a).normalize();
    for (let s = 0; s < L; s += dash+gap) {
      const s1 = Math.min(L, s+dash);
      p.push(...a.clone().addScaledVector(d, s).toArray(), ...a.clone().addScaledVector(d, s1).toArray());
    }
    return p;
  };
  const disc = (e, n, r, color, opacity, order, map = null) => {
    const o = new THREE.Mesh(new THREE.CircleGeometry(r, 64).rotateX(-Math.PI/2),
      new THREE.MeshBasicMaterial({ color, map, transparent: true, opacity, depthTest: false, depthWrite: false, toneMapped: false }));
    o.position.set(e, 0, -n); o.renderOrder = order; dyn.add(o);
  };
  const add3d = (positions, color, width, opacity = 1, order = 20) => { if (positions.length) dyn.add(fat(positions, color, width, order, opacity)); };

  // HTML markers (crisp at any zoom, clickable), keyed by id
  const marks = new Map();
  function mark(key, cls, html, world, onClick) {
    let m = marks.get(key);
    if (!m) {
      const el = document.createElement(onClick ? 'button' : 'div');
      if (onClick) { el.type = 'button'; el.addEventListener('click', (ev) => { ev.stopPropagation(); m.onClick?.(); }); }
      labels.append(el);
      m = { el }; marks.set(key, m);
    }
    m.onClick = onClick; m.world = world; m.seen = true;
    if (m.cls !== cls) { m.el.className = cls; m.cls = cls; }
    if (m.html !== html) { m.el.innerHTML = html; m.html = html; m.w = 0; m.tw = 0; m.dy = 0; }
  }
  const scr = new THREE.Vector3();
  function placeMarks() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const placed = [];
    for (const m of marks.values()) {
      scr.copy(m.world).project(camera);
      const vis = scr.z < 1 && Math.abs(scr.x) < 1.2 && Math.abs(scr.y) < 1.2;
      m.el.hidden = !vis;
      if (vis) { m.xy = [(scr.x+1)/2*w, (1-scr.y)/2*h]; m.el.style.transform = `translate(${m.xy[0].toFixed(1)}px,${m.xy[1].toFixed(1)}px)`; }
    }
    // de-clutter: threat-ordered target tags step up/down when they would overlap; dome labels give way
    const tracks = [...marks.values()].filter((m) => !m.el.hidden && m.cls?.startsWith('city-track'))
      .sort((x, y) => LVW(y.cls)-LVW(x.cls));
    for (const m of tracks) {
      const tag = m.el.querySelector('.tag'); if (!tag) continue;
      if (!m.tw) { m.tw = tag.offsetWidth; m.th = tag.offsetHeight; }
      const x0 = m.xy[0]+35, cy = m.xy[1];
      let dy = 0;
      for (const d of [0, -24, 24, -48, 48, -72, 72]) {
        const box = [x0, cy+d-m.th/2, x0+m.tw, cy+d+m.th/2];
        if (!placed.some((o) => box[0] < o[2] && box[2] > o[0] && box[1] < o[3] && box[3] > o[1])) { dy = d; placed.push(box); break; }
      }
      placed.push([m.xy[0]-23, cy-23, m.xy[0]+23, cy+23]);
      if (m.dy !== dy) { m.dy = dy; tag.style.transform = dy ? `translateY(${dy}px)` : ''; m.el.querySelector('.leader').style.transform = dy ? `rotate(${Math.atan2(dy, 12)*180/Math.PI}deg) scaleX(${Math.hypot(dy, 12)/12})` : ''; }
    }
    for (const m of marks.values()) {
      if (m.el.hidden || !m.cls?.startsWith('city-node')) continue;
      const lab = m.el.querySelector('.nlabel'), r = [m.xy[0]+14, m.xy[1]-8, m.xy[0]+100, m.xy[1]+8];
      const quiet = placed.some((o) => r[0] < o[2] && r[2] > o[0] && r[1] < o[3] && r[3] > o[1]);
      if (lab && lab.hidden !== quiet) lab.hidden = quiet;
    }
  }
  const LVW = (cls) => ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].findIndex((l) => cls.includes('lvl-'+l));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

  // ---- map labels (roads, stations, landmarks, neighbourhoods) with overlap culling ----
  let mapLabelList = [];
  function setMapLabels(d) {
    mapLabels.replaceChildren();
    const prio = { station: 0, building: 1, road: 2, place: 3 };
    mapLabelList = d.labels.map((l) => {
      const el = document.createElement('div');
      el.className = 'ml ml-'+l.k;
      el.innerHTML = l.k === 'building' ? `${esc(l.t)} <small class="num">${Math.round(l.h)} m</small>` : l.k === 'station' ? `<i></i>${esc(l.t)}` : esc(l.t);
      mapLabels.append(el);
      const a = l.k === 'road' ? V(l.p[0], l.p[1]) : V(l.p[0], l.p[1], l.k === 'building' ? l.h : 0);
      const b = l.k === 'road' ? V(l.p[2], l.p[3]) : null;
      const w = (l.t.length+(l.k === 'building' ? 6 : 0))*(/[가-힣]/.test(l.t) ? 11 : 6.6)+12;
      return { ...l, el, a, b, w, prio: prio[l.k] };
    }).sort((x, y) => x.prio-y.prio);
  }
  const pa = new THREE.Vector3(), pb = new THREE.Vector3();
  function placeMapLabels(mpp) {
    const w = canvas.clientWidth, h = canvas.clientHeight, boxes = [];
    // keep clear of the toolbar, legend, scale/coords, compass and every dome/target marker
    const wr = wrap.getBoundingClientRect();
    for (const sel of ['.city-tools', '.city-legend', '.city-foot', '.city-compass', '.city-layers']) {
      for (const e of wrap.querySelectorAll(sel)) { const r = e.getBoundingClientRect(); boxes.push([r.left-wr.left-4, r.top-wr.top-4, r.right-wr.left+4, r.bottom-wr.top+4]); }
    }
    boxes[0][0] = 0; boxes[0][2] = w;                          // toolbar row spans the width
    for (const m of marks.values()) {
      if (m.el.hidden || !m.xy) continue;
      if (!m.w) m.w = m.el.offsetWidth || 40;
      boxes.push([m.xy[0]-16, m.xy[1]-16, m.xy[0]+m.w, m.xy[1]+16]);
    }
    for (const l of mapLabelList) {
      let show = !(l.k === 'road' && mpp > 3.5) && !(l.k === 'place' && mpp < 0.6);
      let x, y, ang = 0;
      if (show) {
        pa.copy(l.a).project(camera);
        if (l.b) { pb.copy(l.b).project(camera); x = ((pa.x+pb.x)/2+1)/2*w; y = (1-(pa.y+pb.y)/2)/2*h; ang = Math.atan2(-(pb.y-pa.y)*h, (pb.x-pa.x)*w)*180/Math.PI; if (ang > 90) ang -= 180; if (ang < -90) ang += 180; }
        else { x = (pa.x+1)/2*w; y = (1-pa.y)/2*h; }
        show = pa.z < 1 && x > 0 && x < w && y > 30 && y < h-20;
      }
      if (show) {
        const r = Math.abs(ang*Math.PI/180), bw = l.w*Math.cos(r)+14*Math.sin(r), bh = l.w*Math.sin(r)+14*Math.cos(r);
        const box = [x-bw/2, y-bh/2, x+bw/2, y+bh/2];
        show = !boxes.some((o) => box[0] < o[2] && box[2] > o[0] && box[1] < o[3] && box[3] > o[1]);
        if (show) { boxes.push(box); l.el.style.transform = `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) translate(-50%,-50%) rotate(${ang.toFixed(1)}deg)`; }
      }
      if (l.el.hidden !== !show) l.el.hidden = !show;
    }
  }
  // metres per pixel at the screen centre → scale bar
  const ray = new THREE.Raycaster(), ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), ndc = new THREE.Vector2();
  function groundAt(px, py) {
    ndc.set(px/canvas.clientWidth*2-1, -(py/canvas.clientHeight*2-1));
    ray.setFromCamera(ndc, camera);
    return ray.ray.intersectPlane(ground, new THREE.Vector3());
  }
  const scaleEl = wrap.querySelector('.city-scale');
  function updateScale() {
    const cx = canvas.clientWidth/2, cy = canvas.clientHeight*0.6;
    const p = groundAt(cx, cy), q = groundAt(cx+100, cy);
    if (!p || !q) return 1;
    const mpp = p.distanceTo(q)/100;
    const nice = [10, 20, 50, 100, 200, 300, 500, 1000, 2000, 5000].filter((m) => m/mpp <= 130).pop() || 10;
    scaleEl.querySelector('i').style.width = `${(nice/mpp).toFixed(0)}px`;
    scaleEl.querySelector('span').textContent = nice >= 1000 ? `${nice/1000} km` : `${nice} m`;
    return mpp;
  }
  // cursor → ground → lat/lon/MGRS
  const coordEl = wrap.querySelector('.city-coord');
  function toLatLon(e, n) {
    const [lat0, lon0] = city.data.origin;
    return [lat0+n/111320, lon0+e/(111320*Math.cos(lat0*Math.PI/180))];
  }
  function showCoord(e, n, prefix = '') {
    if (!city) return;
    const [lat, lon] = toLatLon(e, n);
    coordEl.textContent = `${prefix}${Math.abs(lat).toFixed(5)}°${lat >= 0 ? 'N' : 'S'} ${Math.abs(lon).toFixed(5)}°${lon >= 0 ? 'E' : 'W'} · MGRS ${mgrs(lat, lon)}`;
  }
  canvas.addEventListener('pointermove', (ev) => {
    const r = canvas.getBoundingClientRect(), p = groundAt(ev.clientX-r.left, ev.clientY-r.top);
    if (p) showCoord(p.x, -p.z, '커서 ');
  });
  canvas.addEventListener('pointerleave', () => showCoord(controls.target.x, -controls.target.z, '중심 '));

  let lastState = null, lastOpt = {}, lastBuild = 0, bounds = null, pulsing = [];
  const layers = JSON.parse(JSON.stringify(LAYER_DEFAULT));
  let layerKey = 'targets';
  function syncLayerButtons() {
    for (const b of wrap.querySelectorAll('[data-layer]')) b.setAttribute('aria-pressed', String(!!layers[layerKey][b.dataset.layer]));
  }
  for (const b of wrap.querySelectorAll('[data-layer]')) b.onclick = () => {
    layers[layerKey][b.dataset.layer] = !layers[layerKey][b.dataset.layer]; syncLayerButtons(); lastBuild = 0;
  };
  const dashedCircle = (e, n, r, up = 0, seg = 120) => {   // every other segment of a circle
    const p = [];
    for (let i = 0; i < seg; i += 2) {
      const a0 = i/seg*Math.PI*2, a1 = (i+1)/seg*Math.PI*2;
      p.push(e+r*Math.cos(a0), up, -(n+r*Math.sin(a0)), e+r*Math.cos(a1), up, -(n+r*Math.sin(a1)));
    }
    return p;
  };
  const LV = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
  const fmtS = (s) => (isFinite(s) ? (s >= 60 ? `${Math.floor(s/60)}m${String(Math.round(s%60)).padStart(2, '0')}s` : `${Math.round(s)} s`) : '—');

  function build(st, opt) {
    clearDyn();
    for (const m of marks.values()) m.seen = false;
    const L = layers[opt.screen] || layers.targets, top = st.bounds;
    // 100 m grid over the operating area
    const step = Math.max(top.w, top.h) > 4000 ? 1000 : 100, gp = [];
    for (let x = Math.floor(top.e0/step)*step; x <= top.e1; x += step) gp.push(x, 0, -top.n0, x, 0, -top.n1);
    for (let y = Math.floor(top.n0/step)*step; y <= top.n1; y += step) gp.push(top.e0, 0, -y, top.e1, 0, -y);
    add3d(gp, C.grid, 0.6, 1, 8);
    if (L.pop) for (const p of st.pop) disc(p.e, p.n, p.s*2, C.pop, 0.3*p.a, 9, popTex);

    // protected zones: thin double ring; turns to the threat colour of an approaching HIGH+ track
    for (const z of st.zones) {
      const threats = st.tracks.filter((t) => t.zone === z.id && LV.indexOf(t.level) >= 2).sort((x, y) => LV.indexOf(y.level)-LV.indexOf(x.level) || x.tti-y.tti);
      const th = threats[0], col = th ? TOK.level[th.level] : TOK.zone;
      const outer = fat(circle(z.e, z.n, z.r, 0, 128), col, th ? 1.8 : 1.2, 16, 0.95);
      dyn.add(outer);
      if (th) pulsing.push(outer.material);
      add3d(dashedCircle(z.e, z.n, z.r*0.92, 0, 140), col, 0.8, 0.55, 16);
      if (tilt !== 'top') add3d(circle(z.e, z.n, z.r, 300, 96), col, 0.8, 0.22, 16);   // ceiling, faint
      const text = th ? `${z.code} · ${th.id} TTI ${fmtS(th.tti)}` : `${z.code} · ${z.name}`;
      mark('z:'+z.id, 'city-zonetag'+(th ? ' alert' : ''), `<span style="color:${col}">${esc(text)}</span>`, V(z.e, z.n+z.r, 0));
    }

    // own sensors: coverage (dashed, blue unless degraded), stalk, friendly symbol; a selected dome (①) dims the others
    const ns = opt.screen === 'nodes' ? opt.nsel : null, dimOf = (id) => (ns && ns !== id ? DIM : 1);
    for (const n of st.nodes) {
      const k = dimOf(n.id), on = ns === n.id;
      if (L.coverage) add3d(dashedCircle(n.e, n.n, n.R, 0, 160), TOK.q(n.q), opt.screen === 'nodes' ? (on ? 1.8 : 1.2) : 0.9, (opt.screen === 'nodes' ? 0.8 : 0.45)*k, 12);
      if (on) disc(n.e, n.n, n.R, TOK.q(n.q), 0.07, 11);
      add3d([n.e, 0, -n.n, n.e, n.alt, -n.n], TOK.friend, 0.8, 0.35*k);
      mark('n:'+n.id, 'city-node'+(on ? ' sel' : k < 1 ? ' dim' : ''), `<span class="hit"></span><span class="nlabel num">${esc(n.id)} · ${Math.round(n.q*100)}%</span>`, V(n.e, n.n, n.alt), () => onNode?.(n.id));
    }
    if (L.rays) for (const r of st.rays) {
      const a = V(r.e, r.n, r.alt);
      const b2 = a.clone().add(new THREE.Vector3(Math.sin(r.az)*Math.cos(r.el), Math.sin(r.el), -Math.cos(r.az)*Math.cos(r.el)).multiplyScalar(r.L));
      add3d(dashed(a, b2, 10, 14), TOK.ray, 0.8, 0.28*dimOf(r.node));
    }
    if (opt.truth) for (const o of st.truths) mark('o:'+o.id, 'city-truth', '', V(o.e, o.n, o.alt || 0));

    // tracks: stalk with altitude ticks, ground trace, velocity, symbol + data tag
    for (const t of st.tracks) {
      const col = TOK.level[t.level] || TOK.level.LOW, p = V(t.e, t.n, t.alt), sel = opt.sel === t.id;
      add3d([t.e, 0, -t.n, t.e, t.alt, -t.n], col, 0.9, 0.5);
      const ticks = [];
      for (let a = 50; a < t.alt; a += 50) ticks.push(t.e-(a%100 ? 3 : 7), a, -t.n, t.e+(a%100 ? 3 : 7), a, -t.n);
      add3d(ticks, col, 0.9, 0.6);
      disc(t.e, t.n, 3.5, col, 0.55, 13);
      if (t.hist.length > 1) { const h = []; for (let i = 1; i < t.hist.length; i++) h.push(t.hist[i-1][0], 0, -t.hist[i-1][1], t.hist[i][0], 0, -t.hist[i][1]); add3d(h, col, 1, 0.3, 14); }
      if (Math.hypot(t.vx, t.vy) > 0.3) add3d([...p.toArray(), t.e+t.vx*15, t.alt, -(t.n+t.vy*15)], col, 1.4, 0.85);
      if (L.fp && t.fp && (LV.indexOf(t.level) >= 1 || sel)) {
        const g0 = V(t.fp.e, t.fp.n, 0);
        add3d(dashed(p, g0, 3, 9), col, 1, 0.7);
        add3d(circle(t.fp.e, t.fp.n, t.fp.r, 0, 96), col, 1, 0.75, 12);
        const c = Math.max(6, t.fp.r*0.12);
        add3d([t.fp.e-c, 0, -t.fp.n, t.fp.e+c, 0, -t.fp.n, t.fp.e, 0, -(t.fp.n-c), t.fp.e, 0, -(t.fp.n+c)], col, 1.4, 0.95, 13);
        mark('f:'+t.id, 'city-fptag', `<span style="color:${col}">낙하 예상 · 반경 ${Math.round(t.fp.r)} m${t.fp.fall ? ` · ${fmtS(t.fp.fall)}` : ''}</span>`, V(t.fp.e, t.fp.n-t.fp.r, 0));
      }
      const spd = Math.hypot(t.vx, t.vy);
      const af = affiliation(t), chip = af === 'hostile' ? `<b class="chip" style="background:${col}">의심</b>` : '';
      const line1 = `${chip}${esc(t.id)} <em>│</em> <b class="ty" style="color:${TOK.type[t.cls] || TOK.type.unknown}">${TYPE[t.cls] || '?'}</b> <em>│</em> ${Math.round(t.alt)} m <em>│</em> ${t.permitted ? 'RID 허가' : `${spd.toFixed(0)} m/s`}`;
      const line2 = sel ? `<span class="l2">${t.zoneCode ? `${t.zoneCode} · TTI ${fmtS(t.tti)}` : '보호구역 접근 없음'} · ${t.rid ? `RID ${esc(t.rid)}` : 'Remote ID 없음'}</span>` : '';
      mark('t:'+t.id, `city-track lvl-${t.level}${sel ? ' sel' : ''}`,
        `<span class="hit"></span><span class="leader" style="background:${col}"></span><span class="tag" style="border-left-color:${col}"><span>${line1}</span>${line2}</span>`, p, () => onPick?.(t.id));
    }
    syncModels(st.tracks);
    syncDomes(st.nodes, ns);
    for (const [k, m] of marks) if (!m.seen) { m.el.remove(); marks.delete(k); }
    // compass + wind
    windBearing = Math.atan2(st.wind.x, st.wind.y);
    wrap.querySelector('.wtxt').textContent = `바람 ${Math.hypot(st.wind.x, st.wind.y).toFixed(1)} m/s`;
    if (!bounds) { bounds = top; fit(false); }
  }
  let windBearing = 0;
  function updateCompass() {
    const th = controls.getAzimuthalAngle()*180/Math.PI;     // screen-up heading is −azimuth
    wrap.querySelector('.city-compass .n').style.transform = `rotate(${th}deg)`;
    wrap.querySelector('.city-compass .w').style.transform = `rotate(${windBearing*180/Math.PI+th}deg)`;
  }

  // ---- camera ----
  let tilt = 'tilt', flight = null;
  function viewFor(mode) {
    const b = bounds || { e0: -600, e1: 600, n0: -600, n1: 600, w: 1200, h: 1200 };
    const cx = (b.e0+b.e1)/2, cy = (b.n0+b.n1)/2, span = Math.max(b.w, b.h*camera.aspect)*0.62;
    const dist = Math.max(400, span/Math.tan(camera.fov*Math.PI/360)/camera.aspect*1.05);
    const polar = mode === 'top' ? 0.001 : 0.85, az = controls.getAzimuthalAngle();
    const target = new THREE.Vector3(cx, 0, -cy);
    const pos = target.clone().add(new THREE.Vector3(Math.sin(polar)*Math.sin(az), Math.cos(polar), Math.sin(polar)*Math.cos(az)).multiplyScalar(dist));
    return { target, pos };
  }
  function fit(animate = true) {
    const v = viewFor(tilt);
    if (!animate) { controls.target.copy(v.target); camera.position.copy(v.pos); controls.update(); return; }
    flight = { t0: performance.now(), from: { p: camera.position.clone(), t: controls.target.clone() }, to: v };
  }
  function fadeBuildings() {
    for (const c of Object.values(cities)) for (const m of c.mats) {
      m.mm.opacity = m.opacity*(tilt === 'top' ? 0.45 : 1); m.lm.opacity = m.lineOp*(tilt === 'top' ? 0.7 : 1);
    }
  }
  function setTilt(mode) {
    tilt = mode; fadeBuildings();
    for (const b of wrap.querySelectorAll('[data-tilt]')) b.setAttribute('aria-pressed', String(b.dataset.tilt === mode));
    const off = camera.position.clone().sub(controls.target), d = off.length();
    const az = controls.getAzimuthalAngle(), polar = mode === 'top' ? 0.001 : 0.85;
    const pos = controls.target.clone().add(new THREE.Vector3(Math.sin(polar)*Math.sin(az), Math.cos(polar), Math.sin(polar)*Math.cos(az)).multiplyScalar(d));
    lastBuild = 0;
    flight = { t0: performance.now(), from: { p: camera.position.clone(), t: controls.target.clone() }, to: { pos, target: controls.target.clone() } };
  }
  for (const b of wrap.querySelectorAll('[data-tilt]')) b.onclick = () => setTilt(b.dataset.tilt);
  wrap.querySelector('.city-reset').onclick = () => fit(true);

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    camera.aspect = w/h; camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    for (const m of lineMats) m.resolution.set(w, h);
  }
  new ResizeObserver(resize).observe(canvas);

  let active = false;
  renderer.setAnimationLoop(() => {
    if (!active) return;
    if (flight) {
      const t = Math.min(1, (performance.now()-flight.t0)/900), k = t*t*(3-2*t);
      camera.position.lerpVectors(flight.from.p, flight.to.pos, k);
      controls.target.lerpVectors(flight.from.t, flight.to.target, k);
      camera.lookAt(controls.target);
      if (t >= 1) flight = null;
    }
    controls.update();
    const now = performance.now();
    if (lastState && now-lastBuild > 200) { build(lastState, lastOpt); lastBuild = now; lastState = null; }
    for (const m of pulsing) m.opacity = 0.45+0.5*(0.5+0.5*Math.cos(now/1400*Math.PI*2));
    for (const m of lineMats) m.resolution.set(canvas.clientWidth, canvas.clientHeight);
    stepModels(now);
    renderer.autoClear = false;
    renderer.clear();
    renderer.render(scene, camera);
    renderer.clearDepth();
    renderer.render(modelScene, camera);
    placeMarks();
    if (city) placeMapLabels(updateScale());
    updateCompass();
  });

  return {
    wrap,
    async setCity(key) {
      if (key === cityKey) return;
      const c = await loadCity(key);
      if (city) scene.remove(city.group);
      city = c; cityKey = key; scene.add(c.group);
      c.group.renderOrder = 0;
      wrap.querySelector('.city-name').textContent = c.data.name;
      wrap.querySelector('.city-name').title = `${c.data.anchor} 기준`;
      setMapLabels(c.data); fadeBuildings(); syncLayerButtons();
      const pct = Math.round(c.measuredShare*100);
      const lg = wrap.querySelector('.city-legend');
      lg.innerHTML = `<span><i class="m"></i>건물 높이 실측 ${pct}%</span><a href="symbology.html" target="_blank" rel="noopener" title="표시 기준">ⓘ</a>`;
      lg.title = `실측 ${pct}% (OSM 높이·층수), 추정 ${100-pct}% (용도·면적, 흐리게 표시)`;
      showCoord(controls.target.x, -controls.target.z, '중심 ');
    },
    attach(stage) { if (wrap.parentElement !== stage) { stage.append(wrap); resize(); if (bounds) fit(false); } },
    update(state, opt) {                                  // called every frame; rebuilt at most 5×/s
      if (state.bounds && bounds && (state.bounds.w !== bounds.w || state.bounds.e0 !== bounds.e0)) { bounds = state.bounds; fit(false); }
      const optChanged = JSON.stringify(opt) !== JSON.stringify(lastOpt);
      lastState = state; lastOpt = opt;
      if (optChanged) lastBuild = 0;
      if (opt.screen && opt.screen !== layerKey) { layerKey = opt.screen; syncLayerButtons(); }
    },
    setActive(on) { active = on; if (on) resize(); },
    fit,
    focusNode(id) { const m = domes.get(id); if (m) this.focus(m.target.x, -m.target.z); },
    focus(e, n) {                                         // keep the view angle and distance, move to (e, n)
      const off = camera.position.clone().sub(controls.target), target = V(e, n, 0);
      flight = { t0: performance.now(), from: { p: camera.position.clone(), t: controls.target.clone() }, to: { pos: target.clone().add(off), target } };
    },
  };
}
