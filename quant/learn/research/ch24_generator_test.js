// Independent check of the chapter 24 daily-practice generator.
// Run: node research/ch24_generator_test.js
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../chapters/24-daily-practice.html'), 'utf8');
const src = html.split('/*GEN-START*/')[1].split('/*GEN-END*/')[0];
const GEN = new Function(src + ';return GEN;')();

const close = (a, b) => Math.abs(a - b) < 0.006;
const g = (a, b) => { a = Math.abs(a); b = Math.abs(b); while (b) [a, b] = [b, a % b]; return a; };
const YRS = [2021, 2022, 2023, 2024];

// --- independent solvers (do not reuse generator code) ---
function quadRoots([a, b, c]) {
  const D = b * b - 4 * a * c; if (D < 0) throw 'complex roots';
  const s = Math.sqrt(D); if (Math.abs(Math.round(s) ** 2 - D) > 0) throw 'irrational roots';
  return [(-b - s) / (2 * a), (-b + s) / (2 * a)];
}
function relation(xs, ys) {
  const e = 1e-9, mnx = Math.min(...xs), mxx = Math.max(...xs), mny = Math.min(...ys), mxy = Math.max(...ys);
  if (Math.abs(mnx - mxx) < e && Math.abs(mny - mxy) < e && Math.abs(mnx - mny) < e) return 'x = y or relation cannot be established';
  if (mnx > mxy + e) return 'x > y';
  if (Math.abs(mnx - mxy) < e) return 'x ≥ y';
  if (mxx < mny - e) return 'x < y';
  if (Math.abs(mxx - mny) < e) return 'x ≤ y';
  return 'x = y or relation cannot be established';
}
function fitsFamily(s) {
  const d = s.slice(1).map((v, i) => v - s[i]);
  const ap = d.every(x => x === d[0]);
  const d2 = d.slice(1).map((v, i) => v - d[i]); const sec = d2.every(x => x === d2[0]);
  const gp = s.every(v => v !== 0) && s.slice(1).every((v, i) => Math.abs(v / s[i] - s[1] / s[0]) < 1e-12);
  return ap || sec || gp;
}
function expected(q) {
  const p = q.p;
  switch (q.k) {
    case 'diPctOf': return p.rows[0][p.j] / p.rows[1][p.j] * 100;
    case 'diPctChg': { const o = p.rows[p.row][p.j], n = p.rows[p.row][p.j + 1]; return Math.abs(n - o) / o * 100; }
    case 'diRatio': { const a = p.rows[0][p.j] + p.rows[0][p.j + 1], b = p.rows[1][p.j] + p.rows[1][p.j + 1]; return a / b; }
    case 'quad': return relation(quadRoots(p.cx), quadRoots(p.cy));
    case 'series': return null; // checked by option-fit below
    case 'simp': return p.A / p.B * p.C + p.D - p.E ** 2;
    case 'approx': return Math.round(p.pd) / 100 * (Math.round(p.bd / 10) * 10) + Math.round(p.xd) * Math.round(p.yd);
    case 'sPct': return p.P * (1 + p.a / 100) * (1 - p.b / 100);
    case 'sAvg': return (p.n + 1) * p.B - p.n * p.A;
    case 'sPart': return p.T * (p.q * p.m) / (p.p * 12 + p.q * p.m);
    case 'sCI': return p.P * (1 + p.r / 100) ** 2 - p.P;
    case 'sTrain': return (p.L + p.M) / (p.v * 1000 / 3600);
    case 'sWork': return 1 / (1 / p.a + 1 / p.b);
    case 'sPL1': return p.SP / (1 + p.p / 100);
    case 'sPL2': return p.MP * (1 - p.d1 / 100) * (1 - p.d2 / 100);
  }
  throw 'unknown kind ' + q.k;
}
const num = s => parseFloat(String(s).replace(/[₹,%]/g, '').replace('−', '-'));

