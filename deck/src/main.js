import '@fontsource/be-vietnam-pro/vietnamese-500.css';
import '@fontsource/be-vietnam-pro/latin-500.css';
import '@fontsource/be-vietnam-pro/vietnamese-600.css';
import '@fontsource/be-vietnam-pro/latin-600.css';
import '@fontsource/be-vietnam-pro/vietnamese-800.css';
import '@fontsource/be-vietnam-pro/latin-800.css';
import '@fontsource/be-vietnam-pro/vietnamese-900.css';
import '@fontsource/be-vietnam-pro/latin-900.css';
import '@fontsource/jetbrains-mono/latin-600.css';
import '@fontsource/jetbrains-mono/latin-800.css';
import './style.css';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import DATA from './data.json';
import { brick, brickG, chip, isoPoint } from './brick.js';

gsap.registerPlugin(ScrollTrigger);

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const KIND = { text: 'text', table: 'bảng', figure: 'hình' };
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const wide = matchMedia('(min-width: 721px)');
const S = DATA.stats;
const shortId = (id) => id.replace('who-whs-2023-', '');
const nf = (n) => Number(n).toLocaleString('vi-VN');

/* ---------------- step nav ---------------- */
const hasRetrieval = DATA.retrieval.configs.length > 0;
const AG = DATA.agent;
const TS = DATA.tests;
const hasAgent = AG.dev.length > 0;
const testRuns = Object.entries(AG.runs).filter(([, r]) => r.split === 'test');
const hasTest = Boolean(TS.retrieval) || testRuns.length > 0;
const stepIds = [1, 2, 3, 4, 5, 6].concat(hasRetrieval ? [7] : [], hasAgent ? [8] : [], hasTest ? [9] : []);
$('#stepnav').innerHTML = stepIds.map((n) => `<li><a href="#buoc-${n}" data-n="${n}" aria-label="Bước ${n}">${n}</a></li>`).join('');
stepIds.forEach((n) => { const el = $(`#buoc-${n}`); if (el) el.hidden = false; });
const navLinks = $$('#stepnav a');
function setStep(n) {
  navLinks.forEach((a) => {
    const k = +a.dataset.n;
    if (k === n) a.setAttribute('aria-current', 'step'); else a.removeAttribute('aria-current');
    a.classList.toggle('is-done', k < n);
  });
}
stepIds.forEach((n) => ScrollTrigger.create({ trigger: `#buoc-${n}`, start: 'top 55%', end: 'bottom 55%', onToggle: (st) => st.isActive && setStep(n) }));
setStep(1);

/* ---------------- step 1: bag + scene ---------------- */
$('#bag').innerHTML = ['text', 'table', 'figure'].map((k) =>
  `<li>${brick({ kind: k, w: 2, d: 2, u: 13, sw: 1.6 })}<span class="x">${S.byKind[k]}×</span><span>viên ${KIND[k]}</span></li>`).join('') +
  `<li><span class="x">${S.chunks}×</span><span>tất cả, từ ${DATA.source.pages} trang</span></li>`;

function buildScene1() {
  const host = $('#scene1');
  const U = 30, PW = 12, PD = 5, PH = 0.32;
  const zTop = PH * U * 0.92;
  const seats = { text: [1.4, 1.5], table: [5, 1.5], figure: [8.6, 1.5] };
  const HOVER = 150;
  let pieces = '';
  let arrows = '';
  let tags = '';
  for (const k of ['text', 'table', 'figure']) {
    const [i, j] = seats[k];
    pieces += brickG({ i, j, z: zTop, u: U, kind: k, w: 2, d: 2, cls: `fly fly--${k}` });
    const [cx, cy] = isoPoint(i + 1, j + 1, zTop + U * 0.6, U);
    arrows += `<g class="arr arr--${k}"><line x1="${cx}" y1="${cy - HOVER + 46}" x2="${cx}" y2="${cy - 16}" stroke="#0F5FB8" stroke-width="7" stroke-dasharray="11 8"/><path d="M${cx - 13},${cy - 20} L${cx + 13},${cy - 20} L${cx},${cy + 2} Z" fill="#0F5FB8"/></g>`;
    tags += `<g class="tg tg--${k}" transform="translate(${cx + 96} ${cy - HOVER - 6})"><rect x="-62" y="-17" width="124" height="34" rx="6" fill="#fff" stroke="#111" stroke-width="2.5"/><text x="0" y="6" text-anchor="middle" font-family="JetBrains Mono, monospace" font-weight="800" font-size="16" fill="#111">${S.byKind[k]}× ${KIND[k]}</text></g>`;
  }
  const plate = brickG({ i: 0, j: 0, z: 0, u: U, kind: 'plate', w: PW, d: PD, h: PH });
  const vb = [-(PD * U * 0.866) - 8, -HOVER - 230, (PW + PD) * U * 0.866 + 16, (PW + PD) * U * 0.5 + HOVER + 250];
  host.innerHTML = `
    <div class="sheet" id="sheet">
      <span class="sheet__pg">p.075</span>
      <div class="part part--text"><i></i><i></i><i></i></div>
      <div class="part part--table"></div>
      <div class="part part--figure"><i style="height:44%"></i><i style="height:78%"></i><i style="height:60%"></i><i style="height:92%"></i></div>
    </div>
    <svg id="iso" viewBox="${vb.join(' ')}" aria-hidden="true" focusable="false">${plate}<g id="arrs">${arrows}</g>${pieces}<g id="tgs">${tags}</g>
      <g id="done" transform="translate(${isoPoint(PW / 2, PD / 2, 0, U)[0]} ${-HOVER + 10})"><rect x="-205" y="-20" width="410" height="40" rx="7" fill="#111"/><text x="0" y="7" text-anchor="middle" font-family="JetBrains Mono, monospace" font-weight="800" font-size="17" fill="#fff">${S.chunks} viên · 1 index · ${S.dims} chiều</text></g>
    </svg>`;
  const css = document.createElement('style');
  css.textContent = `.scene--1 .sheet{left:31%;top:6%}.scene--1 #iso{right:2%;bottom:13%;width:min(54vw,820px);height:auto;overflow:visible}
  @media (max-width:720px){.scene--1 .sheet{left:6%;top:0;width:36%}.scene--1 #iso{right:0;bottom:0;width:100%}}`;
  document.head.append(css);
}
buildScene1();

