#!/usr/bin/env python3
"""Buat versi kecil hasil branding agar murah dibaca perakit (Claude) dari Drive.

usage: python scripts/thumbs.py batches/B01/W14
Membaca  <job>/branding/{lama-desktop.png, lama-mobile-hero.png, logo-*.*}
Menulis  <job>/branding/thumbs/{hero-desktop.jpg, hero-mobile.jpg, logo-N.png|svg, index.json}
- screenshot → JPG lebar maks 720 px, hanya bagian atas (hero), kualitas 70
- logo raster → PNG sisi terpanjang maks 240 px; logo SVG disalin apa adanya jika < 40 KB
Tidak pernah membuat job gagal: kesalahan per berkas dicatat di index.json.
"""
import json, pathlib, shutil, sys
from PIL import Image

MAX_HERO_W, MAX_HERO_H, MAX_LOGO = 720, 900, 240


def hero(src: pathlib.Path, dst: pathlib.Path):
    im = Image.open(src).convert("RGB")
    if im.width > MAX_HERO_W:
        im = im.resize((MAX_HERO_W, round(im.height * MAX_HERO_W / im.width)), Image.LANCZOS)
    im = im.crop((0, 0, im.width, min(im.height, MAX_HERO_H)))
    im.save(dst, "JPEG", quality=70, optimize=True)


def logo(src: pathlib.Path, dst: pathlib.Path):
    im = Image.open(src)
    im = im.convert("RGBA") if im.mode not in ("RGBA", "LA") else im
    im.thumbnail((MAX_LOGO, MAX_LOGO), Image.LANCZOS)
    im.save(dst, "PNG", optimize=True)
    return im.size


def main(job_dir: str) -> int:
    b = pathlib.Path(job_dir) / "branding"
    out = b / "thumbs"
    out.mkdir(parents=True, exist_ok=True)
    idx = {"hero": [], "logo": [], "gagal": []}
    for name, target in (("lama-desktop.png", "hero-desktop.jpg"), ("lama-mobile-hero.png", "hero-mobile.jpg")):
        if (b / name).exists():
            try:
                hero(b / name, out / target)
                idx["hero"].append(target)
            except Exception as e:
                idx["gagal"].append(f"{name}: {e}")
    for f in sorted(b.glob("logo-*.*")):
        try:
            if f.suffix.lower() == ".svg":
                if f.stat().st_size < 40_000:
                    shutil.copy(f, out / f.name)
                    idx["logo"].append({"file": f.name, "asal": f.name})
                continue
            w, h = logo(f, out / (f.stem + ".png"))
            idx["logo"].append({"file": f.stem + ".png", "asal": f.name, "ukuran": [w, h]})
        except Exception as e:
            idx["gagal"].append(f"{f.name}: {e}")
    (out / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2))
    kb = sum(p.stat().st_size for p in out.iterdir()) // 1024
    print(f"thumbs: {len(idx['hero'])} hero, {len(idx['logo'])} logo, {kb} KB, gagal {len(idx['gagal'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
