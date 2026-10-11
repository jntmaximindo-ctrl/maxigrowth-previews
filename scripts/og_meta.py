"""pelajaran #54: tiap preview punya kartu pratinjau (og:image = foto preview) supaya link di WA/email tampil dengan gambar, tidak dikira spam."""
import html, pathlib, re, sys
pub = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
n = 0
for f in sorted(pub.glob("*/index.html")):
    s = f.parent.name
    if not (f.parent / "preview.jpg").exists():
        continue
    t = f.read_text(encoding="utf-8", errors="ignore")
    if 'property="og:image"' in t:
        continue
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    judul = html.unescape(m.group(1).strip()) if m else s
    nama = re.split(r"\s+[—·|-]\s+", judul)[0]
    u = f"https://maxigrowthstudio.com/{s}/"
    e = lambda x: html.escape(x, quote=True)
    meta = (f'<meta property="og:type" content="website"><meta property="og:url" content="{u}">'
            f'<meta property="og:title" content="{e(nama)} — Konsep Website Baru">'
            f'<meta property="og:description" content="Contoh website gratis untuk {e(nama)}: cek keluhan gigi, info layanan, dan buat janji lewat WhatsApp.">'
            f'<meta property="og:image" content="{u}preview.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="760">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{u}preview.jpg">')
    t2 = re.sub(r"(<head[^>]*>)", r"\1" + meta.replace("\\", "\\\\"), t, count=1)
    if t2 != t:
        f.write_text(t2, encoding="utf-8"); n += 1
print(f"og:image dipasang di {n} halaman")
