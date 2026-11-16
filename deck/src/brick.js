// Isometric brick drawn as inline SVG: black keyline, flat faces, studs on top.
// One drawing routine for every piece on the page so line weight and proportions never drift.

const COS = 0.866, SIN = 0.5;

export const COLORS = {
  text: { top: '#FFFFFF', left: '#D9DEE2', right: '#BFC6CC' },
  table: { top: '#F6C700', left: '#D9A900', right: '#B88F00' },
  figure: { top: '#D01012', left: '#A80C0E', right: '#86090B' },
  plate: { top: '#D9D9D9', left: '#B4B4B4', right: '#989898' },
  blue: { top: '#1464C8', left: '#0F4F9E', right: '#0B3D7A' },
};

function pt(i, j, z, u) {
  return [(i - j) * u * COS, (i + j) * u * SIN - z];
}

function poly(points, fill, sw) {
  return `<polygon points="${points.map((p) => p.map((n) => n.toFixed(1)).join(',')).join(' ')}" fill="${fill}" stroke="#111" stroke-width="${sw}" stroke-linejoin="round"/>`;
}

/**
 * @param {object} o  w,d = studs wide/deep; h = body height in units; kind = colour key; u = unit px
 * @returns {string} svg markup sized to its own bounding box
 */
export function brick({ w = 2, d = 2, h = 1, kind = 'text', u = 24, studs = true, sw = 2, ghost = false } = {}) {
  const c = COLORS[kind] || COLORS.text;
  const H = h * u * 0.92;
  const top = [pt(0, 0, H, u), pt(w, 0, H, u), pt(w, d, H, u), pt(0, d, H, u)];
  const left = [pt(0, d, H, u), pt(w, d, H, u), pt(w, d, 0, u), pt(0, d, 0, u)];
  const right = [pt(w, 0, H, u), pt(w, d, H, u), pt(w, d, 0, u), pt(w, 0, 0, u)];
  let body = poly(left, ghost ? 'none' : c.left, sw) + poly(right, ghost ? 'none' : c.right, sw) + poly(top, ghost ? 'none' : c.top, sw);
  if (studs) {
    const rx = u * 0.3, ry = u * 0.17, sh = u * 0.2;
    for (let j = 0; j < d; j++) {
      for (let i = 0; i < w; i++) {
        const [cx, cy] = pt(i + 0.5, j + 0.5, H, u);
        body += `<path d="M${(cx - rx).toFixed(1)},${(cy - sh).toFixed(1)} v${sh.toFixed(1)} a${rx.toFixed(1)},${ry.toFixed(1)} 0 0 0 ${(2 * rx).toFixed(1)},0 v${(-sh).toFixed(1)}" fill="${ghost ? 'none' : c.left}" stroke="#111" stroke-width="${sw * 0.8}"/>`;
        body += `<ellipse cx="${cx.toFixed(1)}" cy="${(cy - sh).toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}" fill="${ghost ? 'none' : c.top}" stroke="#111" stroke-width="${sw * 0.8}"/>`;
      }
    }
  }
  const pad = sw + 1;
  const minX = -d * u * COS - pad, maxX = w * u * COS + pad;
  const minY = -H - u * 0.4 - pad, maxY = (w + d) * u * SIN + pad;
  const W = maxX - minX, Ht = maxY - minY;
  const dash = ghost ? ' stroke-dasharray="5 5"' : '';
  return `<svg class="brick${ghost ? ' brick--ghost' : ''}" viewBox="${minX.toFixed(1)} ${minY.toFixed(1)} ${W.toFixed(1)} ${Ht.toFixed(1)}" width="${W.toFixed(0)}" height="${Ht.toFixed(0)}" aria-hidden="true" focusable="false"><g${dash}>${body}</g></svg>`;
}

// Same piece as a <g> for use inside a shared isometric scene; (i, j, z) place it on the scene's stud grid.
export function brickG({ i = 0, j = 0, z = 0, u = 24, cls = '', ...o } = {}) {
  const inner = brick({ ...o, u }).replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '');
  const [x, y] = pt(i, j, z, u);
  return `<g class="${cls}" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})"><g class="${cls}__in">${inner}</g></g>`;
}

export function isoPoint(i, j, z, u) {
  return pt(i, j, z, u);
}

// Small flat piece (top-down view) used in call-outs and lists: one stud row.
export function chip(kind, n = 2) {
  const c = COLORS[kind] || COLORS.text;
  let s = '';
  for (let i = 0; i < n; i++) s += `<circle cx="${10 + i * 16}" cy="10" r="4.6" fill="${c.top}" stroke="#111" stroke-width="1.6"/>`;
  return `<svg class="chip" viewBox="0 0 ${n * 16 + 4} 20" width="${n * 16 + 4}" height="20" aria-hidden="true" focusable="false"><rect x="1" y="1" width="${n * 16 + 2}" height="18" rx="3" fill="${c.top}" stroke="#111" stroke-width="2"/>${s}</svg>`;
}