function animateScene1() {
  const iso = $('#iso');
  const kinds = ['text', 'table', 'figure'];
  if (reduced || !wide.matches) { gsap.set('#arrs', { opacity: 0 }); return; }
  const HOVER = 150;
  const fromSheet = (k) => {
    // screen delta between the sheet part and the brick's seat, converted into SVG user units
    const part = $(`.sheet .part--${k}`).getBoundingClientRect();
    const g = $(`.fly--${k}`, iso);
    const gb = g.getBoundingClientRect();
    const m = iso.getScreenCTM();
    const sx = 1 / m.a, sy = 1 / m.d;
    return { x: (part.left + part.width / 2 - (gb.left + gb.width / 2)) * sx, y: (part.top + part.height / 2 - (gb.top + gb.height / 2)) * sy };
  };
  const tl = gsap.timeline({ defaults: { ease: 'none' }, scrollTrigger: { trigger: '#buoc-1', start: 'top top', end: 'bottom bottom', scrub: 0.6, invalidateOnRefresh: true } });
  gsap.set(['#arrs .arr', '#tgs .tg', '#done'], { opacity: 0 });
  kinds.forEach((k, n) => {
    const inn = `.fly--${k}__in`;
    tl.fromTo(inn, { x: () => fromSheet(k).x, y: () => fromSheet(k).y, scale: 0.25, opacity: 0, transformOrigin: '50% 50%' },
      { x: 0, y: -HOVER, scale: 1, opacity: 1, duration: 1, ease: 'power2.inOut' }, n * 0.35);
    tl.to(`.sheet .part--${k}`, { opacity: 0.22, duration: 0.5 }, n * 0.35 + 0.1);
    tl.to(`.tg--${k}`, { opacity: 1, duration: 0.3 }, n * 0.35 + 0.8);
  });
  tl.to('#arrs .arr', { opacity: 1, duration: 0.4, stagger: 0.12 }, 1.9);
  kinds.forEach((k, n) => {
    const t = 2.6 + n * 0.5;
    tl.to(`.fly--${k}__in`, { y: 0, duration: 0.55, ease: 'expo.in' }, t);
    tl.to(`.fly--${k}__in`, { scaleY: 0.9, transformOrigin: '50% 100%', duration: 0.07 }, t + 0.55);
    tl.to(`.fly--${k}__in`, { scaleY: 1, duration: 0.2, ease: 'expo.out' }, t + 0.62);
    tl.to([`.arr--${k}`, `.tg--${k}`], { opacity: 0, duration: 0.25 }, t + 0.3);
  });
  tl.to('#done', { opacity: 1, duration: 0.4 }, 4.3);
  tl.to('#hint1', { opacity: 0, duration: 0.3 }, 0.4);
  tl.to({}, { duration: 0.5 });
}

