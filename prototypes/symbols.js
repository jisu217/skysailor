// Tactical symbology for the city view and its reference sheet (symbology.html).
// Colour has three jobs, kept apart: the TYPE colour (violet balloon, cyan drone, green bird, white unknown) paints
// the target itself; the threat-level scale (grey → yellow → orange → red) is reserved for threat; own sensors are
// sky blue in a white ring. Type colours avoid the threat scale, the navy map and the friendly blue.
// Each target is a pictogram (drone / balloon / bird / unknown) in a dark badge so it stands off the map:
//   badge shape = affiliation (circle: unknown, diamond: suspected hostile, rounded square: neutral/permitted)
//   ring + glow colour = threat level (grey → yellow → orange → red), the one colour scale used everywhere
// Badge shapes borrow the MIL-STD-2525 / APP-6 idea (shape = affiliation); this is not a compliant
// implementation. Own sensors keep a fixed friendly blue.

export const TOK = {
  friend: '#3d7bff',
  zone: '#d1b47a',
  coverage: '#5f86ad',
  ray: '#8ea4bd',
  level: { LOW: '#8a9bad', MEDIUM: '#e6c84f', HIGH: '#f0974a', CRITICAL: '#ef5b5b' },
  type: { balloon: '#c58bff', drone: '#38e8f0', bird: '#9be36b', unknown: '#f4f8fc' },
  friendRing: '#e8f0f8',
  q: (q) => (q > 0.8 ? '#5b8fff' : q > 0.5 ? '#e6c84f' : '#ef5b5b'),   // coverage: friendly blue unless degraded
};
export const TYPE = { drone: 'UAV', balloon: 'BLN', bird: 'BRD', unknown: '?' };
export const TYPE_KO = { drone: '드론', balloon: '풍선', bird: '조류', unknown: '미상' };
export const AFFIL_KO = { hostile: '적성 의심', unknown: '미상', neutral: '중립·허가', friend: '아군' };

/** affiliation from what the pipeline knows (never "confirmed hostile": that is the operator's call) */
export function affiliation(t) {
  if (t.permitted) return 'neutral';                       // Remote ID on the permit list
  if (t.cls === 'bird') return 'neutral';
  if (t.level === 'HIGH' || t.level === 'CRITICAL') return 'hostile';
  return 'unknown';
}

// pictograms on a 24 × 24 grid
const GLYPH = {
  drone: `<g fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
      <path d="M7.2 7.2 L16.8 16.8 M16.8 7.2 L7.2 16.8"/>
      <circle cx="6" cy="6" r="3.3"/><circle cx="18" cy="6" r="3.3"/><circle cx="6" cy="18" r="3.3"/><circle cx="18" cy="18" r="3.3"/></g>
    <rect x="9.6" y="9.6" width="4.8" height="4.8" rx="1.2" fill="currentColor"/>`,
  balloon: `<path d="M12 2.2c3.7 0 6.2 2.8 6.2 6.3 0 3.7-3.3 6.6-5.3 7.8h-1.8C9.1 15.1 5.8 12.2 5.8 8.5c0-3.5 2.5-6.3 6.2-6.3z" fill="currentColor"/>
    <path d="M9.4 5.6c.7-1 1.7-1.5 2.6-1.6" fill="none" stroke="#06101b" stroke-width="1.1" stroke-linecap="round" opacity=".55"/>
    <path d="M12 16.3v3.2" stroke="currentColor" stroke-width="1"/><rect x="10.5" y="19.5" width="3" height="2.4" rx=".5" fill="currentColor"/>`,
  bird: `<path d="M1.5 10.8C4.6 7.6 9 8.2 12 12.4 15 8.2 19.4 7.6 22.5 10.8 19.2 10.3 15.6 11.9 12 16.2 8.4 11.9 4.8 10.3 1.5 10.8Z" fill="currentColor"/>`,
  unknown: `<text x="12" y="17.2" text-anchor="middle" font-family="ui-sans-serif,-apple-system,sans-serif" font-size="15" font-weight="700" fill="currentColor">?</text>`,
  dome: `<path d="M4.5 15.5a7.5 7.5 0 0 1 15 0z" fill="currentColor" opacity=".9"/>
    <path d="M3 15.5h18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    <circle cx="12" cy="11.6" r="1.7" fill="#06101b"/><path d="M12 15.5v3.5M9.5 19h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>`,
};

const BADGE = {
  unknown: '<circle cx="18" cy="18" r="14.5"/>',
  friend: '<circle cx="18" cy="18" r="14.5"/>',
  hostile: '<path d="M18 2.2 L33.8 18 L18 33.8 L2.2 18 Z" stroke-linejoin="round"/>',
  neutral: '<rect x="4" y="4" width="28" height="28" rx="6"/>',
};

/**
 * SVG string for a symbol.
 * affil: friend|hostile|neutral|unknown · glyph: drone|balloon|bird|unknown|dome · color: ring/glow
 * tentative: dashed ring (track not yet confirmed) · sel: white selection ring
 */
export function symbol({ affil, glyph, color, tentative = false, sel = false, size = 34, ink = '#eef5ff', hollow = false, fill = '#06101bf2' }) {
  const dash = tentative ? ' stroke-dasharray="3.5 2.5"' : '';
  const selRing = sel ? '<circle cx="18" cy="18" r="17.3" fill="none" stroke="#fff" stroke-width="1.2" stroke-dasharray="4 3"/>' : '';
  return `<svg class="sym" width="${size}" height="${size}" viewBox="0 0 36 36" style="--glow:${color}" aria-hidden="true">
    <g fill="${hollow ? 'none' : fill}" stroke="${color}" stroke-width="${hollow ? 1.4 : 1.7}"${dash}>${BADGE[affil]}</g>
    ${hollow ? '' : `<g transform="translate(8 8) scale(.833)" style="color:${tentative ? '#aab8c6' : ink}">${GLYPH[glyph] || GLYPH.unknown}</g>`}
    ${selRing}</svg>`;
}

/** hollow: ring only, drawn around the 3D model in the city view */
export function trackSymbol(t, sel = false, hollow = false) {
  return symbol({ affil: affiliation(t), glyph: TYPE[t.cls] ? t.cls : 'unknown', color: TOK.level[t.level] || TOK.level.LOW,
    tentative: t.status === 'tentative', sel, hollow, size: hollow ? 46 : 34 });
}

/** own dome: solid friendly-blue badge, white dome glyph; the ring turns yellow/red when attitude degrades */
export function nodeSymbol(q) {
  return symbol({ affil: 'friend', glyph: 'dome', color: q > 0.8 ? TOK.friendRing : TOK.q(q), size: 30, ink: '#ffffff', fill: TOK.friend });
}
