import { Chess } from './chess.js';

// <pure>
function parseInfo(line) {
  if (!line.startsWith('info') || !/ pv /.test(line)) return null;
  const mp = / multipv (\d+)/.exec(line);
  const sc = / score (cp|mate) (-?\d+)/.exec(line);
  const pv = / pv (.+)$/.exec(line);
  const dp = / depth (\d+)/.exec(line);
  if (!sc || !pv) return null;
  return { idx: mp ? +mp[1] : 1, depth: dp ? +dp[1] : 0, kind: sc[1], val: +sc[2], pv: pv[1].trim().split(/\s+/) };
}

function pvToSan(ChessCls, fen, pv, n) {
  const c = new ChessCls(fen);
  const out = [];
  for (let i = 0; i < Math.min(n, pv.length); i++) {
    const parts = c.fen().split(' ');
    const turn = parts[1], num = parts[5];
    const u = pv[i];
    let m;
    try { m = c.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }); } catch (e) { m = null; }
    if (!m) break;
    out.push(turn === 'w' ? num + '. ' + m.san : (i === 0 ? num + '... ' + m.san : m.san));
  }
  return out.join(' ');
}

// score is given from the side to move; sign converts it to White's view
function fmtScore(kind, valForMe) {
  if (kind === 'mate') return '#' + valForMe;
  return (valForMe >= 0 ? '+' : '-') + Math.abs(valForMe / 100).toFixed(2);
}
// </pure>

const GLYPH = { p: '♟', n: '♞', b: '♝', r: '♜', q: '♛', k: '♚' };
const $ = (id) => document.getElementById(id);

let chess = new Chess();
let flipped = false;          // false = I play White, true = I play Black
let selected = null;
let targets = [];
let lines = {};
let whiteShare = 0.5;
let barLabel = '0.00';
let ready = false, searching = false, restart = false, searchFen = '';
let renderTimer = null;

// ---------- engine ----------
const worker = new Worker('engine/stockfish-19-lite-single.js');
const send = (cmd) => worker.postMessage(cmd);
worker.onerror = (e) => { $('info').textContent = 'Engine failed to load: ' + (e.message || 'unknown error'); };
worker.onmessage = (e) => onLine(String(e.data));

send('uci');

function onLine(line) {
  if (line === 'uciok') {
    send('setoption name MultiPV value 3');
    send('isready');
  } else if (line === 'readyok') {
    ready = true;
    analyse();
  } else if (line.startsWith('bestmove')) {
    searching = false;
    if (restart) { restart = false; analyse(); } else { render(); }
  } else if (line.startsWith('info')) {
    if (restart) return;
    const p = parseInfo(line);
    if (p && p.idx <= 3) { lines[p.idx] = p; scheduleRender(); }
  }
}

function analyse() {
  lines = {};
  if (!ready) return;
  if (chess.isGameOver()) { render(); return; }
  if (searching) { restart = true; send('stop'); return; }
  searching = true;
  restart = false;
  searchFen = chess.fen();
  send('position fen ' + searchFen);
  send('go movetime 1500');
  render();
}

function scheduleRender() {
  if (renderTimer) return;
  renderTimer = setTimeout(() => { renderTimer = null; render(); }, 120);
}

// ---------- rendering ----------
function render() {
  drawBoard();
  drawInfo();
  drawBar();
}

function squareName(file, rank) { return 'abcdefgh'[file] + (rank + 1); }

function drawBoard() {
  const hist = chess.history({ verbose: true });
  const last = hist.length ? hist[hist.length - 1] : null;
  const capTargets = new Set(targets.filter((m) => m.captured || m.flags.includes('e')).map((m) => m.to));
  const tset = new Set(targets.map((m) => m.to));
  let html = '';
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const file = flipped ? 7 - c : c;
      const rank = flipped ? r : 7 - r;
      const sq = squareName(file, rank);
      const light = (file + rank) % 2 === 1;
      const cls = ['sq', light ? 'l' : 'd'];
      if (last && (sq === last.from || sq === last.to)) cls.push('last');
      if (sq === selected) cls.push('sel');
      if (tset.has(sq)) { cls.push('target'); if (capTargets.has(sq)) cls.push('cap'); }
      const attrs = (r === 7 ? ` data-f="${'abcdefgh'[file]}"` : '') + (c === 0 ? ` data-r="${rank + 1}"` : '');
      const p = chess.get(sq);
      const glyph = p ? `<span class="${p.color}">${GLYPH[p.type]}\uFE0E</span>` : '';
      html += `<div class="${cls.join(' ')}" data-sq="${sq}"${attrs}>${glyph}</div>`;
    }
  }
  const best = lines[1] ? lines[1].pv[0] : null;
  html += arrowSvg(best);
  $('board').innerHTML = html;
}