/* ---------------- step 2: text ---------------- */
const ex = DATA.examples;
$('#spec2').innerHTML = `
  <li><span class="v">${S.byKind.text}</span><span>viên text, cắt theo đoạn</span></li>
  <li><span class="v">≤ 1.500</span><span>ký tự mỗi viên</span></li>
  <li><span class="v">${S.blankPages.length}</span><span>trang trắng, không có gì để cắt</span></li>`;
{
  const t = ex.text.text;
  const cut = t.indexOf('\n');
  const first = cut > 0 ? t.slice(0, cut) : '';
  const rest = cut > 0 ? t.slice(cut + 1) : t;
  const marked = esc(rest).replace('from 32.7% in 2000 to 22.3% in 2020', '<mark>from 32.7% in 2000 to 22.3% in 2020</mark>');
  $('#ex-text .callout__title').innerHTML = `${chip('text', 3)} Một viên text thật, trang ${ex.text.page}`;
  $('#ex-text-body').innerHTML = `${first ? `<b>${esc(first)}</b><br>` : ''}${marked}…<p class="src">${esc(ex.text.id)}</p>`;
}

/* ---------------- step 3: table ---------------- */
$('#spec3').innerHTML = `
  <li><span class="v">${S.byKind.table}</span><span>viên bảng từ ${S.tablePages} trang có bảng</span></li>
  <li><span class="v">12</span><span>hàng mỗi viên, tiêu đề cột lặp lại</span></li>
  <li><span class="v">96–127</span><span>trang annex, in theo cặp trái phải</span></li>`;
{
  const cells = (row) => row.split('|').slice(1, -1).map((c) => c.trim());
  const L = ex.table.leftRows.map(cells);
  const R = ex.table.rightRows.map(cells);
  const lrow = (r) => `<tr><td class="name">${esc(r[0])}</td><td>${esc(r[4])}</td><td>${esc(r[5])}</td><td>${esc(r[6])}</td></tr>`;
  const rrow = (r) => `<tr><td class="name borrow">${esc(r[0])}</td><td>${esc(r[1])}</td><td>${esc(r[3])}</td><td>${esc(r[4])}</td></tr>`;
  $('#ex-table').innerHTML = `
    <div class="tpage"><h3>Trang 100 · có tên nước</h3>
      <table class="tgrid"><thead><tr><th class="name">Countries and areas</th><th>LE male</th><th>LE female</th><th>LE both</th></tr></thead><tbody>${L.map(lrow).join('')}</tbody></table></div>
    <div class="tpage"><h3>Trang 101 · chỉ có số</h3>
      <table class="tgrid"><thead><tr><th class="name borrow">mượn từ tr. 100</th><th>MMR</th><th>U5MR</th><th>NMR</th></tr></thead><tbody>${R.map(rrow).join('')}</tbody></table></div>
    <p class="tnote">${chip('table', 4)} <span>Cột viền nét đứt là cột được ghép sang. Số liệu lấy nguyên từ hai viên <code class="src">${shortId(ex.table.leftId)}</code> và <code class="src">${shortId(ex.table.rightId)}</code>.</span></p>`;
}

/* ---------------- step 4: figure ---------------- */
const descModels = `${S.described}/${S.figures}`;
$('#spec4').innerHTML = `
  <li><span class="v">${S.figures}</span><span>hình, cắt từ chú thích tới dòng Source</span></li>
  <li><span class="v">${descModels}</span><span>hình đã có mô tả thị giác</span></li>
  <li><span class="v">${S.figurePages}</span><span>trang có hình</span></li>`;
$('#ex-figure').innerHTML = `
  <figure class="crop"><img src="./crops/${esc(ex.figure.crop)}" alt="${esc(ex.figure.caption)}: hai biểu đồ cột về tỷ lệ người sống với HIV biết tình trạng, được điều trị và ức chế virus." loading="lazy">
    <figcaption>${esc(ex.figure.id)} · trang ${ex.figure.page}</figcaption></figure>
  <div class="parts3">
    <div class="part3"><h3>Chú thích</h3><p>${esc(ex.figure.caption)}</p></div>
    <div class="part3"><h3>Lớp chữ trong hình</h3><p>${esc(ex.figure.layer)}…</p></div>
    <div class="part3 part3--red"><h3>Mô tả thị giác</h3><p>${ex.figure.desc ? esc(ex.figure.desc.replace(/\s+/g, ' ')) + '…' : 'Chưa có mô tả cho hình này.'}</p></div>
  </div>`;

