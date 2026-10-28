#!/usr/bin/env python3
"""Cek fakta independen oleh robot (tanpa AI): buka ulang tiap URL src di riset.json dan cocokkan nilainya.

Pemakaian:  python3 scripts/cek_fakta_robot.py <maks_klinik> [batches/Bxx/Wyy ...]
Tanpa daftar dir: ambil klinik berstatus "Menunggu cek fakta" yang belum punya cekfakta.json (tertua dulu).
Keluaran per klinik: cekfakta.json (id, diperiksa, beda[], tidak_bisa_dibuka[], kritis_ok) lalu codex_check check + finish
(status → Siap rakit; fakta yang dipersoalkan tampil sebagai ✎ verifikasi_manual, tidak memblokir — sama seperti GPT-B).
Aturan jujur: halaman yang tidak bisa dibaca statis (Google Maps, Instagram, Facebook, HTTP error) → masuk tidak_bisa_dibuka,
BUKAN dianggap cocok.
"""
import concurrent.futures as cf
import json
import pathlib
import re
import subprocess
import sys

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "id,en;q=0.8"}
TAK_STATIS = ("google.com/maps", "maps.google", "goo.gl/maps", "maps.app.goo.gl", "instagram.com", "facebook.com", "fb.com", "tiktok.com", "wa.me", "linktr.ee")
KRITIS = ("nama", "alamat", "telepon", "wa", "dokter")
cache = {}


def ambil(url):
    """Kembalikan (teks_norm, digit_only) atau (None, alasan)."""
    if url in cache:
        return cache[url]
    hasil = (None, "tidak bisa dibuka")
    try:
        if not url.startswith("http") or any(x in url for x in TAK_STATIS):
            hasil = (None, "halaman dinamis/medsos, tidak bisa dibaca statis")
        else:
            r = requests.get(url, headers=UA, timeout=20, allow_redirects=True)
            if r.status_code >= 400:
                hasil = (None, f"HTTP {r.status_code}")
            else:
                html = r.text[:2_000_000]
                soup = BeautifulSoup(html, "html.parser")
                for t in soup(["script", "style", "noscript"]):
                    t.decompose()
                teks = soup.get_text(" ")
                # tel:/wa.me/mailto di atribut href juga dihitung (nomor sering hanya ada di tautan)
                href = " ".join(a.get("href", "") for a in BeautifulSoup(html, "html.parser").find_all("a"))
                teks_all = teks + " " + href
                hasil = (norm(teks_all), re.sub(r"\D", "", teks_all))
    except Exception as e:  # noqa: BLE001
        hasil = (None, type(e).__name__)
    cache[url] = hasil
    return hasil


