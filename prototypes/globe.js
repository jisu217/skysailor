// 3D overview globe for the C-UAS screen, ported from the EBS project (Earth Broadcasting System,
// src/main.js and helpers; used with the author's permission): same camera, controls, render-on-demand
// loop, vector/photo views, day/night shading, night lights, sun, atmosphere and HYG star field.
// Added here: Korea and the US get detailed province/state lines (Natural Earth 1:10m), and sites.
// Attribution: prototypes/data/geo/*-attribution.txt, STARS-LICENSE.md, textures/*-attribution.txt.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';

const DEG = Math.PI/180;
const HOME = { lat: 28, lon: 127, dist: 3.8 };                          // EBS start: East Asia facing, 3.8 away
export const REGIONS = {
  kr: { name: '대한민국', lat: 36.3, lon: 127.8, dist: 2.2 },
  us: { name: '미국', lat: 39, lon: -97.5, dist: 3.0 },
};

function toSphere(lon, lat, r = 1) {
  const a = lon*DEG, b = lat*DEG;
  return new THREE.Vector3(r*Math.cos(b)*Math.cos(a), r*Math.sin(b), -r*Math.cos(b)*Math.sin(a));
}

// EBS coastlines.js: subdivide long arcs so chords do not cut through the sphere
function linePositions(geojson, radius = 1.00015, maxArcDeg = 0.25) {
  const out = [], p = new THREE.Vector3(), maxArc = maxArcDeg*DEG;
  for (const { geometry } of geojson.features) {
    const polys = geometry.type === 'LineString' ? [[geometry.coordinates]]
      : geometry.type === 'MultiLineString' ? [geometry.coordinates]
        : geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
    for (const poly of polys) for (const ring of poly) for (let i = 1; i < ring.length; i++) {
      const s = toSphere(...ring[i-1]), e = toSphere(...ring[i]);
      const steps = Math.max(1, Math.ceil(s.angleTo(e)/maxArc));
      for (let k = 0; k < steps; k++) for (const t of [k/steps, (k+1)/steps]) {
        p.copy(s).lerp(e, t).normalize().multiplyScalar(radius); out.push(p.x, p.y, p.z);
      }
    }
  }
  return out;
}

// EBS land-surface.js: muted land fill on a 4096×2048 canvas (Korea/US one step lighter)
function landSurface(land, detail, maxAniso) {
  const c = document.createElement('canvas'); c.width = 4096; c.height = 2048;
  const g = c.getContext('2d');
  const fill = (geojson, color) => {
    g.fillStyle = color;
    for (const { geometry } of geojson.features) {
      const polys = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
      for (const poly of polys) {
        g.beginPath();
        for (const ring of poly) {
          ring.forEach(([lon, lat], i) => { const x = (lon+180)/360*c.width, y = (90-lat)/180*c.height; i ? g.lineTo(x, y) : g.moveTo(x, y); });
          g.closePath();
        }
        g.fill('evenodd');
      }
    }
  };
  g.fillStyle = '#061329'; g.fillRect(0, 0, c.width, c.height);
  fill(land, '#182440');
  fill(detail, '#1d2c4d');
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = maxAniso;
  return new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
}