/* ---------------- step 5: baseplate + page picker ---------------- */
$('#say5').innerHTML = `Ba loại viên dùng chung một khuôn: id, chữ, trang, loại. Tất cả được embedding bằng <b>${esc(S.embedModel || 'gemini-embedding-001')}</b> (${S.dims || 768} chiều) rồi nằm trong một bảng pgvector. Mỗi ô dưới đây là một viên thật, xếp theo thứ tự trang.`;
const chunks = DATA.chunks;
const plate = $('#plate');
plate.innerHTML = chunks.map((c, n) => `<button class="pc pc--${c.k}" data-n="${n}" tabindex="${n === 0 ? 0 : -1}" aria-label="${KIND[c.k]}, trang ${c.p}"></button>`).join('');
const pcs = $$('.pc', plate);
const pagesEl = $('#pages');
pagesEl.innerHTML = DATA.pages.map((p) => {
  const tot = p.text + p.table + p.figure;
  if (!tot) return `<button class="pg pg--blank" data-p="${p.p}" role="option" aria-selected="false" aria-disabled="true" tabindex="-1" aria-label="Trang ${p.p}, không có viên"></button>`;
  const seg = (n, c) => (n ? `<i class="${c}" style="height:${(n / tot) * 100}%"></i>` : '');
  return `<button class="pg" data-p="${p.p}" role="option" aria-selected="false" aria-label="Trang ${p.p}: ${p.text} text, ${p.table} bảng, ${p.figure} hình">${seg(p.text, 't')}${seg(p.table, 'b')}${seg(p.figure, 'f')}</button>`;
}).join('');
$('#legend').innerHTML = ['text', 'table', 'figure'].map((k) => `<li>${chip(k)}<span class="x">${S.byKind[k]}</span><span>${KIND[k]}</span></li>`).join('') +
  `<li><span class="x">${S.dbRows ?? S.chunks}</span><span>dòng trong pgvector</span></li>`;

const piece = $('#piece');
function showPiece(n, pageList) {
  const c = chunks[n];
  pcs.forEach((b) => b.classList.remove('is-sel'));
  pcs[n].classList.add('is-sel');
  pcs.forEach((b) => (b.tabIndex = -1));
  pcs[n].tabIndex = 0;
  const list = pageList || chunks.map((x, i) => [x, i]).filter(([x]) => x.p === c.p).map(([, i]) => i);
  const body = c.k === 'figure'
    ? `<img class="piece__img" src="./crops/${esc(c.crop)}" alt="${esc(c.cap)}" loading="lazy"><p class="piece__txt">${esc(c.cap)}\n\n${c.hasDesc ? esc(c.desc) + '…' : esc(c.layer)}</p>`
    : `<p class="piece__txt">${esc(c.t)}${c.n > 320 ? '…' : ''}</p>`;
  piece.innerHTML = `
    <p class="callout__title">Trang ${c.p} → ${list.length} viên</p>
    <div class="piece__list">${list.map((i) => `<button data-n="${i}" aria-pressed="${i === n}">${chip(chunks[i].k, 1)}${esc(shortId(chunks[i].id).replace(/^p\d+-/, ''))}</button>`).join('')}</div>
    <p class="piece__id">${esc(c.id)} · ${KIND[c.k]} · ${nf(c.n)} ký tự${c.rows ? ` · hàng ${esc(c.rows)}` : ''}</p>
    ${body}`;
}
function pickPage(p, animate = true) {
  const idx = chunks.map((c, i) => [c, i]).filter(([c]) => c.p === p).map(([, i]) => i);
  if (!idx.length) return;
  $$('.pg', pagesEl).forEach((b) => b.setAttribute('aria-selected', String(+b.dataset.p === p)));
  plate.classList.add('has-pick');
  pcs.forEach((b) => b.classList.remove('is-on'));
  idx.forEach((i) => pcs[i].classList.add('is-on'));
  showPiece(idx[0], idx);
  if (animate && !reduced) gsap.fromTo(idx.map((i) => pcs[i]), { y: -26 }, { y: 0, duration: 0.5, ease: 'expo.out', stagger: 0.04, clearProps: 'y' });
}
pagesEl.addEventListener('click', (e) => { const b = e.target.closest('.pg:not(.pg--blank)'); if (b) pickPage(+b.dataset.p); });
plate.addEventListener('click', (e) => { const b = e.target.closest('.pc'); if (b) pickPage(chunks[+b.dataset.n].p, false), showPiece(+b.dataset.n); });
piece.addEventListener('click', (e) => { const b = e.target.closest('.piece__list button'); if (b) showPiece(+b.dataset.n); });
plate.addEventListener('keydown', (e) => {
  const cur = +document.activeElement?.dataset?.n;
  if (Number.isNaN(cur)) return;
  const cols = getComputedStyle(plate).gridTemplateColumns.split(' ').length;
  const d = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols }[e.key];
  if (!d) return;
  e.preventDefault();
  const n = Math.max(0, Math.min(chunks.length - 1, cur + d));
  pcs[n].tabIndex = 0; pcs[n].focus();
  pickPage(chunks[n].p, false); showPiece(n);
});
pickPage(75, false);

