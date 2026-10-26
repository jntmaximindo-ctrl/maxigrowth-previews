"""Kolase outreach WA — 3 screenshot HP ASLI dari preview klinik dalam 1 gambar.

Format disetujui pemilik 26 Okt 2026:
  1) maskot gigi 3D (#stage)  2) cek keluhan gigi interaktif (#semak, peta gigi)
  3) daftar perawatan & biaya (#rawatan)
Hasil: /tmp/kolase/<slug>.jpg (diunggah workflow ke Drive bus "11 Kolase WA").
Catatan selesai: data/kolase.json {slug: "YYYY-MM-DD"} supaya tidak diulang.

Pakai: python scripts/kolase.py --batas 40 [--slug habit-singosari]
"""
import argparse, json, pathlib, sys, time
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path("/tmp/kolase")
CATAT = ROOT / "data" / "kolase.json"
SITUS = "https://maxigrowthstudio.com"
LABEL = ["Maskot gigi", "Cek keluhan gigi", "Perawatan & biaya"]
FONT = "/usr/share/fonts/truetype/dejavu/"


def font(n, bold=False):
    try:
        return ImageFont.truetype(FONT + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), n)
    except OSError:
        return ImageFont.load_default()


def antrean(batas, slug=None, ulang=False):
    sudah = json.loads(CATAT.read_text()) if CATAT.exists() else {}
    hasil = []
    for st in sorted(ROOT.glob("batches/B*/W*/status.json")):
        try:
            s = json.loads(st.read_text()).get("status")
            j = json.loads((st.parent / "job.json").read_text())
        except Exception:
            continue
        sl = j.get("slug")
        if not sl or (slug and sl not in slug):
            continue
        if ulang:
            if sl not in sudah or sudah[sl] == "v2":
                continue
        elif not slug and (s not in ("Siap review", "Selesai") or sl in sudah):
            continue
        nama = (j.get("nama") or sl).split(" — ")[0].split(" - ")[0].split(" | ")[0].strip()
        hasil.append((sl, nama, f"{j.get('batch')}/{j.get('id')}"))
    return hasil[:batas], sudah


def foto(page, sl):
    page.goto(f"{SITUS}/{sl}/", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)
    pos = page.evaluate("""() => {
      const y = id => { const e = document.getElementById(id); return e ? e.getBoundingClientRect().top + scrollY : null; };
      const peta = document.querySelector('#semak svg, #semak .arch, #semak [class*=gigi]');
      const bg = getComputedStyle(document.getElementById('top') || document.body).backgroundColor;
      const r = document.getElementById('rawatan');
      return {stage: y('stage'), semak: y('semak'), rawatan: y('rawatan'), lokasi: y('lokasi'),
              rawatanTampil: !!(r && r.offsetHeight > 0),
              peta: peta ? peta.getBoundingClientRect().top + scrollY : null, bg};
    }""")
    if pos["stage"] is None or pos["semak"] is None:
        raise RuntimeError(f"bagian tidak lengkap: {pos}")
    label = list(LABEL)
    if pos["rawatanTampil"]:
        ketiga = pos["rawatan"] - 70
    elif pos["lokasi"] is not None:
        # daftar perawatan kosong (section disembunyikan) -> pakai lokasi & jam buka
        ketiga = pos["lokasi"] - 70
        label[2] = "Lokasi & jam buka"
    else:
        raise RuntimeError(f"perawatan & lokasi tidak tampil: {pos}")
    target = [pos["stage"] - 110,
              (pos["peta"] - 330) if pos["peta"] else pos["semak"] + 250,
              ketiga]
    shots = []
    for i, y in enumerate(target):
        page.evaluate(f"window.scrollTo(0, {max(0, int(y))})")
        page.wait_for_timeout(1800)
        p = OUT / f"{sl}-{i + 1}.png"
        page.screenshot(path=str(p))
        shots.append(p)
    return shots, pos["bg"], label