let fails = [], n = 0, kinds = {}, answerPos = {}, quadRel = {};
const fail = (seed, q, msg) => { if (fails.length < 30) fails.push(`${seed} ${q.k}: ${msg} | ${q.q} | ${q.opts.join(' / ')}`); else fails.length++; };
const start = new Date(Date.UTC(2026, 0, 1));
for (let s = 0; s < 2000; s++) {
  const d = new Date(start.getTime() + s * 864e5), seed = d.toISOString().slice(0, 10) + (s % 3 === 0 ? '' : '#' + (s % 7));
  const set = GEN.makeSet(seed), again = GEN.makeSet(seed);
  if (JSON.stringify(set) !== JSON.stringify(again)) fails.push(seed + ': same seed gave different set');
  if (set.length !== 20) fails.push(seed + ': set size ' + set.length);
  const counts = {}; set.forEach(q => { const c = q.k.startsWith('di') ? 'di' : q.k.startsWith('s') && q.k !== 'simp' && q.k !== 'series' ? 'single' : q.k; counts[c] = (counts[c] || 0) + 1; });
  if (counts.di !== 6 || counts.quad !== 3 || counts.series !== 3 || (counts.simp || 0) + (counts.approx || 0) !== 2 || counts.single !== 6) fails.push(seed + ': mix ' + JSON.stringify(counts));
  for (const q of set) {
    n++; kinds[q.k] = (kinds[q.k] || 0) + 1;
    const nOpt = q.opts.length;
    if (nOpt !== (q.k === 'quad' ? 5 : 4)) fail(seed, q, 'option count ' + nOpt);
    if (new Set(q.opts).size !== nOpt) fail(seed, q, 'duplicate options');
    if (q.why.length !== nOpt || q.why.filter(w => w === '').length !== 1 || q.why[q.a] !== '') fail(seed, q, 'explanations mismatch');
    if (q.why.some((w, i) => i !== q.a && !(w && w.length > 10))) fail(seed, q, 'missing mistake explanation');
    if (/NaN|undefined|Infinity|null/.test(JSON.stringify([q.q, q.opts, q.sol, q.why, q.tbl || '']))) fail(seed, q, 'bad token in text');
    answerPos[q.a] = (answerPos[q.a] || 0) + 1;
    if (q.k === 'quad') {
      const e = expected(q); quadRel[e] = (quadRel[e] || 0) + 1;
      if (q.opts.filter(o => o === e).length !== 1 || q.opts[q.a] !== e) fail(seed, q, 'quad relation expected ' + e + ' got ' + q.opts[q.a]);
      continue;
    }
    if (q.k === 'series') {
      const fit = q.opts.map(o => { const v = num(o); let full = q.p.shown.slice(); if (q.p.miss) full[q.p.pos] = v; else full.push(v); return fitsFamily(full); });
      if (fit.filter(Boolean).length !== 1 || !fit[q.a]) fail(seed, q, 'series fit ' + fit);
      // visible terms alone must fit exactly one prediction across families
      if (q.opts.map(num).some(v => !(v > 0) || v !== Math.floor(v))) fail(seed, q, 'non-positive/non-integer term');
      continue;
    }
    if (q.k === 'diRatio') {
      const e = expected(q);
      const vals = q.opts.map(o => { const [a, b] = o.split(' : ').map(Number); if (g(a, b) !== 1 || !(a > 0 && b > 0)) fail(seed, q, 'ratio not simplified/positive ' + o); return a / b; });
      if (vals.filter(v => Math.abs(v - e) < 1e-9).length !== 1 || Math.abs(vals[q.a] - e) > 1e-9) fail(seed, q, 'ratio answer');
      if (q.p.rows.flat().some(v => !(v > 0) || v !== Math.floor(v))) fail(seed, q, 'bad table cell');
      continue;
    }
    const e = expected(q), vals = q.opts.map(num);
    if (vals.some(v => !(v > 0))) fail(seed, q, 'non-positive option');
    if (vals.some(v => v > 1e7)) fail(seed, q, 'huge option');
    if (vals.filter(v => close(v, e)).length !== 1 || !close(vals[q.a], e)) fail(seed, q, 'expected ' + e + ' got ' + q.opts[q.a]);
    if (q.k.startsWith('di') && q.p.rows.flat().some(v => !(v > 0) || v !== Math.floor(v))) fail(seed, q, 'bad table cell');
    if (q.k === 'approx') { // exact (unrounded) value must be nearest to the correct option
      const ex = q.p.pd / 100 * q.p.bd + q.p.xd * q.p.yd, dist = vals.map(v => Math.abs(v - ex)), best = dist.indexOf(Math.min(...dist));
      if (best !== q.a) fail(seed, q, 'approx nearest option is not the answer');
    }
    if (['sPct', 'sAvg', 'sTrain', 'sWork', 'sCI', 'sPL1', 'sPL2', 'sPart', 'simp', 'diPctOf', 'diPctChg'].includes(q.k) && Math.abs(e - Math.round(e * 100) / 100) > 1e-6) fail(seed, q, 'correct answer not clean: ' + e);
  }
}
console.log('seeds: 2000, questions:', n);
console.log('by kind:', JSON.stringify(kinds));
console.log('answer position counts:', JSON.stringify(answerPos));
console.log('quad relations:', JSON.stringify(quadRel));
console.log(fails.length ? 'FAIL ' + fails.length + '\n' + fails.slice(0, 30).join('\n') : 'ALL CHECKS PASSED');
process.exit(fails.length ? 1 : 0);