/* ---------------- step 6: benchmark ---------------- */
const B = DATA.benchmark;
const GROUPS = [['table', 'Bảng'], ['image', 'Ảnh, sơ đồ'], ['chart', 'Biểu đồ'], ['multihop', 'Multi-hop'], ['text', 'Text'], ['unanswerable', 'Thiếu bằng chứng']];
const devN = B.dev.length;
$('#devbag').innerHTML = `<h3>Túi dev · ${devN} câu</h3><p>Mở để thử và chọn cấu hình. Bấm một câu để xem bằng chứng của nó.</p>
  <div class="groups">${GROUPS.map(([g, label]) => {
    const qs = B.dev.filter((q) => q.group === g);
    return `<div class="group"><h4>${label} · ${qs.length}</h4><ul>${qs.map((q) => `<li><button class="qb" data-id="${q.id}" aria-pressed="false">${q.id}</button></li>`).join('')}</ul></div>`;
  }).join('')}</div>`;
$('#testbag').innerHTML = `<h3>Túi test · ${B.testCount} câu</h3><p>Chưa mở. Không câu nào trong túi này được hiện ở đây.</p>
  <ul class="sealed-counts">${GROUPS.map(([g, label]) => `<li><span>${label}</span><span class="x">${B.counts[`test/${g}`] ?? 0}</span></li>`).join('')}</ul>
  <p class="seal"><svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><rect x="4" y="10" width="16" height="11" rx="2" fill="none" stroke="#111" stroke-width="2.6"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="#111" stroke-width="2.6"/></svg>sha256 ${esc(B.testHash)}…</p>`;
function showQ(id) {
  const q = B.dev.find((x) => x.id === id);
  $$('.qb').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
  const gold = q.gold.map((g) => `<dd class="m">${esc(g.loc)}<br>${esc(g.chunk)}</dd>`).join('');
  $('#qcard').innerHTML = q.answerable
    ? `<h3>${esc(q.q)}</h3><dl><dt>Đáp án chuẩn</dt><dd>${esc(q.a)}</dd><dt>Bằng chứng${q.mode === 'all' ? ' (cần đủ cả ' + q.gold.length + ')' : ''}</dt>${gold}</dl>`
    : `<h3>${esc(q.q)}</h3><dl><dt>Hành vi mong đợi</dt><dd>Tìm, rồi nói rõ là không đủ bằng chứng.</dd><dt>Vì sao thiếu</dt><dd>${esc(q.why)}</dd></dl>`;
}
$('#devbag').addEventListener('click', (e) => { const b = e.target.closest('.qb'); if (b) showQ(b.dataset.id); });
showQ('d-im2');

/* ---------------- step 7: retrieval ---------------- */
const METHOD = {
  dense: ['Dense', 'embedding câu hỏi, tìm vector gần nhất trong pgvector'],
  bm25: ['BM25', 'khớp từ khóa trên chữ của viên'],
  hybrid: ['Hybrid', 'gộp thứ hạng dense và BM25 bằng RRF'],
  rerank: ['Rerank', 'LLM xếp lại 15 ứng viên của hybrid'],
  rewrite: ['Viết lại query', 'LLM viết thêm 2 câu tìm, gộp bằng RRF'],
  multistage: ['Nhiều chặng', 'tìm, đọc, hỏi tiếp phần còn thiếu'],
};
if (hasRetrieval) {
  const R = DATA.retrieval;
  const answerable = B.dev.filter((q) => q.answerable);
  let cfg = 0;
  let qid = 'd-mh2';
  const sel = $('#qsel');
  sel.innerHTML = answerable.map((q) => `<option value="${q.id}">${q.id} · ${esc(q.q.length > 78 ? q.q.slice(0, 76) + '…' : q.q)}</option>`).join('');
  sel.value = qid;
  const seat = '<svg class="rk__seat" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8.6" fill="#fff" stroke="#111" stroke-width="2"/><path d="M5.6 10.4l2.9 2.9 5.6-6" fill="none" stroke="#0F5FB8" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const render = (animate) => {
    const c = R.configs[cfg];
    const q = answerable.find((x) => x.id === qid);
    $('#say7').innerHTML = `Mỗi cột là một cách tìm, chạy trên cùng ${c.methods[0].n} câu dev có đáp án. Viên có dấu khớp là viên chứa bằng chứng. Kết quả dưới đây đo trên ${esc(c.note)}.`;
    $('#configs').innerHTML = R.configs.length > 1 ? R.configs.map((x, i) => `<button data-i="${i}" aria-pressed="${i === cfg}">${x.label === 'final' ? 'Có mô tả hình' : 'Chưa có mô tả hình'}</button>`).join('') : '';
    $('#asked').innerHTML = `<b>${esc(q.q)}</b> Cần ${q.mode === 'all' ? `đủ ${q.gold.length} bằng chứng` : 'một bằng chứng'}: ${q.gold.map((g) => `tr. ${g.p}`).join(' và ')}.`;
    $('#methods').innerHTML = c.methods.map((m) => {
      const [name, sub] = METHOD[m.method] || [m.method, ''];
      const r = m.q[qid];
      const rows = r.top.map((t, i) => `<li class="rk rk--${i + 1} rk--${t.k}${t.hit ? ' rk--hit' : ''}"><span class="rk__n">${i + 1}</span><span class="rk__t">tr. ${t.p} · ${KIND[t.k]}<br>${esc(shortId(t.id).replace(/^p\d+-/, ''))}</span>${t.hit ? seat : ''}</li>`).join('');
      const studs = answerable.map((x) => `<i class="${m.q[x.id]?.hit3 ? 'on' : ''}${x.id === qid ? ' cur' : ''}" title="${x.id}"></i>`).join('');
      const extra = r.extra && r.extra.length ? `<p class="method__extra">Câu tìm thêm: ${r.extra.map(esc).join(' · ')}</p>` : '';
      return `<article class="method"><h3>${name}</h3><p class="method__sub">${sub}</p><ol class="rank">${rows}</ol>${extra}
        <div class="score"><p class="score__row"><span>Hit@3</span><span class="x">${m.hit3}</span></p><div class="studs" role="img" aria-label="Hit@3 ${m.hit3}">${studs}</div></div>
        <p class="method__meta">Hit@1 ${m.hit1} · MRR ${m.mrr}<br>${nf(Math.round(m.ms))} ms/câu · ${m.apiCalls} lượt gọi API</p></article>`;
    }).join('');
    if (animate && !reduced) gsap.from('#methods .rk', { y: -22, opacity: 0, duration: 0.45, ease: 'expo.out', stagger: { each: 0.035, grid: 'auto', from: 'start' } });
  };
  sel.addEventListener('change', () => { qid = sel.value; render(true); });
  $('#configs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { cfg = +b.dataset.i; render(true); } });
  render(false);
}