def warna(bg):
    try:
        v = [int(float(x)) for x in bg[bg.index("(") + 1:bg.index(")")].split(",")[:3]]
        if sum(v) > 600 or sum(v) < 30:  # terlalu terang/gelap → hijau tua baku
            raise ValueError
        return tuple(v)
    except Exception:
        return (31, 90, 85)


def susun(shots, out, nama, url, bg, label=LABEL):
    # Format KOTAK 1080x1080 (disetujui pemilik; versi lebar terlihat lonjong di WA).
    W = H = 1080
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 95), "Konsep website untuk", font=font(36), fill=(220, 235, 232), anchor="mm")
    ukuran = 54
    while d.textlength(nama, font=font(ukuran, True)) > W - 90 and ukuran > 30:
        ukuran -= 2
    d.text((W // 2, 150), nama, font=font(ukuran, True), fill="white", anchor="mm")
    pw, top = 320, 235
    gap = (W - 3 * pw) // 4
    ph = None
    for i, p in enumerate(shots):
        s = Image.open(p).convert("RGB")
        s = s.resize((pw, int(s.height * pw / s.width)))
        ph = ph or min(s.height, 580)
        s = s.crop((0, 0, pw, ph))
        x = gap + i * (pw + gap)
        sh = Image.new("RGBA", (pw + 60, ph + 60), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((30, 36, pw + 30, ph + 36), 38, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        img.paste(sh, (x - 30, top - 30), sh)
        d.rounded_rectangle((x - 10, top - 10, x + pw + 10, top + ph + 10), 38, fill=(24, 24, 24))
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph - 1), 28, fill=255)
        img.paste(s, (x, top), m)
        d.text((x + pw // 2, top + ph + 52), label[i], font=font(27, True), fill="white", anchor="mm")
    d.text((W // 2, top + ph + 125), url, font=font(30, True), fill="white", anchor="mm")
    d.text((W // 2, H - 40), "Pratinjau konsep oleh Maxi Growth Studio · bukan situs resmi klinik",
           font=font(20), fill=(200, 225, 220), anchor="mm")
    img.save(out, quality=88)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--batas", type=int, default=40)
    a.add_argument("--slug", help="satu/lebih slug dipisah koma")
    a.add_argument("--ulang", action="store_true",
                   help="cek ulang kolase lama; buat ulang hanya yang perawatannya kosong")
    arg = a.parse_args()
    arg.slug = set(arg.slug.split(",")) if arg.slug else None
    OUT.mkdir(parents=True, exist_ok=True)
    daftar, sudah = antrean(arg.batas, arg.slug, arg.ulang)
    print(f"antrean kolase: {len(daftar)}")
    if not daftar:
        return
    from playwright.sync_api import sync_playwright
    ok = gagal = 0
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 390, "height": 682}, device_scale_factor=2,
                             is_mobile=True, has_touch=True,
                             user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        page = ctx.new_page()
        for sl, nama, job in daftar:
            try:
                shots, bg, label = foto(page, sl)
                if arg.ulang and label == LABEL:
                    sudah[sl] = "v2"  # kolase lama sudah benar
                    print(f"= {job} {sl} sudah benar", flush=True)
                    CATAT.write_text(json.dumps(sudah, ensure_ascii=False, indent=0, sort_keys=True))
                    continue
                susun(shots, OUT / f"{sl}.jpg", nama, f"maxigrowthstudio.com/{sl}/", warna(bg), label)
                sudah[sl] = "v2"
                ok += 1
                print(f"✓ {job} {sl} | {label[2]}", flush=True)
                CATAT.parent.mkdir(exist_ok=True)
                CATAT.write_text(json.dumps(sudah, ensure_ascii=False, indent=0, sort_keys=True))
            except Exception as e:
                gagal += 1
                print(f"✗ {job} {sl}: {type(e).__name__}: {str(e)[:200]}")
        br.close()
    CATAT.parent.mkdir(exist_ok=True)
    CATAT.write_text(json.dumps(sudah, ensure_ascii=False, indent=0, sort_keys=True))
    print(f"selesai: {ok} kolase, {gagal} gagal")


if __name__ == "__main__":
    main()