// EBS stars.js
function starField(catalog, pixelRatio) {
  const pos = [], mag = [];
  for (const [ra, dec, m] of catalog) {
    const a = ra*Math.PI/12, d = dec*DEG;
    pos.push(50*Math.cos(d)*Math.cos(a), 50*Math.sin(d), -50*Math.cos(d)*Math.sin(a)); mag.push(m);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('magnitude', new THREE.Float32BufferAttribute(mag, 1));
  const mat = new THREE.ShaderMaterial({
    uniforms: { pixelRatio: { value: pixelRatio } }, transparent: true, depthWrite: false,
    vertexShader: `attribute float magnitude; uniform float pixelRatio; varying float brightness;
      void main(){ vec3 dir = mat3(viewMatrix)*position; gl_Position = projectionMatrix*vec4(dir,1.0);
        gl_PointSize = 2.0*pixelRatio*clamp(3.4-magnitude*0.36,1.0,4.0);
        brightness = clamp(pow(10.0,-0.16*(magnitude-1.0)),0.10,0.85); }`,
    fragmentShader: `varying float brightness; void main(){ float r = length(gl_PointCoord-0.5)*2.0; if(r>1.0) discard;
        gl_FragColor = vec4(0.80,0.86,1.0,(1.0-smoothstep(0.1,1.0,r))*brightness); }`,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; pts.renderOrder = -1;
  return pts;
}

// EBS: spherical shell keeps the atmospheric falloff attached to the globe at any zoom
function atmosphere() {
  return new THREE.Mesh(new THREE.SphereGeometry(1.24, 96, 64), new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide, forceSinglePass: true, blending: THREE.AdditiveBlending,
    uniforms: { glowColor: { value: new THREE.Color('#245ca8') } },
    vertexShader: `varying vec3 wp; void main(){ vec4 w = modelMatrix*vec4(position,1.0); wp = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform vec3 glowColor; varying vec3 wp; void main(){
        if(!gl_FrontFacing && length(cameraPosition) > 1.24) discard;
        vec3 ray = normalize(wp-cameraPosition); float r = length(cross(cameraPosition, ray));
        float a = exp(-max(r-1.0,0.0)*19.0)*(1.0-smoothstep(1.04,1.24,r))*smoothstep(0.90,1.0,r);
        gl_FragColor = vec4(glowColor, a*0.48); }`,
  }));
}

// EBS solar-position.js (NOAA approximate solar declination and equation of time, UTC)
function solarDirection(date) {
  const year = date.getUTCFullYear(), start = Date.UTC(year, 0, 1);
  const days = (Date.UTC(year+1, 0, 1)-start)/86400000, el = (date.getTime()-start)/86400000;
  const g = 2*Math.PI/days*(el-0.5);
  const eot = 229.18*(0.000075+0.001868*Math.cos(g)-0.032077*Math.sin(g)-0.014615*Math.cos(2*g)-0.040849*Math.sin(2*g));
  const dec = 0.006918-0.399912*Math.cos(g)+0.070257*Math.sin(g)-0.006758*Math.cos(2*g)+0.000907*Math.sin(2*g)
    -0.002697*Math.cos(3*g)+0.00148*Math.sin(3*g);
  const min = date.getUTCHours()*60+date.getUTCMinutes()+date.getUTCSeconds()/60+date.getUTCMilliseconds()/60000;
  const lon = (((180-(min+eot)/4+540)%360)-180)*DEG;
  return [Math.cos(dec)*Math.cos(lon), Math.sin(dec), -Math.cos(dec)*Math.sin(lon)];
}

// EBS night-light-texture.js: NASA Black Marble mask, lit only on the night side
function nightLights(url, sunDirection, anisotropy, onReady) {
  const material = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
    uniforms: { lightMap: { value: null }, sunDirection: { value: sunDirection } },
    vertexShader: `varying vec2 lightUv; varying vec3 worldNormal; varying vec3 worldPosition;
      void main(){ lightUv = uv; worldNormal = normalize(mat3(modelMatrix)*normal);
        vec4 world = modelMatrix*vec4(position,1.0); worldPosition = world.xyz; gl_Position = projectionMatrix*viewMatrix*world; }`,
    fragmentShader: `uniform sampler2D lightMap; uniform vec3 sunDirection; varying vec2 lightUv; varying vec3 worldNormal; varying vec3 worldPosition;
      void main(){ vec3 n = normalize(worldNormal);
        float night = 1.0-smoothstep(-0.18,0.04,dot(n,sunDirection));
        float facing = smoothstep(0.02,0.18,dot(n,normalize(cameraPosition-worldPosition)));
        float b = texture2D(lightMap,lightUv).r;
        float alpha = pow(b,0.85)*smoothstep(0.015,0.10,b)*night*facing*0.9;
        if(alpha < 0.001) discard;
        gl_FragColor = vec4(mix(vec3(1.0,0.58,0.22),vec3(1.0,0.86,0.57),b), alpha); }`,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1.0004, 96, 64), material);
  mesh.renderOrder = 2; mesh.visible = false;
  new THREE.TextureLoader().loadAsync(url).then((t) => {
    t.colorSpace = THREE.NoColorSpace; t.wrapS = THREE.RepeatWrapping; t.anisotropy = anisotropy;
    t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
    material.uniforms.lightMap.value = t; mesh.visible = true; onReady();
  }).catch((e) => console.warn('야간 불빛 자료를 불러오지 못했습니다.', e));
  return mesh;
}

