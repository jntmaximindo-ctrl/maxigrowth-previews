#!/usr/bin/env python3
"""Review otomatis preview klinik (tanpa AI): cek halaman live, tulis data/review.json."""
import glob
import json
import os
import re
import time
import urllib.request
import concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://maxigrowthstudio.com/"


def baca(path, default):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def ambil(url):
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (maxigrowth-review)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            time.sleep(2)
    return 0, ""


def periksa(kid, slug):
    if not slug:
        return kid, "gagal", "tanpa tautan preview"
    kode, html = ambil(BASE + slug + "/")
    if kode != 200:
        return kid, "gagal", "HTTP " + str(kode)
    if len(html) < 15000:
        return kid, "gagal", "halaman terlalu pendek"
    low = html.lower()
    if "noindex" not in low:
        return kid, "gagal", "tanpa noindex"
    teks = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    teks = re.sub(r"(?s)<[^>]+>", " ", teks)
    if re.search(r"lorem ipsum|\{\{|\[nama|\[alamat|placeholder|todo|\bundefined\b|\bnan\b", teks, re.I):
        return kid, "gagal", "teks placeholder"
    if not re.search(r"wa\.me|whatsapp|tel:", low):
        return kid, "gagal", "tanpa kontak"
    return kid, "lolos", ""


links = baca("data/preview-links.json", {})
outreach = baca("data/outreach.json", {})
review = baca("data/review.json", {})
catatan = baca("data/review-catatan.json", {})
def kesementara(alasan):
    """Pelajaran 42: gagal karena belum terdeploy (404/tanpa tautan/HTTP 0/5xx) bersifat sementara -> diperiksa ulang."""
    a = str(alasan)
    return a.startswith("tanpa tautan") or a in ("HTTP 404", "HTTP 0") or re.match(r"HTTP 5\d\d", a) is not None


todo = []
for p in glob.glob(os.path.join(ROOT, "batches", "*", "*", "status.json")):
    st = baca(os.path.relpath(p, ROOT), {})
    if (st.get("status") or "").lower() != "siap review":
        continue
    kid = os.path.basename(os.path.dirname(p))
    if kid in outreach:
        continue
    if kid in review and not (review[kid] == "gagal" and kesementara(catatan.get(kid, ""))):
        continue
    slug = links.get(kid)
    if isinstance(slug, list):
        slug = slug[0] if slug else None
    todo.append((kid, slug))

print("diperiksa:", len(todo))
with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for kid, hasil, alasan in ex.map(lambda a: periksa(*a), todo):
        review[kid] = hasil
        if alasan:
            catatan[kid] = alasan
        else:
            catatan.pop(kid, None)

with open(os.path.join(ROOT, "data", "review.json"), "w", encoding="utf-8") as f:
    json.dump(review, f, ensure_ascii=False, indent=1, sort_keys=True)
with open(os.path.join(ROOT, "data", "review-catatan.json"), "w", encoding="utf-8") as f:
    json.dump(catatan, f, ensure_ascii=False, indent=1, sort_keys=True)
print("lolos:", sum(1 for v in review.values() if v == "lolos"), "gagal:", sum(1 for v in review.values() if v == "gagal"))