/* ---------------- step 8: agent trace ---------------- */
const CFG8 = { 'C-dense': ['Dense', 'tìm vector gần nhất'], 'D-hybrid-rerank': ['Hybrid + rerank', 'cấu hình retrieval đã chốt'] };
if (hasAgent) {
  const cfgs = Object.keys(AG.dev[0].by);
  let acfg = cfgs[cfgs.length - 1];
  let aq = (AG.dev.find((q) => q.answerable && q.group === 'multihop') || AG.dev[0]).id;
  let cite = null;
  const asel = $('#asel');
  asel.innerHTML = AG.dev.map((q) => `<option value="${q.id}">${q.id}${q.answerable ? '' : ' (thiếu evidence)'} · ${esc(q.q.length > 70 ? q.q.slice(0, 68) + '…' : q.q)}</option>`).join('');
  asel.value = aq;
  const st = (n) => (n === 1 ? '1 lượt tìm' : `${n} lượt tìm`);
  const render8 = (animate) => {
    const q = AG.dev.find((x) => x.id === aq);
    const r = q.by[acfg];
    $('#aconfigs').innerHTML = cfgs.map((c) => `<button data-c="${c}" aria-pressed="${c === acfg}">${(CFG8[c] || [c])[0]}</button>`).join('');
    $('#say8').innerHTML = `Agent không biết đáp án chuẩn. Nó tự nghĩ câu tìm, đọc các viên trả về, rồi trả lời kèm trích dẫn hoặc nói không đủ bằng chứng. Mỗi lượt tìm bên dưới là một lần gọi thật vào pgvector; viên có viền xanh nằm vừa trong ngân sách context.`;
    if (!r) { $('#trace').innerHTML = '<p class="asked">Cấu hình này chưa chạy câu này.</p>'; return; }
    const steps = r.steps.map((s, i) => `<li class="tl__step"><p class="tl__q"><span class="tl__n">${i + 1}</span><b>Tìm:</b> <q>${esc(s.query)}</q></p>
      <ol class="rank rank--row">${s.res.map((t, j) => `<li class="rk rk--${Math.min(j + 1, 5)} rk--${t.k}${s.ctx.includes(t.id) ? ' rk--in' : ' rk--out'}"><span class="rk__n">${j + 1}</span><span class="rk__t">tr. ${t.p} · ${KIND[t.k] || t.k}<br>${esc(shortId(t.id).replace(/^p\d+-/, ''))}</span></li>`).join('')}</ol></li>`).join('');
    const by = Object.fromEntries(r.cites.map((c) => [c.id, c]));
    const body = r.status === 'answered'
      ? esc(r.answer).replace(/\[([^\]]+)\]/g, (m, id) => (by[id] ? `<button class="cite" data-id="${esc(id)}" aria-pressed="${cite === id}">tr. ${by[id].p}</button>` : m))
      : r.status === 'abstain' ? `Không đủ bằng chứng để trả lời.${r.reason ? `<br><span class="why">Lý do của agent: ${esc(r.reason)}</span>` : ''}`
        : `Lỗi: ${esc(r.error)}`;
    const src = cite && by[cite] ? `<div class="citesrc"><p class="piece__id">${esc(shortId(cite))} · tr. ${by[cite].p} · ${KIND[by[cite].k] || ''}</p><p class="piece__txt">${esc(by[cite].t)}</p></div>` : (r.cites.length ? '<p class="hintline">Bấm một trích dẫn để đọc đoạn nguồn của nó.</p>' : '');
    const end = `<li class="tl__step tl__end tl__end--${r.status}"><p class="tl__q"><span class="tl__n">${r.status === 'answered' ? '✓' : r.status === 'abstain' ? '–' : '!'}</span><b>${r.status === 'answered' ? 'Trả lời' : r.status === 'abstain' ? 'Từ chối' : 'Lỗi'}</b></p><p class="ans">${body}</p>${src}</li>`;
    const expected = q.answerable ? `<p class="meta8"><b>Đáp án chuẩn (chỉ để đối chiếu):</b> ${esc(q.expected)}</p>` : '<p class="meta8"><b>Câu này tài liệu không trả lời được.</b> Hành vi đúng là từ chối.</p>';
    $('#trace').innerHTML = `<p class="asked"><b>${esc(q.q)}</b></p><ol class="tl">${steps}${end}</ol>${expected}
      <p class="method__meta">${st(r.steps.length)} · ${nf(Math.round(r.ms))} ms · ${nf(r.tokens)} token · context cuối ${nf(r.ctxChars)} ký tự${r.goldIn === null ? '' : ` · bằng chứng chuẩn ${r.goldIn ? 'có' : 'không có'} trong context`}</p>`;
    if (animate && !reduced) gsap.from('#trace .tl__step', { y: -26, opacity: 0, duration: 0.5, ease: 'expo.out', stagger: 0.12 });
  };
  asel.addEventListener('change', () => { aq = asel.value; cite = null; render8(true); });
  $('#aconfigs').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { acfg = b.dataset.c; cite = null; render8(true); } });
  $('#trace').addEventListener('click', (e) => { const b = e.target.closest('.cite'); if (b) { cite = cite === b.dataset.id ? null : b.dataset.id; render8(false); } });
  render8(false);
}

