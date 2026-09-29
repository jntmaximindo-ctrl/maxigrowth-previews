// Skor "jadul" website klinik (0 = modern, 100 = sangat jadul). Tanpa AI.
// usage: node scripts/skor_jadul.mjs <url>   → cetak JSON {skor, masalah[]}
import { chromium } from "playwright";
const url = process.argv[2];
const out = { url, skor: 0, masalah: [] };
const add = (poin, m) => { out.skor += poin; out.masalah.push(m); };
const browser = await chromium.launch();
try {
  const page = await (await browser.newContext({ viewport: { width: 375, height: 812 }, userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148" })).newPage();
  const t0 = Date.now();
  let resp;
  try { resp = await page.goto(url, { waitUntil: "load", timeout: 30000 }); }
  catch { add(100, "website tidak bisa dibuka / timeout"); throw new Error("skip"); }
  const ms = Date.now() - t0;
  if (!page.url().startsWith("https://")) add(15, "tidak pakai HTTPS");
  if (ms > 8000) add(15, `lambat dibuka (${Math.round(ms / 1000)} detik)`); else if (ms > 4000) add(7, `agak lambat (${Math.round(ms / 1000)} detik)`);
  const r = await page.evaluate(() => {
    const vp = document.querySelector('meta[name="viewport"]');
    const html = document.documentElement.outerHTML.toLowerCase();
    const years = [...document.body.innerText.matchAll(/(?:©|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})/gi)].map(m => +m[1]);
    return {
      viewport: !!vp && /width=device-width/.test(vp.content || ""),
      overflow: document.documentElement.scrollWidth > window.innerWidth + 5,
      wa: /wa\.me|api\.whatsapp|whatsapp\.com\/send/.test(html),
      tel: !!document.querySelector('a[href^="tel:"]'),
      teks: document.body.innerText.trim().length,
      flash: /\.swf|<marquee|<frameset|<font /.test(html),
      tahun: years.length ? Math.max(...years) : null,
    };
  });
  if (!r.viewport) add(25, "tidak mobile-friendly (tanpa viewport)");
  if (r.overflow) add(15, "tampilan melebar/terpotong di HP");
  if (!r.wa) add(15, "tidak ada tombol WhatsApp");
  if (!r.tel) add(5, "tidak ada tombol telepon");
  if (r.teks < 400) add(10, "isi halaman sangat sedikit");
  if (r.flash) add(15, "teknologi web lama (marquee/frameset/font)");
  if (r.tahun && r.tahun < new Date().getFullYear() - 2) add(10, `copyright lama (${r.tahun})`);
  if (resp && resp.status() >= 400) add(30, `halaman error ${resp.status()}`);
} catch (e) { if (e.message !== "skip") add(50, "gagal dianalisis: " + e.message.slice(0, 80)); }
finally { await browser.close(); }
out.skor = Math.min(100, out.skor);
console.log(JSON.stringify(out));
