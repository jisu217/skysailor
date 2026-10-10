// Small 3D target models for the city view and the symbology sheet.
// Balloon shape follows the Skysailor game scene (web/src/game/main.js: stretched sphere, knot, cord,
// MeshStandard roughness .35 / metalness .05); drone, bird and unknown are drawn in the same style.
// Each type has its own colour (symbols.js TOK.type), kept clear of the threat-level scale, plus a soft glow of
// the same colour so the model separates from the light buildings. Each model is about 1 unit across;
// userData.size is its screen height reference and userData.animate(t) moves rotors, wings or sway.
import * as THREE from 'three';
import { TOK } from './symbols.js';

const tint = (hex, k) => new THREE.Color(hex).multiplyScalar(k);
const skin = (hex, rough = 0.35) => new THREE.MeshStandardMaterial({ color: hex, roughness: rough, metalness: 0.05, emissive: tint(hex, 0.28) });
const pearl = () => skin(TOK.type.balloon);
let glowTex = null;
function glow(hex, size) {
  if (!glowTex) {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,255,255,.55)'); g.addColorStop(0.45, 'rgba(255,255,255,.16)'); g.addColorStop(1, 'rgba(255,255,255,0)');
    x.fillStyle = g; x.fillRect(0, 0, 64, 64); glowTex = new THREE.CanvasTexture(c);
  }
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: hex, transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending }));
  s.scale.setScalar(size); s.renderOrder = -1;
  return s;
}

function balloon() {
  const g = new THREE.Group(), m = pearl();
  const env = new THREE.Mesh(new THREE.SphereGeometry(0.32, 24, 18), m);
  env.scale.set(1, 1.25, 1);
  const knot = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.08, 10), m);
  knot.position.y = -0.4-0.03; knot.rotation.x = Math.PI;
  const cord = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, -0.46, 0), new THREE.Vector3(0.04, -0.62, 0), new THREE.Vector3(0, -0.8, 0)]),
    new THREE.LineBasicMaterial({ color: '#c3d2e2' }));
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.1, 0.12), new THREE.MeshStandardMaterial({ color: '#7d8a99', roughness: 0.6 }));
  box.position.y = -0.86;
  g.add(glow(TOK.type.balloon, 1.6), env, knot, cord, box);
  g.userData = { size: 1.3, animate: (t) => { g.rotation.z = Math.sin(t*0.9)*0.06; g.rotation.x = Math.cos(t*0.7)*0.04; } };
  return g;
}

function drone(accent = '#8a9bad') {
  const g = new THREE.Group(), c = TOK.type.drone;
  const body = new THREE.MeshStandardMaterial({ color: tint(c, 0.55), roughness: 0.45, metalness: 0.3, emissive: tint(c, 0.12) });
  const light = skin(c, 0.4);
  g.add(glow(c, 1.5));
  const hull = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.09, 0.2), body);
  const top = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.04, 0.12), light);
  top.position.y = 0.065;
  g.add(hull, top);
  const rotors = [];
  for (const [x, z] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.035, 0.05), body);
    arm.position.set(x*0.16, 0, z*0.16); arm.rotation.y = x*z > 0 ? -Math.PI/4 : Math.PI/4;
    const motor = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.07, 12), light);
    motor.position.set(x*0.32, 0.03, z*0.32);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.006, 28),
      new THREE.MeshStandardMaterial({ color: c, emissive: tint(c, 0.3), transparent: true, opacity: 0.3, roughness: 0.2, depthWrite: false }));
    disc.position.set(x*0.32, 0.075, z*0.32);
    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.008, 0.03), light);
    blade.position.copy(disc.position);
    rotors.push(blade);
    g.add(arm, motor, disc, blade);
  }
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.03, 10, 8), new THREE.MeshBasicMaterial({ color: accent }));
  led.position.set(0.14, 0.02, 0);
  g.add(led);
  g.userData = { size: 0.8, led, animate: (t) => { rotors.forEach((r, i) => { r.rotation.y = t*40*(i%2 ? 1 : -1); }); } };
  return g;
}

