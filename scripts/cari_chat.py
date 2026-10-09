#!/usr/bin/env python3
"""Pencari klinik lewat chat GPT (pengganti jalur Codex yang dijeda).

  ingest <dir>  → baca CARI-*_hasil.json* dari <dir>, tulis sourcing/<kota>-<waktu>/hasil.json (dibaca sourcing.py apply);
                  nama file yang sudah diproses ditulis ke /tmp/cari-arsip.txt (diarsipkan robot, valid maupun tidak)
  kota          → cetak daftar kota berikutnya (belum 'habis') dari data/kota.txt, maks 8
Tanpa library Google (bisa diuji lokal).
"""
import json, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def parse(teks):
    teks = re.sub(r"^```[a-z]*\s*$", "", teks, flags=re.M)
    a, b = teks.find("{"), teks.rfind("}")
    if a < 0 or b < a:
        raise ValueError("tidak ada JSON")
    d = json.loads(teks[a:b + 1])
    if not d.get("kota") or not isinstance(d.get("klinik"), list):
        raise ValueError("field kota/klinik tidak ada")
    return d


def ingest(src):
    src = pathlib.Path(src)
    arsip, ok = [], 0
    for f in sorted(src.glob("CARI-*_hasil.json*")):
        arsip.append(f.name)
        try:
            d = parse(f.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            print(f"❌ {f.name}: {e}")
            continue
        dest = ROOT / "sourcing" / f"{slug(d['kota'])}-{time.strftime('%Y%m%d%H%M%S', time.gmtime())}{ok}"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "hasil.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        ok += 1
        print(f"✅ {f.name}: {d['kota']} {len(d['klinik'])} kandidat")
    pathlib.Path("/tmp/cari-arsip.txt").write_text("\n".join(arsip) + ("\n" if arsip else ""))
    return 0


def kota():
    try:
        habis = set(json.loads((ROOT / "data" / "sourcing-state.json").read_text()).get("habis", []))
    except Exception:
        habis = set()
    out = []
    for line in (ROOT / "data" / "kota.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, n = line.partition("|")
        if slug(k) not in habis:
            out.append(f"{k.strip()} | {n.strip() or 'Indonesia'}")
    print("DAFTAR KOTA BERIKUTNYA (urut; ambil dari atas):")
    print("\n".join(out[:8]) or "(semua kota habis)")
    return 0


if __name__ == "__main__":
    sys.exit(ingest(sys.argv[2]) if sys.argv[1] == "ingest" else kota())
