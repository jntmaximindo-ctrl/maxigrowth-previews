"""Render hasil rakit Robot vs GPT (HTML di /tmp/uji/Robot dan /tmp/uji/GPT) pada 1440 dan 390 px.
Keluaran: /tmp/uji/Banding/<slug>-komputer.png (kiri Robot, kanan GPT, 3 potongan vertikal), <slug>-ponsel.png,
dan banding.txt (ukuran, error konsol, tinggi halaman, overflow horizontal)."""
import sys, os, glob
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
R, G, OUT = "/tmp/uji/Robot", "/tmp/uji/GPT", "/tmp/uji/Banding"
os.makedirs(OUT, exist_ok=True)
slugs = sorted(os.path.basename(p)[:-5] for p in glob.glob(G + "/*.html"))
lap = []
def shot(pw, path, w, h, tag):
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    err = []
    pg.on("pageerror", lambda e: err.append(str(e)[:120]))
    pg.on("console", lambda m: err.append(m.text[:120]) if m.type == "error" else None)
    pg.goto("file://" + path); pg.wait_for_timeout(1500)
    tinggi = pg.evaluate("document.documentElement.scrollHeight")
    over = pg.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
    parts = []
    for i, y in enumerate((0, max(0, tinggi // 2 - h // 2), max(0, tinggi - h))):
        pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(400)
        f = f"/tmp/uji_{tag}_{i}.png"; pg.screenshot(path=f); parts.append(f)
    b.close()
    return parts, tinggi, over, err
def gabung(a, b, out, w, h):
    W = w * 2 + 20
    im = Image.new("RGB", (W, h * 3 + 40), "white"); d = ImageDraw.Draw(im)
    for i in range(3):
        im.paste(Image.open(a[i]), (0, i * h + 40)); im.paste(Image.open(b[i]), (w + 20, i * h + 40))
    d.text((10, 10), "ROBOT", fill="black"); d.text((w + 30, 10), "GPT", fill="black")
    im.thumbnail((2400, 3600)); im.save(out)
with sync_playwright() as pw:
    for s in slugs:
        rp, gp = f"{R}/{s}.html", f"{G}/{s}.html"
        if not os.path.exists(rp): continue
        for nama, w, h in (("komputer", 1440, 900), ("ponsel", 390, 844)):
            ra = shot(pw, rp, w, h, "r"); ga = shot(pw, gp, w, h, "g")
            gabung(ra[0], ga[0], f"{OUT}/{s}-{nama}.png", w, h)
            lap.append(f"{s} {nama}: robot {os.path.getsize(rp)//1024}KB tinggi {ra[1]} overflow {ra[2]} err {len(ra[3])} | gpt {os.path.getsize(gp)//1024}KB tinggi {ga[1]} overflow {ga[2]} err {len(ga[3])} {ga[3][:2]}")
open(f"{OUT}/banding.txt", "w").write("\n".join(lap)); print("\n".join(lap))
