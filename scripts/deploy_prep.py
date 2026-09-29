#!/usr/bin/env python3
"""Siapkan folder dist/ untuk Cloudflare Pages dari semua preview yang sudah lolos cek.

dist/<slug>/...  ← salinan batches/<B>/<ID>/site/
data/preview-links.json ← {ID: slug}
Cetak hash isi dist (untuk memutuskan perlu deploy ulang atau tidak).
"""
import hashlib, json, pathlib, re, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OK = {"Siap review", "Disetujui", "Selesai", "Dikirim", "Deal", "Live"}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60]


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    links = {}
    for site in sorted((ROOT / "batches").glob("B*/*/site/index.html")):
        d = site.parent.parent
        try:
            st = json.loads((d / "status.json").read_text(encoding="utf-8")).get("status", "")
        except Exception:
            st = ""
        if st not in OK:
            continue
        try:
            job = json.loads((d / "job.json").read_text(encoding="utf-8"))
        except Exception:
            job = {}
        slug = slugify(job.get("slug") or job.get("nama")) or d.name.lower()
        if slug in links.values():
            slug = f"{slug}-{d.name.lower()}"
        shutil.copytree(site.parent, DIST / slug)
        links[d.name] = slug
    # jangan diindeks mesin pencari: ini preview untuk calon klien, bukan situs resmi klinik
    (DIST / "_headers").write_text("/*\n  X-Robots-Tag: noindex, nofollow\n", encoding="utf-8")
    (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (DIST / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
                                     '<title>Maxi Growth Studio · Preview</title><p>Preview website oleh Maxi Growth Studio.</p>',
                                     encoding="utf-8")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "preview-links.json").write_text(json.dumps(links, indent=1, sort_keys=True), encoding="utf-8")
    h = hashlib.sha1()
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(DIST)).encode()); h.update(f.read_bytes())
    print(h.hexdigest())


if __name__ == "__main__":
    main()