function arrowSvg(uci) {
  if (!uci || chess.isGameOver()) return '';
  const pos = (sq) => {
    const f = sq.charCodeAt(0) - 97, rk = +sq[1] - 1;
    return [(flipped ? 7 - f : f) + 0.5, (flipped ? rk : 7 - rk) + 0.5];
  };
  const [x1, y1] = pos(uci.slice(0, 2));
  const [x2, y2] = pos(uci.slice(2, 4));
  return `<svg id="arrow" viewBox="0 0 8 8"><defs><marker id="ah" markerWidth="4" markerHeight="4" refX="2.2" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 z" fill="#3a9d4a"/></marker></defs><line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#3a9d4a" stroke-width="0.16" stroke-opacity="0.8" marker-end="url(#ah)"/></svg>`;
}

function whiteView(p) {
  const sign = searchFen.split(' ')[1] === 'w' ? 1 : -1;
  return p.val * sign;
}

function drawInfo() {
  const me = flipped ? 'Black' : 'White';
  if (!ready) { $('info').textContent = 'Loading engine…'; return; }
  if (chess.isGameOver()) {
    let t = 'Game over: ';
    if (chess.isCheckmate()) t += (chess.turn() === 'w' ? 'Black' : 'White') + ' wins by checkmate';
    else t += 'draw';
    $('info').textContent = t;
    whiteShare = chess.isCheckmate() ? (chess.turn() === 'w' ? 0 : 1) : 0.5;
    barLabel = chess.isCheckmate() ? (chess.turn() === 'w' ? '0-1' : '1-0') : '½';
    return;
  }
  const sign = flipped ? -1 : 1;
  const rows = [`Eval from ${me}'s view (${chess.turn() === 'w' ? 'White' : 'Black'} to move)${searching ? '  analysing…' : ''}`];
  for (let i = 1; i <= 3; i++) {
    const p = lines[i];
    if (!p) continue;
    const ev = fmtScore(p.kind, whiteView(p) * sign);
    if (i === 1) barLabel = ev;
    rows.push(`${i}. ${ev.padStart(6)}  ${pvToSan(Chess, searchFen, p.pv, 6)}`);
  }
  if (lines[1]) {
    const w = whiteView(lines[1]);
    whiteShare = lines[1].kind === 'mate' ? (w > 0 ? 1 : 0) : 1 / (1 + Math.exp(-w / 400));
  }
  $('info').textContent = rows.join('\n');
}

function drawBar() {
  const fill = $('fill'), label = $('barlabel');
  fill.style.height = (whiteShare * 100) + '%';
  fill.style.top = flipped ? '0' : 'auto';
  fill.style.bottom = flipped ? 'auto' : '0';
  const bottomIsWhite = !flipped;
  const bottomShare = bottomIsWhite ? whiteShare : 1 - whiteShare;
  const leadingBottom = bottomShare >= 0.5;
  const leadingWhite = leadingBottom ? bottomIsWhite : !bottomIsWhite;
  label.textContent = barLabel;
  label.style.top = leadingBottom ? 'auto' : '4px';
  label.style.bottom = leadingBottom ? '4px' : 'auto';
  label.style.color = leadingWhite ? '#000' : '#fff';
}

// ---------- interaction ----------
$('board').addEventListener('pointerdown', (e) => {
  const el = e.target.closest('[data-sq]');
  if (!el || chess.isGameOver()) return;
  const sq = el.dataset.sq;
  if (selected && targets.some((m) => m.to === sq)) {
    chess.move({ from: selected, to: sq, promotion: 'q' }); // auto-queen
    selected = null; targets = [];
    analyse();
    render();
    return;
  }
  const p = chess.get(sq);
  if (p && p.color === chess.turn()) {
    selected = sq;
    targets = chess.moves({ square: sq, verbose: true });
  } else {
    selected = null; targets = [];
  }
  render();
});

function reset() { selected = null; targets = []; lines = {}; analyse(); render(); }

$('sideBtn').addEventListener('click', () => {
  flipped = !flipped;
  $('sideBtn').textContent = flipped ? 'Play as White' : 'Play as Black';
  render();
});
$('undoBtn').addEventListener('click', () => { chess.undo(); reset(); });
$('newBtn').addEventListener('click', () => { chess = new Chess(); reset(); });
$('fenBtn').addEventListener('click', () => {
  const row = $('fenrow');
  row.style.display = row.style.display === 'flex' ? 'none' : 'flex';
});
$('fenLoad').addEventListener('click', () => {
  const fen = $('fenInput').value.trim();
  if (!fen) return;
  try { chess = new Chess(fen); } catch (e) { alert('Invalid FEN'); return; }
  $('fenrow').style.display = 'none';
  reset();
});
$('copyBtn').addEventListener('click', async () => {
  const fen = chess.fen();
  try { await navigator.clipboard.writeText(fen); $('copyBtn').textContent = 'Copied!'; }
  catch (e) { $('fenInput').value = fen; $('fenrow').style.display = 'flex'; $('copyBtn').textContent = 'FEN shown above'; }
  setTimeout(() => { $('copyBtn').textContent = 'Copy FEN'; }, 1500);
});

render();
