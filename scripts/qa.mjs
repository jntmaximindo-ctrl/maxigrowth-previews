// usage: node scripts/qa.mjs <site/index.html> <outdir>
// Gerbang G4 (teknis): error console/page, overflow horizontal di 390px, target sentuh < 44px,
// gambar tanpa alt, link target=_blank tanpa noopener, host eksternal di luar daftar izin.
// Screenshot desktop & mobile untuk QC visual. Keluar kode 1 bila ada masalah wajib.
import fs from 'fs'; import path from 'path';
import { chromium } from 'playwright';

const [, , file, out] = process.argv; fs.mkdirSync(out, { recursive: true });
const IZIN = /^(https?:\/\/)?([a-z0-9-]+\.)*(fonts\.googleapis\.com|fonts\.gstatic\.com|cdnjs\.cloudflare\.com|maps\.google\.com|maps\.googleapis\.com|maps\.gstatic\.com|www\.google\.com|google\.com|wa\.me|api\.whatsapp\.com|waze\.com|maxigrowthstudio\.com)(\/|$)/i;
const report = { file, when: new Date().toISOString(), pass: true, desktop: {}, mobile: {} };
const b = await chromium.launch();
for (const [tag, vp] of [['desktop', { width: 1366, height: 860 }], ['mobile', { width: 390, height: 844 }]]) {
  const p = await b.newPage({ viewport: vp, deviceScaleFactor: 1, hasTouch: tag === 'mobile' });
  const errs = [], ext = new Set();
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errs.push(m.text()); });
  p.on('request', (r) => { const u = r.url(); if (/^https?:/.test(u) && !IZIN.test(u)) ext.add(new URL(u).host); });
  await p.goto('file://' + path.resolve(file), { waitUntil: 'load' });
  await p.addStyleTag({ content: '*{animation:none!important;transition:none!important}.rv,[data-reveal]{opacity:1!important;transform:none!important}' });
  await p.waitForTimeout(1200);
  const r = await p.evaluate((mobile) => {
    const overflowX = document.documentElement.scrollWidth - innerWidth;
    const kecil = []; const noAlt = []; const noOpener = [];
    for (const el of document.querySelectorAll('a[href],button,input,select,textarea,[role=button]')) {
      const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      if (!b.width || cs.visibility === 'hidden' || cs.display === 'none') continue;
      if (mobile && (b.width < 44 || b.height < 44) && !el.closest('p,li,td,.inline,svg,[data-qa-skip]')) kecil.push((el.innerText || el.getAttribute('aria-label') || el.tagName).trim().slice(0, 40) + ` (${Math.round(b.width)}×${Math.round(b.height)})`);
    }
    document.querySelectorAll('img:not([alt])').forEach((i) => noAlt.push(i.src.slice(0, 80)));
    document.querySelectorAll('a[target=_blank]').forEach((a) => { if (!/noopener/.test(a.rel)) noOpener.push(a.href.slice(0, 80)); });
    const lebar = [...document.querySelectorAll('body *')].filter((e) => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 5).map((e) => e.tagName + (e.className ? '.' + String(e.className).split(' ')[0] : ''));
    return { overflowX, kecil: kecil.slice(0, 15), jumlahKecil: kecil.length, noAlt, noOpener, penyebabOverflow: lebar };
  }, tag === 'mobile');
  await p.screenshot({ path: `${out}/${tag}-hero.png` });
  await p.screenshot({ path: `${out}/${tag}-penuh.png`, fullPage: true });
  Object.assign(report[tag], r, { errors: errs, hostLuarIzin: [...ext] });
  if (errs.length || r.overflowX > 0 || ext.size || r.noOpener.length) report.pass = false;
  // target sentuh kecil = peringatan untuk QC visual; gagal hanya jika sangat banyak (denah gigi SVG dikecualikan)
  if (tag === 'mobile' && r.jumlahKecil > 12) report.pass = false;
  await p.close();
}
await b.close();
fs.writeFileSync(`${out}/qa-report.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify({ pass: report.pass, d: { err: report.desktop.errors.length, ox: report.desktop.overflowX }, m: { err: report.mobile.errors.length, ox: report.mobile.overflowX, kecil: report.mobile.jumlahKecil }, ext: report.desktop.hostLuarIzin }));
process.exit(report.pass ? 0 : 1);
