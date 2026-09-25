// usage: node scripts/brand_capture.mjs <url-or-file> <outdir>
// Screenshot situs lama (desktop + mobile, hero + halaman penuh) dan ekstraksi branding otomatis:
// kandidat warna hex (dibobot luas area), font yang dipakai, kandidat logo (URL + unduhan).
// Tanpa token AI. Hasil: <outdir>/brand-capture.json + PNG + logo-*.{png,svg,jpg,webp}
import fs from 'fs'; import path from 'path';
import { chromium } from 'playwright';

const [, , target, out] = process.argv;
fs.mkdirSync(out, { recursive: true });
const url = /^https?:/.test(target) ? target : 'file://' + path.resolve(target);
const result = { url: target, captured: new Date().toISOString(), ok: false, colors: [], fonts: [], logos: [], errors: [] };

const browser = await chromium.launch();
try {
  for (const [tag, vp] of [['desktop', { width: 1366, height: 860 }], ['mobile', { width: 390, height: 844 }]]) {
    const page = await browser.newPage({ viewport: vp, deviceScaleFactor: 1, userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36' });
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(2500);
      await page.screenshot({ path: `${out}/lama-${tag}-hero.png` });
      await page.screenshot({ path: `${out}/lama-${tag}-penuh.png`, fullPage: true }).catch(() => {});
      result.ok = true;
      if (tag !== 'desktop') { await page.close(); continue; }

      const data = await page.evaluate(() => {
        const toHex = (c) => {
          const m = c && c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/);
          if (!m || (m[4] !== undefined && +m[4] < 0.5)) return null;
          return '#' + [m[1], m[2], m[3]].map((x) => (+x).toString(16).padStart(2, '0')).join('');
        };
        const colors = {}, fonts = {};
        const add = (hex, w, kind) => { if (!hex) return; colors[hex] ??= { hex, weight: 0, kinds: {} };
          colors[hex].weight += w; colors[hex].kinds[kind] = (colors[hex].kinds[kind] || 0) + 1; };
        for (const el of document.querySelectorAll('body *')) {
          const r = el.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;
          const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
          const area = Math.min(r.width * r.height, 400000);
          add(toHex(cs.backgroundColor), area, 'bg');
          if (el.childNodes.length && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
            { add(toHex(cs.color), r.width * 20, 'text'); const f = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
              fonts[f] = (fonts[f] || 0) + r.width; }
          if (/^(A|BUTTON)$/.test(el.tagName)) add(toHex(cs.backgroundColor), 20000, 'cta');
          if (el.tagName === 'svg' || el.closest('svg')) add(toHex(cs.fill), area, 'svg');
        }
        const logos = [];
        const push = (src, why) => { if (src && !logos.some((l) => l.src === src)) logos.push({ src, why }); };
        for (const img of document.querySelectorAll('img')) {
          const s = (img.currentSrc || img.src || '') + ' ' + img.alt + ' ' + img.className + ' ' + (img.id || '');
          if (/logo/i.test(s)) push(img.currentSrc || img.src, 'img[logo]');
        }
        const hdr = document.querySelector('header, nav, .header, #header');
        hdr?.querySelectorAll('img').forEach((i) => push(i.currentSrc || i.src, 'header img'));
        hdr?.querySelectorAll('svg').forEach((s, i) => { if (i < 2) push('inline-svg:' + btoa(unescape(encodeURIComponent(s.outerHTML))).slice(0, 200000), 'header svg'); });
        document.querySelectorAll('link[rel*="icon"], meta[property="og:image"]').forEach((l) => push(l.href || l.content, l.rel || 'og:image'));
        const theme = document.querySelector('meta[name="theme-color"]')?.content || null;
        return { colors: Object.values(colors), fonts, logos, theme, title: document.title };
      });

      const neutral = (hex) => { const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
        const max = Math.max(r, g, b), min = Math.min(r, g, b); return max - min < 18 || max > 245 && min > 235 || max < 22; };
      result.title = data.title; result.theme_color = data.theme;
      result.colors = data.colors.filter((c) => !neutral(c.hex)).sort((a, b) => b.weight - a.weight).slice(0, 8)
        .map((c) => ({ hex: c.hex, share: 0, kinds: c.kinds, weight: Math.round(c.weight) }));
      const tot = result.colors.reduce((s, c) => s + c.weight, 0) || 1;
      result.colors.forEach((c) => { c.share = +(c.weight / tot).toFixed(3); delete c.weight; });
      result.neutrals = data.colors.filter((c) => neutral(c.hex)).sort((a, b) => b.weight - a.weight).slice(0, 4).map((c) => c.hex);
      result.fonts = Object.entries(data.fonts).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([f]) => f);

      let i = 0;
      for (const l of data.logos.slice(0, 6)) {
        i++;
        if (l.src.startsWith('inline-svg:')) {
          const svg = decodeURIComponent(escape(Buffer.from(l.src.slice(11), 'base64').toString('binary')));
          fs.writeFileSync(`${out}/logo-${i}.svg`, svg); result.logos.push({ file: `logo-${i}.svg`, why: l.why });
          continue;
        }
        try {
          const res = await page.request.get(l.src, { timeout: 20000 });
          if (!res.ok()) throw new Error('HTTP ' + res.status());
          const ct = res.headers()['content-type'] || ''; const ext = (ct.match(/(png|jpe?g|svg|webp|gif|x-icon|vnd\.microsoft\.icon)/) || ['', 'png'])[1].replace('jpeg', 'jpg').replace(/x-icon|vnd\.microsoft\.icon/, 'ico');
          fs.writeFileSync(`${out}/logo-${i}.${ext}`, await res.body());
          result.logos.push({ file: `logo-${i}.${ext}`, src: l.src, why: l.why });
        } catch (e) { result.logos.push({ src: l.src, why: l.why, error: String(e.message || e) }); }
      }
    } catch (e) { result.errors.push(`${tag}: ${e.message}`); }
    await page.close();
  }
} finally { await browser.close(); }

fs.writeFileSync(`${out}/brand-capture.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify({ ok: result.ok, colors: result.colors.map((c) => c.hex), fonts: result.fonts, logos: result.logos.length, errors: result.errors }));
