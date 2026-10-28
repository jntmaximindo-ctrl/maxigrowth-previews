#!/usr/bin/env python3
"""Lint kepatuhan iklan fasyankes (Permenkes 1787/2010) + etika kedokteran gigi.
usage: python scripts/lint_permenkes.py <file.html|file.json> [...]
Mengecek teks yang tampil (tanpa script/style). Keluar kode 1 jika ada pelanggaran.
Kata di dalam elemen dengan atribut data-lint-ok dilewati (mis. banner pratinjau yang menjelaskan aturan).
"""
import html, json, re, sys, pathlib

TERLARANG = [
    r"\bterbaik\b", r"\bnomor\s*1\b", r"\bno\.?\s*1\b", r"\b#1\b", r"\btermurah\b", r"\bsatu-satunya\b",
    r"\bpaling\s+(bagus|murah|canggih|lengkap|terpercaya|ahli)\b", r"\bdijamin\b", r"\bgaransi\s+hasil\b",
    r"\btanpa\s+rasa\s+sakit\b", r"\b100\s*%\b", r"\bgratis\b", r"\bdiskon\b", r"\bpromo\b", r"\bcashback\b",
    r"\bhadiah\b", r"\bbest\b", r"\bcheapest\b", r"\bpainless\b", r"\bguaranteed?\b", r"\bfree\b", r"\bdiscount\b",
]
PERINGATAN = [r"\btestimoni\b", r"\btestimonial\b", r"\bbefore\s*[-&/]?\s*after\b", r"\bsebelum\s*(dan|&|-)\s*sesudah\b"]


def teks_html(src: str) -> str:
    src = re.sub(r"<(script|style|svg)[\s\S]*?</\1>", " ", src, flags=re.I)
    src = re.sub(r"<([a-z0-9]+)[^>]*data-lint-ok[^>]*>[\s\S]*?</\1>", " ", src, flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", src))


def teks_json(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(teks_json(v) for k, v in obj.items() if k not in ("outreach",))
    if isinstance(obj, list):
        return " ".join(teks_json(v) for v in obj)
    return str(obj) if isinstance(obj, str) else ""


def cek(path: pathlib.Path) -> tuple[list, list]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    t = teks_json(json.loads(raw)) if path.suffix == ".json" else teks_html(raw)
    t = re.sub(r"\s+", " ", t)
    def cari(pola):
        hasil = []
        for p in pola:
            for m in re.finditer(p, t, flags=re.I):
                # pelajaran 40: 'No.1' sebagai nomor alamat (Blok C No.1, Jl. Raya No.1) bukan klaim 'nomor 1'
                if p == r"\bno\.?\s*1\b" and re.search(r"(?i)\b(jl|jalan|blok|ruko|gg|gang|kav|komplek|perum|lt|lantai|raya|rt|rw)\b.{0,30}$", t[max(0, m.start() - 40): m.start()]):
                    continue
                hasil.append((m.group(0), t[max(0, m.start() - 40): m.end() + 40].strip()))
        return hasil
    return cari(TERLARANG), cari(PERINGATAN)


def main(paths):
    gagal = False
    for p in map(pathlib.Path, paths):
        salah, awas = cek(p)
        print(f"== {p}: {len(salah)} pelanggaran, {len(awas)} peringatan")
        for kata, ctx in salah:
            print(f"  ✗ '{kata}' … {ctx} …")
        for kata, ctx in awas:
            print(f"  ! '{kata}' … {ctx} …")
        gagal |= bool(salah)
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
