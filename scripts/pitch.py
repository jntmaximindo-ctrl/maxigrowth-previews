"""PDF pitch deck per klinik (6 halaman 16:9) — tanpa AI, tidak menghubungi klinik.

Template: templates/pitch/index.html (desain GPT, disetujui pemilik 27 Okt 2026).
Data: job.json (nama, slug, kota, maps.rating/ulasan) + riset.json (jumlah cabang) + screenshot ASLI preview
(komputer + ponsel) lewat Playwright. Warna aksen = variabel --mg milik preview klinik itu sendiri.
Hasil: /tmp/pitch/Proposal Website - <Nama>.pdf  (diunggah workflow ke Drive bus "12 Pitch Deck PDF").
Catatan selesai: data/pitch.json {slug: "YYYY-MM-DD"}.

Pakai: python scripts/pitch.py --batas 10 [--slug a,b,c]
"""
import argparse, base64, io, json, pathlib, re, sys, datetime
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path("/tmp/pitch")
BAHAN = pathlib.Path("/tmp/pitch_bahan")
CATAT = ROOT / "data" / "pitch.json"
SITUS = "https://maxigrowthstudio.com"
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def b64(img, kind="JPEG", q=82):
    buf = io.BytesIO()
    img = img.convert("RGB")
    img.save(buf, kind, quality=q)
    return f"data:image/{kind.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def angka(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def antrean(batas, slug=None):
    sudah = json.loads(CATAT.read_text()) if CATAT.exists() else {}
    review = json.loads((ROOT / "data" / "review.json").read_text())
    hasil = []
    for jb in sorted(ROOT.glob("batches/B*/W*/job.json")) + sorted(ROOT.glob("batches/B*/N*/job.json")):
        try:
            j = json.loads(jb.read_text())
        except Exception:
            continue
        sl = j.get("slug")
        if not sl or (slug and sl not in slug):
            continue
        if not slug and (review.get(j["id"]) != "lolos" or sl in sudah):
            continue
        m = j.get("maps") or {}
        r, u = angka(m.get("rating")), angka(m.get("ulasan"))
        if not r or not u or u < 3:
            print(f"- lewati {sl}: rating/ulasan tidak ada", flush=True)
            continue
        cab = 1
        rp = jb.parent / "riset.json"
        if rp.exists():
            try:
                cab = max(1, len(json.loads(rp.read_text()).get("cabang") or []))
            except Exception:
                pass
        nama = (j.get("nama") or sl).split(" — ")[0].split(" - ")[0].split(" | ")[0].strip()
        hasil.append(dict(slug=sl, nama=nama, kota=j.get("kota") or "", rating=r, ulasan=int(u), cabang=cab))
    return hasil[:batas], sudah