/**
 * sites: [{id, name, sub, lat, lon, mode:'kr'|'us', live:bool}]
 * returns { setMode, flyToSite, resetView, setView, setAlerts, setActive, resize }
 */
export async function createGlobe({ canvas, overlay, sites, onSite, base = 'data/geo/' }) {
  const load = (f) => fetch(base+f).then((r) => { if (!r.ok) throw new Error(`${f}: ${r.status}`); return r.json(); });
  const [land, borders, detail, starCatalog] = await Promise.all([load('land.json'), load('borders.json'), load('admin1-kr-us.json'), load('stars.json')]);

  let renderNeeded = true;
  const invalidate = () => { renderNeeded = true; };
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  const aniso = renderer.capabilities.getMaxAnisotropy();

  const scene = new THREE.Scene();
  scene.add(starField(starCatalog, renderer.getPixelRatio()));
  const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 100);
  camera.position.copy(toSphere(HOME.lon, HOME.lat, HOME.dist));
  const controls = new OrbitControls(camera, canvas);
  Object.assign(controls, { enablePan: false, enableDamping: true, dampingFactor: 0.07, rotateSpeed: 0.55, zoomSpeed: 0.7, minDistance: 1.2, maxDistance: 10 });
  const initialViewDistance = HOME.dist, baseRotateSpeed = controls.rotateSpeed;
  controls.addEventListener('change', () => {
    // surface distance tracks apparent motion: slow rotation down as the camera zooms in
    const surface = Math.max(0.01, camera.position.distanceTo(controls.target)-1);
    controls.rotateSpeed = baseRotateSpeed*surface/(initialViewDistance-1);
    invalidate();
  });
  controls.update();

  // earth: vector (default) or photo material
  const tl = new THREE.TextureLoader();
  const tex = (f, srgb = true) => { const t = tl.load(base+'textures/'+f, invalidate); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = aniso; return t; };
  const vectorMaterial = landSurface(land, detail, aniso);
  let photoMaterial = null;
  const earth = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), vectorMaterial);
  scene.add(earth);

  const lineMat = (color, width) => new LineMaterial({ color, linewidth: width, worldUnits: false, toneMapped: false });
  const lineObj = (positions, mat) => new LineSegments2(new LineSegmentsGeometry().setPositions(positions), mat);
  const coastlineMaterial = lineMat('#365b86', 1), borderMaterial = lineMat('#35506b', 0.55);
  const gridMaterial = lineMat('#15263d', 0.6), detailMaterial = lineMat('#4f7fb4', 0.6);
  const coastlines = lineObj(linePositions(land), coastlineMaterial);
  const countryBorders = lineObj(linePositions(borders), borderMaterial);
  const provinces = lineObj(linePositions(detail, 1.0002, 0.05), detailMaterial);   // Korea / US only
  const grid = [];
  const gp = (lon, lat) => toSphere(lon, lat, 1.0001).toArray();
  for (let lat = -75; lat <= 75; lat += 15) for (let lon = -180; lon < 180; lon += 0.25) grid.push(...gp(lon, lat), ...gp(lon+0.25, lat));
  for (let lon = -180; lon < 180; lon += 15) for (let lat = -90; lat < 90; lat += 0.25) grid.push(...gp(lon, lat), ...gp(lon, lat+0.25));
  const graticule = lineObj(grid, gridMaterial);
  earth.add(coastlines, countryBorders, provinces, graticule);
  scene.add(atmosphere());

  // sun, day/night
  scene.add(new THREE.AmbientLight(0xd8e8ff, 0.85));
  const sun = new THREE.DirectionalLight(0xfff1da, 2.5);
  scene.add(sun);
  const sunDirection = new THREE.Vector3();
  earth.add(nightLights(base+'textures/earth-night.png', sunDirection, aniso, invalidate));
  // EBS: shade coastline fragments with the same sun direction, brighter tint at night
  for (const m of [coastlineMaterial, detailMaterial]) {
    m.onBeforeCompile = (shader) => {
      shader.uniforms.coastSunDirection = { value: sunDirection };
      shader.uniforms.coastNightColor = { value: new THREE.Color(m === detailMaterial ? '#6fa6dc' : '#80bfff') };
      shader.vertexShader = `varying vec3 coastWorldNormal;\n${shader.vertexShader}`.replace('void main() {', `void main() {
        vec3 coastPoint = position.y < 0.5 ? instanceStart : instanceEnd;
        coastWorldNormal = normalize(mat3(modelMatrix) * coastPoint);`);
      shader.fragmentShader = `uniform vec3 coastSunDirection; uniform vec3 coastNightColor; varying vec3 coastWorldNormal;\n${shader.fragmentShader}`
        .replace('vec4 diffuseColor = vec4( diffuse, alpha );', `
        float coastDaylight = smoothstep(-0.22, 0.32, dot(normalize(coastWorldNormal), coastSunDirection));
        vec4 diffuseColor = vec4(mix(coastNightColor, diffuse, coastDaylight), alpha);`);
    };
    m.customProgramCacheKey = () => (m === detailMaterial ? 'detail' : 'coastline')+'-day-night-v1';
  }
  const sunVectorMaterial = new THREE.MeshBasicMaterial({ color: '#fff1d5', toneMapped: false });
  let sunPhotoMaterial = null;
  const sunDisc = new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 24), sunVectorMaterial);
  scene.add(sunDisc);
  const gc = document.createElement('canvas'); gc.width = gc.height = 128;
  const gx = gc.getContext('2d'), grad = gx.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,235,196,0.7)'); grad.addColorStop(0.2, 'rgba(255,211,145,0.2)'); grad.addColorStop(1, 'rgba(255,194,110,0)');
  gx.fillStyle = grad; gx.fillRect(0, 0, 128, 128);
  const sunGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(gc), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
  sunGlow.scale.setScalar(1.2);
  scene.add(sunGlow);
  const nightShade = new THREE.Mesh(new THREE.SphereGeometry(1.001, 128, 96), new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, uniforms: { sunDirection: { value: sunDirection } },
    vertexShader: `varying vec3 globeNormal; void main(){ globeNormal = normalize(mat3(modelMatrix)*normal); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform vec3 sunDirection; varying vec3 globeNormal; void main(){
        float daylight = smoothstep(-0.22,0.32,dot(normalize(globeNormal),sunDirection));
        gl_FragColor = vec4(0.0,0.005,0.018,(1.0-daylight)*0.48); }`,
  }));
  nightShade.renderOrder = 1;
  scene.add(nightShade);
  const localSun = new THREE.Vector3(), sunDist = Math.hypot(20, 10, 15);
  let lastSolar = -Infinity;
  function updateSun(now) {
    if (Math.abs(now-lastSolar) >= 1000) { localSun.fromArray(solarDirection(new Date(now))); lastSolar = now; invalidate(); }
    sunDirection.copy(localSun).applyQuaternion(earth.quaternion);
    sun.position.copy(sunDirection).multiplyScalar(sunDist);
    sunDisc.position.copy(sun.position); sunGlow.position.copy(sun.position);
  }

  function setView(mode) {
    const vector = mode !== 'photo';
    if (!vector && !photoMaterial) {
      photoMaterial = new THREE.MeshPhongMaterial({ map: tex('earth.jpg'), normalMap: tex('earth-normal.jpg', false), normalScale: new THREE.Vector2(0.35, 0.35), shininess: 8, specular: 0x18202b });
      sunPhotoMaterial = new THREE.MeshBasicMaterial({ map: tex('sun.jpg'), toneMapped: false });
    }
    earth.material = vector ? vectorMaterial : photoMaterial;
    sunDisc.material = vector ? sunVectorMaterial : sunPhotoMaterial;
    coastlines.visible = graticule.visible = vector;
    invalidate();
  }

  // site markers: HTML buttons, hidden on the far side (EBS dashboard.js projection test)
  const markers = [];
  for (const s of sites) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'globe-site'; b.dataset.mode = s.mode; b.dataset.live = String(!!s.live);
    b.innerHTML = '<i></i><span><b></b><small></small></span>';
    b.querySelector('b').textContent = s.name; b.querySelector('small').textContent = s.sub || '';
    b.setAttribute('aria-label', `${s.name} ${s.sub || ''}`);
    b.addEventListener('click', () => onSite?.(s));
    overlay.append(b);
    markers.push({ el: b, site: s, local: toSphere(s.lon, s.lat, 1.001) });
  }
  const world = new THREE.Vector3(), screen = new THREE.Vector3();
  function placeMarkers() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    for (const m of markers) {
      world.copy(m.local).applyQuaternion(earth.quaternion);
      const front = world.dot(camera.position) > world.lengthSq()+0.03;
      screen.copy(world).project(camera);
      const visible = front && Math.abs(screen.x) < 1.1 && Math.abs(screen.y) < 1.1;
      if (m.el.hidden !== !visible) m.el.hidden = !visible;
      if (visible) m.el.style.transform = `translate(${((screen.x+1)/2*w).toFixed(1)}px, ${((1-screen.y)/2*h).toFixed(1)}px)`;
    }
  }

  // EBS fly-to: slerp the camera direction, lerp the distance, smoothstep over 1 s
  let flight = null;
  function flyTo(lat, lon, dist, ms = 1000) {
    const to = toSphere(lon, lat, dist).applyQuaternion(earth.quaternion);
    return new Promise((resolve) => { flight = { from: camera.position.clone(), to, start: performance.now(), ms, resolve }; invalidate(); });
  }
  const rot = new THREE.Quaternion(), part = new THREE.Quaternion(), unitFrom = new THREE.Vector3(), unitTo = new THREE.Vector3();
  function stepFlight(now) {
    const t = Math.min(1, (now-flight.start)/flight.ms), k = t*t*(3-2*t);
    rot.setFromUnitVectors(unitFrom.copy(flight.from).normalize(), unitTo.copy(flight.to).normalize());
    part.identity().slerp(rot, k);
    camera.position.copy(flight.from).normalize().applyQuaternion(part).multiplyScalar(THREE.MathUtils.lerp(flight.from.length(), flight.to.length(), k));
    camera.lookAt(controls.target);
    controls.dispatchEvent({ type: 'change' });
    if (t >= 1) { const r = flight.resolve; flight = null; controls.update(); r(); }
  }

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    camera.aspect = w/h;
    camera.fov = w < h ? 55 : 40;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    for (const m of [coastlineMaterial, borderMaterial, gridMaterial, detailMaterial]) m.resolution.set(w, h);
    invalidate();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  // EBS keyboard: arrows rotate the globe, +/- zoom
  canvas.addEventListener('keydown', (e) => {
    const r = { ArrowLeft: 0.08, ArrowRight: -0.08 };
    if (e.key in r) earth.rotation.y += r[e.key];
    else if (e.key === 'ArrowUp') earth.rotation.x += 0.08;
    else if (e.key === 'ArrowDown') earth.rotation.x -= 0.08;
    else if (['+', '=', '-'].includes(e.key)) {
      camera.position.multiplyScalar(e.key === '-' ? 1.1 : 1/1.1).clampLength(controls.minDistance, controls.maxDistance);
      controls.dispatchEvent({ type: 'change' });
    } else return;
    invalidate(); e.preventDefault();
  });

  setView('vector');
  updateSun(Date.now());
  let active = true;
  renderer.setAnimationLoop(() => {
    if (!active) return;
    if (flight) stepFlight(performance.now()); else controls.update();
    updateSun(Date.now());
    // match the globe's apparent scale instead of a fixed pixel width
    const zoom = initialViewDistance/camera.position.distanceTo(controls.target);
    coastlineMaterial.linewidth = zoom; gridMaterial.linewidth = 0.6*zoom; borderMaterial.linewidth = 0.55*zoom;
    detailMaterial.linewidth = Math.min(2, 0.6*zoom);
    if (renderNeeded) { renderer.render(scene, camera); placeMarkers(); renderNeeded = false; }
  });

  return {
    setMode(mode) {
      const r = REGIONS[mode];
      for (const m of markers) m.el.classList.toggle('dim', m.site.mode !== mode);
      return flyTo(r.lat, r.lon, r.dist);
    },
    flyToSite(site) { return flyTo(site.lat, site.lon, 1.35, 1200); },
    resetView() { return flyTo(HOME.lat, HOME.lon, HOME.dist); },
    setView,
    setAlerts(levels) {                                     // {siteId: 'LOW'|'MEDIUM'|'HIGH'|'CRITICAL'|null}
      for (const m of markers) m.el.dataset.level = levels[m.site.id] || '';
    },
    setActive(on) { active = on; if (on) resize(); },
    resize,
  };
}