function bird() {
  const g = new THREE.Group(), m = skin(TOK.type.bird, 0.6);
  m.side = THREE.DoubleSide;
  g.add(glow(TOK.type.bird, 1.1));
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.07, 14, 10), m);
  body.scale.set(2.6, 0.75, 0.85);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), m);
  head.position.set(0.17, 0.02, 0);
  // tail: small fan behind the body
  const tail = new THREE.Mesh(new THREE.ShapeGeometry(new THREE.Shape([new THREE.Vector2(-0.14, 0), new THREE.Vector2(-0.27, 0.07), new THREE.Vector2(-0.27, -0.07)])), m);
  tail.rotation.x = -Math.PI/2;
  // gull wing: broad at the root, swept and tapered to the tip; s = ±1 for the two sides
  const wing = (s) => {
    const pts = [[0.07, 0], [0.05, 0.16], [-0.01, 0.3], [-0.09, 0.46], [-0.11, 0.4], [-0.08, 0.22], [-0.09, 0]];
    const w = new THREE.Mesh(new THREE.ShapeGeometry(new THREE.Shape(pts.map(([x, y]) => new THREE.Vector2(x, y*s)))), m);
    w.rotation.x = -Math.PI/2;
    const pivot = new THREE.Group(); pivot.add(w); return pivot;
  };
  const l = wing(1), r = wing(-1);
  g.add(body, head, tail, l, r);
  g.userData = { size: 0.6, animate: (t) => { const a = 0.15+Math.sin(t*5)*0.5; l.rotation.x = a; r.rotation.x = -a; } };
  return g;
}

function unknown() {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color: TOK.type.unknown, roughness: 0.3, metalness: 0.1, emissive: '#4a5a6c', flatShading: true });
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.22, 0), m);
  g.add(glow(TOK.type.unknown, 1.1), core);
  g.userData = { size: 0.6, animate: (t) => { core.rotation.y = t*0.8; core.rotation.x = t*0.5; m.emissiveIntensity = 0.8+0.4*Math.sin(t*3); } };
  return g;
}

// Skysailor sensor dome (hanging.py: Ø 0.38 m, 0.08 m deep, 8 cameras on the rim, three cables to a hanging
// weight). Faceted translucent shell, glowing camera ring, cables and weight. setStatus(colour) recolours the
// lenses; setTilt(rad) tilts the shell (measured attitude; the tilt direction is not reported, only its size).
export function makeDome() {
  const g = new THREE.Group(), body = new THREE.Group();
  const c = TOK.friend;
  const shell = new THREE.Mesh(new THREE.SphereGeometry(0.5, 12, 3, 0, Math.PI*2, 0, 0.82),
    new THREE.MeshStandardMaterial({ color: '#cfe0ff', emissive: tint(c, 0.25), roughness: 0.25, metalness: 0.1, transparent: true, opacity: 0.55, flatShading: true, side: THREE.DoubleSide, depthWrite: false }));
  shell.scale.set(1, 0.42, 1); shell.position.y = -0.2;
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(shell.geometry, 1), new THREE.LineBasicMaterial({ color: '#e8f0ff', transparent: true, opacity: 0.8 }));
  edges.scale.copy(shell.scale); edges.position.copy(shell.position);
  const rimY = -0.2+0.5*Math.cos(0.82)*0.42, rimR = 0.5*Math.sin(0.82);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(rimR, 0.018, 8, 48), new THREE.MeshStandardMaterial({ color: '#dbe6f5', roughness: 0.4, metalness: 0.3 }));
  rim.rotation.x = Math.PI/2; rim.position.y = rimY;
  const lensMat = new THREE.MeshBasicMaterial({ color: c });
  for (let i = 0; i < 8; i++) {
    const a = i/8*Math.PI*2, lens = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), lensMat);
    lens.position.set(Math.cos(a)*rimR, rimY+0.02, Math.sin(a)*rimR);
    body.add(lens);
  }
  body.add(shell, edges, rim);
  // three cables from the rim to the weight below (they hang straight, so they stay out of the tilted body)
  const w = new THREE.Vector3(0, -0.75, 0), cab = [];
  for (let i = 0; i < 3; i++) { const a = i/3*Math.PI*2; cab.push(Math.cos(a)*rimR*0.9, rimY, Math.sin(a)*rimR*0.9, w.x, w.y, w.z); }
  const cables = new THREE.LineSegments(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(cab, 3)),
    new THREE.LineBasicMaterial({ color: '#a9bdd6', transparent: true, opacity: 0.85 }));
  const weight = new THREE.Mesh(new THREE.SphereGeometry(0.06, 12, 10), new THREE.MeshStandardMaterial({ color: '#8fa3bb', roughness: 0.5, metalness: 0.4 }));
  weight.position.copy(w);
  g.add(glow(c, 1.7), body, cables, weight);
  g.userData = {
    size: 1.1, lensMat,
    setStatus: (hex) => lensMat.color.set(hex),
    setTilt: (rad) => { body.rotation.z = rad; },
    animate: (t) => { body.rotation.y = t*0.15; },
  };
  return g;
}

export function makeModel(cls) {
  return cls === 'balloon' ? balloon() : cls === 'drone' ? drone() : cls === 'bird' ? bird() : unknown();
}

export function addModelLights(scene) {
  scene.add(new THREE.HemisphereLight('#e6f0ff', '#1a2433', 2.2));
  const sun = new THREE.DirectionalLight('#ffffff', 2.4);
  sun.position.set(-3, 6, 4);
  scene.add(sun);
}