/* ---------------- step 9: test results ---------------- */
const RUN_LABEL = (name) => {
  const m = name.match(/^(day6|whs)-test-(.+)$/);
  const corpus = m[1] === 'day6' ? 'Day 6 · 7 câu' : 'WHO · 30 câu';
  const cfg = { 'A-dense': 'dense (baseline)', 'B-rerank': 'dense + rerank (chọn)', 'C-dense': 'dense (baseline)', 'D-hybrid-rerank': 'hybrid + rerank (chọn)' }[m[2]] || m[2];
  return [corpus, cfg];
};
if (hasTest) {
  const parts = [];
  if (TS.retrieval) {
    const n = TS.retrieval[0].n;
    parts.push(`<h3 class="t9h">Retrieval trên ${n} câu test có đáp án</h3><div class="methods methods--test">${TS.retrieval.map((m) => {
      const [name] = METHOD[m.method] || [m.method];
      const hit = +m.hit3.split('/')[0];
      const studs = Array.from({ length: n }, (_, i) => `<i class="${i < hit ? 'on' : ''}"></i>`).join('');
      const lock = m.method === TS.lockedRetrieval ? '<span class="lockflag">đã chốt</span>' : '';
      return `<article class="method${lock ? ' method--locked' : ''}"><h3>${name}${lock}</h3><div class="score"><p class="score__row"><span>Hit@3</span><span class="x">${m.hit3}</span></p><div class="studs studs--24" role="img" aria-label="Hit@3 ${m.hit3}">${studs}</div></div>
        <p class="method__meta">Hit@1 ${m.hit1} · Hit@5 ${m.hit5} · MRR ${m.mrr}<br>${Object.entries(m.byGroup).map(([g, v]) => `${({ table: 'bảng', image: 'hình', chart: 'biểu đồ', multihop: 'multi-hop', text: 'text' })[g] || g} ${v}`).join(' · ')}</p></article>`;
    }).join('')}</div>`);
  }
  $('#tbench').innerHTML = parts.join('');
  const card = ([name, r]) => {
    const [corpus, cfg] = RUN_LABEL(name);
    const rv = r.review;
    const gi = r.answerable_gold_in_final_context;
    const graded = rv
      ? `<dl class="grade"><dt>Câu trả lời (tự chấm)</dt><dd>${rv.grounded_answer.mean === null ? '—' : rv.grounded_answer.mean.toFixed(2)} / 2 · ${rv.grounded_answer['0']}×0, ${rv.grounded_answer['1']}×1, ${rv.grounded_answer['2']}×2</dd>
          <dt>Citation hỗ trợ</dt><dd>${rv.citation_validity.n}/${rv.citation_validity.N}</dd><dt>Từ chối đúng</dt><dd>${rv.abstention.n}/${rv.abstention.N}</dd><dt>Từ chối oan</dt><dd>${rv.false_abstention.n}/${rv.false_abstention.N}</dd></dl>`
      : '<p class="ungraded">Chưa có nhãn chấm tay. Số liệu bên dưới chỉ là đếm tự động.</p>';
    const GL = { table: 'bảng', image: 'hình', chart: 'biểu đồ', multihop: 'multi-hop', text: 'text', unanswerable: 'thiếu evidence' };
    const pass = r.pass && r.corpus === 'whs'
      ? `<div class="passbox"><p class="score__row"><span>Đạt</span><span class="x">${r.pass.n}</span></p><p class="method__meta">${r.pass.rate}% · ${r.pass.needs27 ? 'vượt ngưỡng 27/30' : 'chưa tới 27/30'}<br>${Object.entries(r.pass.byGroup).map(([g, v]) => `${GL[g] || g} ${v}`).join(' · ')}</p></div>` : '';
    return `<article class="method acard${r.pass && r.pass.needs27 ? ' method--locked' : ''}"><h3>${esc(cfg)}</h3><p class="method__sub">${esc(corpus)}</p>${pass}${graded}
      <p class="method__meta">Trả lời ${r.status.answered || 0} · từ chối ${r.status.abstain || 0} · lỗi ${r.status.error || 0}<br>Dùng tool ${r.tool_use} · bằng chứng trong context ${gi}<br>${nf(Math.round(r.seconds_total))} s · ${nf(r.prompt_tokens + r.output_tokens)} token · ${r.api_calls} lượt gọi API</p></article>`;
  };
  $('#atests').innerHTML = testRuns.length ? `<h3 class="t9h">Agent trên túi test</h3><div class="methods">${testRuns.map(card).join('')}</div>` : '';
  $('#say9').innerHTML = 'Túi test chỉ mở một lần, sau khi cấu hình được khoá. Không câu hỏi nào được hiện ở đây, chỉ có số đếm.';
}