def hex_dari(css):
    css = (css or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", css):
        return css
    if re.fullmatch(r"#[0-9a-fA-F]{3}", css):
        return "#" + "".join(c * 2 for c in css[1:])
    m = re.match(r"rgba?\((\d+)[ ,]+(\d+)[ ,]+(\d+)", css)
    if m:
        return "#%02x%02x%02x" % tuple(int(x) for x in m.groups())
    return None


def gelap(h, f=0.38):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def foto(pw, sl):
    """Kembalikan (hero_desktop, cek_desktop, hero_hp, cek_hp, aksen) sebagai gambar PIL."""
    url = f"{SITUS}/{sl}/"
    out = {}
    br = pw.chromium.launch()
    # --- komputer
    c = br.new_context(viewport={"width": 1440, "height": 810})
    pg = c.new_page()
    pg.goto(url, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2500)
    aksen = hex_dari(pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--mg')")) or "#0b7a5a"
    pos = pg.evaluate("""() => { const y = id => { const e = document.getElementById(id); return e ? e.getBoundingClientRect().top + scrollY : null; };
      return {semak: y('semak')}; }""")
    if pos["semak"] is None:
        raise RuntimeError("bagian cek keluhan tidak ada")
    out["hd"] = Image.open(io.BytesIO(pg.screenshot()))
    pg.evaluate(f"window.scrollTo(0, {max(0, int(pos['semak']) - 60)})")
    pg.wait_for_timeout(1800)
    out["cd"] = Image.open(io.BytesIO(pg.screenshot()))
    c.close()
    # --- ponsel
    c = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg = c.new_page()
    pg.goto(url, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(2500)
    pos = pg.evaluate("""() => { const y = id => { const e = document.getElementById(id); return e ? e.getBoundingClientRect().top + scrollY : null; };
      const peta = document.querySelector('#semak svg, #semak .arch, #semak [class*=gigi]');
      return {semak: y('semak'), peta: peta ? peta.getBoundingClientRect().top + scrollY : null}; }""")
    out["hp"] = Image.open(io.BytesIO(pg.screenshot()))
    y = (pos["peta"] - 330) if pos["peta"] else pos["semak"] + 250
    pg.evaluate(f"window.scrollTo(0, {max(0, int(y))})")
    pg.wait_for_timeout(1800)
    out["cp"] = Image.open(io.BytesIO(pg.screenshot()))
    c.close()
    br.close()
    return out, aksen


def qr_uri(url, warna):
    import segno
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="svg", scale=6, border=0, dark=warna)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode()


def susun(k, shots, aksen, kualitas):
    h = (ROOT / "templates" / "pitch" / "index.html").read_text()
    tgl = datetime.date.today()
    tanggal = f"{tgl.day} {BULAN[tgl.month - 1]} {tgl.year}"
    rating = f"{k['rating']:.1f}".replace(".", ",")
    ulasan = f"{k['ulasan']:,}".replace(",", ".")
    nm = k["nama"]
    ukuran = 110 if len(nm) <= 20 else 88 if len(nm) <= 30 else 70
    h = h.replace('<span class="clinic-name">', f'<span class="clinic-name" style="font-size:{ukuran}px">')
    if k["cabang"] > 1:
        cab = str(k["cabang"])
    else:
        cab = k["kota"] or "1"
        h = h.replace('<div class="metric-number">{{jumlah_cabang}}</div>', '<div class="metric-number" style="font-size:72px;padding-top:30px">{{jumlah_cabang}}</div>')
        h = h.replace(">Cabang klinik<", ">Lokasi praktik<")
    shown = f"maxigrowthstudio.com/{k['slug']}/"
    # screenshot komputer: potong ke rasio kotak tampil (600x346)
    def pot(im, rasio):
        w, hh = im.size
        t = int(w / rasio)
        return im.crop((0, 0, w, min(hh, t)))
    rep = {
        "{{nama_klinik}}": nm, "{{rating}}": rating, "{{jumlah_ulasan}}": ulasan, "{{jumlah_cabang}}": cab,
        "{{url_preview}}": shown, "{{tanggal}}": tanggal,
        "{{gambar_hero}}": b64(pot(shots["hd"], 600 / 346), q=kualitas), "{{gambar_fitur}}": b64(pot(shots["cd"], 600 / 346), q=kualitas),
        "{{gambar_hero_hp}}": b64(shots["hp"].resize((390, 844)), q=kualitas), "{{gambar_fitur_hp}}": b64(shots["cp"].resize((390, 844)), q=kualitas),
        "{{qr}}": qr_uri(f"{SITUS}/{k['slug']}/", gelap(aksen)),
    }
    for a, b in rep.items():
        h = h.replace(a, b)
    h = h.replace('href="maxigrowthstudio.com/', 'href="https://maxigrowthstudio.com/')
    h = h.replace("--aksen: #397e71", f"--aksen: {aksen}").replace("--aksen-gelap: #183f38", f"--aksen-gelap: {gelap(aksen)}")
    if "{{" in h:
        raise RuntimeError("placeholder tersisa: " + h[h.index("{{"):h.index("{{") + 30])
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batas", type=int, default=10)
    ap.add_argument("--slug", default="")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    slugs = [s.strip() for s in a.slug.split(",") if s.strip()] or None
    q, sudah = antrean(a.batas, slugs)
    print(f"antrean: {len(q)} klinik", flush=True)
    with sync_playwright() as pw:
        for k in q:
            try:
                shots, aksen = foto(pw, k["slug"])
                BAHAN.mkdir(parents=True, exist_ok=True)  # bahan untuk GPT: screenshot asli + warna aksen
                for kode, nm_ in (("hd", "hero-komputer"), ("cd", "cek-komputer"), ("hp", "hero-ponsel"), ("cp", "cek-ponsel")):
                    shots[kode].convert("RGB").save(BAHAN / f"{k['slug']}-{nm_}.jpg", quality=85)
                (BAHAN / f"{k['slug']}-info.txt").write_text(
                    f"nama: {k['nama']}\nkota: {k['kota']}\nrating: {k['rating']}\nulasan: {k['ulasan']}\ncabang: {k['cabang']}\nwarna_aksen: {aksen}\npreview: {SITUS}/{k['slug']}/\n")
                for kual in (82, 70, 58):
                    html = susun(k, shots, aksen, kual)
                    br = pw.chromium.launch()
                    pg = br.new_page(viewport={"width": 1920, "height": 1080})
                    pg.set_content(html, wait_until="networkidle")
                    pg.wait_for_timeout(1500)
                    nama_file = re.sub(r'[\\/:*?"<>|]', "", k["nama"]).strip()
                    p = OUT / f"Proposal Website - {nama_file}.pdf"
                    pg.pdf(path=str(p), width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
                    br.close()
                    if p.stat().st_size <= 2_000_000:
                        break
                sudah[k["slug"]] = datetime.date.today().isoformat()
                print(f"✓ {k['slug']} {p.stat().st_size // 1024} KB aksen={aksen}", flush=True)
            except Exception as e:
                print(f"✗ {k['slug']}: {e}", flush=True)
    CATAT.write_text(json.dumps(sudah, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