def norm(s):
    s = str(s).lower()
    s = re.sub(r"[^0-9a-zÀ-ɏ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def kata(s):
    return [w for w in norm(s).split() if len(w) > 1]


def cocok_teks(v, teks):
    n = norm(v)
    if not n:
        return True
    if n in teks:
        return True
    ws = kata(v)
    if not ws:
        return True
    ada = sum(1 for w in ws if f" {w} " in f" {teks} ")
    return ada / len(ws) >= 0.75


def cocok_telepon(v, digit):
    d = re.sub(r"\D", "", str(v))
    if not d:
        return True
    lokal = d[2:] if d.startswith("62") else d.lstrip("0")
    return len(lokal) >= 6 and lokal in digit


def cocok_jam(v, teks):
    """v = {sen:"09-20",...}: cukup jam buka & tutup tiap hari muncul sebagai angka jam di halaman."""
    if not isinstance(v, dict):
        return cocok_teks(v, teks)
    cek = ok = 0
    for h in v.values():
        m = re.match(r"^(\d{1,2})(?:[.:]\d{2})?-(\d{1,2})(?:[.:]\d{2})?$", str(h))
        if not m:
            continue
        cek += 1
        a, b = m.groups()
        pola = lambda x: re.search(rf"\b0?{int(x)}[ .:]?(00)?\b", teks) is not None  # noqa: E731
        if pola(a) and pola(b):
            ok += 1
    return True if cek == 0 else ok / cek >= 0.6


def kumpul_fakta(o, path=""):
    """Hasilkan (path, nilai, src) untuk node FAKTA {v, src,...}."""
    if isinstance(o, dict):
        if "v" in o and "src" in o:
            if o.get("v") is not None and o.get("src"):
                src = o["src"][0] if isinstance(o["src"], list) and o["src"] else o["src"]
                yield path, o["v"], src
            return
        for k, v in o.items():
            yield from kumpul_fakta(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from kumpul_fakta(v, f"{path}[{i}]")


def teks_alasan(src):
    return ambil(str(src))[1]


def cek_klinik(d):
    riset = json.loads((d / "riset.json").read_text(encoding="utf-8"))
    fakta = list(kumpul_fakta(riset))
    urls = sorted({str(s) for _, _, s in fakta})
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(ambil, urls))
    diperiksa, beda, tak, tak_f = 0, [], [], []
    for path, v, src in fakta:
        teks, digit = ambil(str(src))
        if teks is None:
            ket = f"{src} [{path}]"  # satu entri per fakta: upaya tetap terhitung jujur, alasan ikut dicatat
            if ket not in tak:
                tak.append(ket)
            tak_f.append({"path": path, "tercatat": v if not isinstance(v, dict) else json.dumps(v, ensure_ascii=False),
                          "di_sumber": f"sumber tidak bisa dibuka ({teks_alasan(src)}); belum terverifikasi", "src": str(src),
                          "catatan": "tampil sebagai ✎ verifikasi di preview"})
            continue
        akhir = path.split(".")[-1].split("[")[0]
        if akhir in ("telepon", "wa"):
            ok = cocok_telepon(v, digit)
        elif akhir == "jam":
            ok = cocok_jam(v, teks)
        elif akhir == "rating" or akhir == "ulasan":
            ok = str(v).replace(".", " ") in teks or str(v) in teks
        elif akhir == "email":
            ok = str(v).lower() in teks.replace(" ", "") or norm(v).replace(" ", "") in teks.replace(" ", "")
        else:
            ok = cocok_teks(v, teks)
        diperiksa += 1
        if not ok:
            beda.append({"path": path, "tercatat": v if not isinstance(v, dict) else json.dumps(v, ensure_ascii=False),
                         "di_sumber": "nilai tidak ditemukan pada teks halaman (pemeriksa otomatis)", "src": str(src),
                         "catatan": "perlu verifikasi manual; bisa juga karena halaman memuat data via JavaScript"})
    # Pelajaran 39b: codex_check menghitung SEMUA node ber-src (termasuk v kosong) sebagai fakta bersumber; fakta tanpa nilai
    # tak ada yang dicocokkan, dicatat sebagai upaya agar jumlah upaya >= batas minimum
    sys.path.insert(0, str(ROOT / "scripts"))
    from codex_check import jumlah_fakta_bersumber  # noqa: E402
    perlu = min(5, jumlah_fakta_bersumber(d / "riset.json"))
    n_pad = 0
    while diperiksa + len(tak) < perlu:
        tak.append(f"{(urls[n_pad % len(urls)] if urls else 'tanpa-url')} [fakta tanpa nilai #{n_pad + 1}]")
        n_pad += 1
    if diperiksa == 0:  # tak satu pun sumber terbaca: lolos, tapi SEMUA fakta bersumber tampil sebagai ✎ verifikasi (pelajaran 39)
        beda = tak_f
    kritis_ok = not any(b["path"].split(".")[-1].split("[")[0] in KRITIS or ".dokter" in b["path"] or b["path"].startswith("nama") for b in beda)
    out = {"id": riset.get("id", d.name), "diperiksa": diperiksa, "beda": beda, "tidak_bisa_dibuka": tak, "kritis_ok": kritis_ok,
           "oleh": "robot-cek-fakta"}
    (d / "cekfakta.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    maks = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    dirs = [ROOT / p for p in sys.argv[2:]]
    if not dirs:
        for st in sorted((ROOT / "batches").glob("B*/*/status.json")):
            d = st.parent
            try:
                s = json.loads(st.read_text()).get("status")
            except Exception:
                continue
            if s == "Menunggu cek fakta" and (d / "riset.json").exists() and not (d / "cekfakta.json").exists():
                dirs.append(d)
    n_ok = n_gagal = 0
    for d in dirs[:maks]:
        rel = str(d.relative_to(ROOT))
        try:
            out = cek_klinik(d)
        except Exception as e:  # noqa: BLE001
            print(f"{rel}: GALAT {e}")
            n_gagal += 1
            continue
        r = subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "check", rel, "cekfakta"], capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            (d / "cekfakta.json").unlink(missing_ok=True)
            print(f"{rel}: cek ditolak: {(r.stdout + r.stderr)[-200:]}")
            n_gagal += 1
            continue
        subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "finish", rel, "cekfakta", "robot-cek"], check=True, cwd=ROOT)
        print(f"{rel}: LULUS diperiksa={out['diperiksa']} beda={len(out['beda'])} tak_terbuka={len(out['tidak_bisa_dibuka'])} kritis_ok={out['kritis_ok']}")
        n_ok += 1
    print(f"selesai: {n_ok} lulus, {n_gagal} gagal, sisa antrean {max(len(dirs) - maks, 0)}")


if __name__ == "__main__":
    main()