/* ---------------- box ---------------- */
$('#box').innerHTML = `
  <div><dt>Tài liệu nguồn</dt><dd>${esc(DATA.source.title)}. ${esc(DATA.source.publisher)}, ISBN ${esc(DATA.source.isbn)}, ${DATA.source.pages} trang. Giấy phép ${esc(DATA.source.license)}.<br><a href="${esc(DATA.source.url)}">Trang tài liệu trên who.int</a></dd></div>
  <div><dt>Index</dt><dd>${S.dbRows ?? S.chunks} dòng trong PostgreSQL + pgvector, cosine. ${esc(S.embedModel || '')}, ${S.dims || ''} chiều.${S.indexSeconds ? ` Lần nạp đầu mất ${nf(Math.round(S.indexSeconds))} giây, ${S.indexApiCalls} lượt gọi API.` : ''}</dd></div>
  <div><dt>Lắp lại từ đầu</dt><dd><code>python bonus/extract.py --pdf …</code><br><code>python bonus/describe_figures.py</code><br><code>python bonus/build_chunks.py</code><br><code>python bonus/index.py</code><br><code>python bonus/eval_retrieval.py --split dev</code></dd></div>
  <div><dt>Chạy agent</dt><dd><code>python src/run_agent_eval.py --corpus whs --split dev --config D-hybrid-rerank --method hybrid_rerank --budget 12000</code><br>Nhãn chấm tay đặt trong <code>reviews.json</code> cạnh <code>traces.json</code>; deck đọc lại khi build.</dd></div>`;

/* ---------------- motion ---------------- */
function entrances() {
  if (reduced) return;
  $$('.spread:not(.spread--tall)').forEach((sp) => {
    const els = $$('.num, h2, .say, .spec li, .callout, .tpage, .tnote, .crop, .part3, .pickrow, .plate, .legend, .bagbox, .askrow, .asked, .method, .box > div', sp);
    if (!els.length) return;
    gsap.from(els, { y: -34, opacity: 0, duration: 0.7, ease: 'expo.out', stagger: 0.05, clearProps: 'transform,opacity', scrollTrigger: { trigger: sp, start: 'top 72%', once: true } });
  });
  gsap.from('#plate .pc', { y: -22, opacity: 0, duration: 0.4, ease: 'expo.out', stagger: { each: 0.0022 }, clearProps: 'transform,opacity', scrollTrigger: { trigger: '#plate', start: 'top 80%', once: true } });
}

function start() {
  animateScene1();
  entrances();
  ScrollTrigger.refresh();
}
if (document.fonts && document.fonts.ready) document.fonts.ready.then(start); else start();
