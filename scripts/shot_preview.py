"""pelajaran #53: foto preview tiap klinik untuk email reachout -> public/<slug>/preview.jpg
(dipakai sebagai gambar yang bisa diklik di email). Hanya memotret ulang halaman yang berubah (cache .shots/<slug>.sha)."""
import hashlib, pathlib, shutil, sys
from playwright.sync_api import sync_playwright

pub = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "public")
cache = pathlib.Path(".shots"); cache.mkdir(exist_ok=True)
baru = sama = gagal = 0
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1200, "height": 760}, device_scale_factor=1)
    for f in sorted(pub.glob("*/index.html")):
        s = f.parent.name
        if s in ("atabara",):
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        jpg, sha = cache / f"{s}.jpg", cache / f"{s}.sha"
        if not (jpg.exists() and sha.exists() and sha.read_text() == h):
            try:
                pg.goto(f.resolve().as_uri(), wait_until="load", timeout=30000)
                pg.wait_for_timeout(3000)
                pg.screenshot(path=str(jpg), type="jpeg", quality=72)
                sha.write_text(h); baru += 1
            except Exception as e:
                print(f"✗ {s}: {e}"); gagal += 1
                continue
        else:
            sama += 1
        shutil.copy(jpg, f.parent / "preview.jpg")
    b.close()
print(f"foto preview: {baru} baru, {sama} dari cache, {gagal} gagal")
