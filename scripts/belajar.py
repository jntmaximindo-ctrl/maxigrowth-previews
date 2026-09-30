#!/usr/bin/env python3
"""Loop belajar pekerja (Codex/GPT): kesalahan yang berulang otomatis jadi aturan di instruksi mereka.

  catat <tahap> <check.out> <job>   → ambil baris "✗ ..." dari hasil codex_check, simpan ke /tmp/belajar/qa.jsonl
  gabung                            → pindahkan /tmp/belajar/qa.jsonl ke data/qa-log.jsonl (repo)
  sisip <file_aturan>               → masukkan daftar kesalahan umum ke file ATURAN GPT (Drive) di antara penanda;
                                      exit 0 bila berubah (robot lalu mengunggah), 3 bila tidak ada perubahan
  perbarui                          → hitung kategori kesalahan 30 hari terakhir; yang muncul ≥2x ditulis ke
                                      AGENTS.md (bagian otomatis) + /tmp/belajar/kesalahan-umum.md (untuk GPT di Drive)
Tidak memakai AI: murni hitung & tulis, jadi gratis dan jalan tiap run orkestrator.
"""
import datetime, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path("/tmp/belajar")
LOG = ROOT / "data" / "qa-log.jsonl"
AG = ROOT / "AGENTS.md"
MULAI, SELESAI = "<!-- BELAJAR:MULAI (otomatis, jangan diedit manual) -->", "<!-- BELAJAR:SELESAI -->"
MIN_ULANG, HARI = 2, 30

# saran perbaikan untuk kategori yang dikenal (kategori lain: contoh kesalahannya ditampilkan apa adanya)
SARAN = [
    (r"src kosong", "Setiap nilai fakta WAJIB punya src (URL yang benar-benar dibuka). Tidak yakin → v=null."),
    (r"terlalu kecil", "Jangan menyederhanakan halaman: salin struktur contoh baku utuh lalu ganti isinya (≥30 KB)."),
    (r"atabara", "Hapus SEMUA sisa teks contoh baku (cari 'Atabara' sebelum push)."),
    (r"melayu|malaysia", "Klinik Indonesia: jangan pakai istilah Malaysia (temujanji, pergigian, RM)."),
    (r"nama klinik", "Nama klinik dari job.json wajib tampil di halaman (judul/hero)."),
    (r"nomor wa", "Semua nomor WA dari riset.json wajib tampil di halaman (tombol/footer)."),
    (r"permenkes", "Jalankan lint_permenkes.py sebelum push; hapus kata terlarang (terbaik, termurah, dijamin, promo, diskon, testimoni)."),
    (r"skema|schema|wajib ada|harus list", "Ikuti skema di schemas/ persis: semua field wajib ada (boleh null), tipe data benar."),
    (r"terlalu sedikit fakta", "Cek fakta: buka ulang SEMUA src di riset.json, minimal 5 fakta diperiksa."),
    (r"skor_jadul", "Klinik yang punya website wajib diberi skor_jadul (jalankan scripts/skor_jadul.mjs)."),
    (r"tidak ada|not found|json", "Pastikan file keluaran ada di folder job yang benar dan JSON-nya valid sebelum push."),
]


def kategori(baris):
    s = baris.lower()
    s = re.sub(r"'[^']*'|\"[^\"]*\"", "'…'", s)          # nama/teks spesifik
    s = re.sub(r"\[\d+\]|/\d+|\d+", "N", s)               # indeks & angka
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120]


def catat(tahap, out, job):
    TMP.mkdir(exist_ok=True)
    t = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    baris = [x[1:].strip() for x in pathlib.Path(out).read_text(errors="ignore").splitlines() if x.startswith("✗")]
    with open(TMP / "qa.jsonl", "a") as f:
        for b in baris[:25]:
            f.write(json.dumps({"t": t, "tahap": tahap, "job": job, "kat": kategori(b), "contoh": b[:200]}, ensure_ascii=False) + "\n")
    print(f"{len(baris)} kesalahan dicatat")


def lulus(tahap, job):
    TMP.mkdir(exist_ok=True)
    t = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(TMP / "qa.jsonl", "a") as f:
        f.write(json.dumps({"t": t, "tahap": tahap, "job": job, "kat": "LULUS", "contoh": ""}) + "\n")


def rapor():
    """Rapor pekerja per peran (7 & 30 hari): klinik lulus, klinik pernah gagal, lulus sekali jalan."""
    if not LOG.exists():
        return
    now = datetime.datetime.utcnow()
    rows = []
    for ln in LOG.read_text().splitlines():
        try:
            rows.append(json.loads(ln))
        except Exception:
            pass
    L = ["# Rapor pekerja (otomatis)", "", "| peran/tahap | periode | klinik lulus | klinik pernah gagal | lulus sekali jalan | kesalahan terbanyak |", "|---|---|---|---|---|---|"]
    for hari in (7, 30):
        batas = (now - datetime.timedelta(days=hari)).strftime("%Y-%m-%dT%H:%M:%SZ")
        per = {}
        for r in rows:
            if r["t"] < batas:
                continue
            x = per.setdefault(r["tahap"], {"lulus": set(), "gagal": set(), "kat": {}})
            if r["kat"] == "LULUS":
                x["lulus"].add(r["job"])
            else:
                x["gagal"].add(r["job"]); x["kat"][r["kat"]] = x["kat"].get(r["kat"], 0) + 1
        for tahap, x in sorted(per.items()):
            sekali = len(x["lulus"] - x["gagal"])
            pct = f"{100 * sekali // len(x['lulus'])}%" if x["lulus"] else "-"
            top = max(x["kat"], key=x["kat"].get)[:60] if x["kat"] else "-"
            L.append(f"| {tahap} | {hari} hari | {len(x['lulus'])} | {len(x['gagal'])} | {pct} | {top} |")
    (ROOT / "data" / "rapor.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def gabung():
    src = TMP / "qa.jsonl"
    if src.exists() and src.read_text().strip():
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a") as f:
            f.write(src.read_text())
        src.unlink()


def perbarui():
    if not LOG.exists():
        print("belum ada catatan kesalahan"); return
    batas = (datetime.datetime.utcnow() - datetime.timedelta(days=HARI)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hit, contoh, jobs = {}, {}, {}
    for ln in LOG.read_text().splitlines():
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r["t"] < batas:
            continue
        k = (r["tahap"], r["kat"])
        jobs.setdefault(k, set()).add(r["job"])
        contoh[k] = r["contoh"]
    for k, js in jobs.items():
        hit[k] = len(js)                                   # dihitung per klinik, bukan per baris
    ulang = sorted([k for k in hit if hit[k] >= MIN_ULANG], key=lambda k: -hit[k])[:15]
    L = ["## Kesalahan yang sering terjadi (dipelajari otomatis dari cek gagal — WAJIB dihindari)"]
    if not ulang:
        L.append("- (belum ada kesalahan berulang)")
    for tahap, kat in ulang:
        saran = next((s for pola, s in SARAN if re.search(pola, kat)), None)
        L.append(f"- [{tahap}] {saran or 'Hindari: ' + contoh[(tahap, kat)]} (terjadi di {hit[(tahap, kat)]} klinik)")
    blok = MULAI + "\n" + "\n".join(L) + "\n" + SELESAI
    ag = AG.read_text(encoding="utf-8")
    ag = re.sub(re.escape(MULAI) + r".*?" + re.escape(SELESAI), lambda m: blok, ag, flags=re.S) if MULAI in ag else ag.rstrip() + "\n\n" + blok + "\n"
    AG.write_text(ag, encoding="utf-8")
    TMP.mkdir(exist_ok=True)
    (TMP / "kesalahan-umum.md").write_text("# Kesalahan umum pekerja (otomatis dari robot)\n\n" + "\n".join(L[1:]) + "\n", encoding="utf-8")
    print("\n".join(L))


def sisip(f):
    src = TMP / "kesalahan-umum.md"
    if not src.exists():
        sys.exit(3)
    isi = src.read_text(encoding="utf-8").replace("# Kesalahan umum pekerja (otomatis dari robot)",
                                                   "=== KESALAHAN YANG SERING TERJADI (dipelajari otomatis — WAJIB dihindari) ===")
    blok = MULAI + "\n" + isi.strip() + "\n" + SELESAI
    lama = pathlib.Path(f).read_text(encoding="utf-8")
    baru = re.sub(re.escape(MULAI) + r".*?" + re.escape(SELESAI), lambda m: blok, lama, flags=re.S) if MULAI in lama else lama.rstrip() + "\n\n" + blok + "\n"
    if baru == lama:
        sys.exit(3)
    pathlib.Path(f).write_text(baru, encoding="utf-8")
    print("ATURAN GPT diperbarui")


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"catat": catat, "lulus": lulus, "gabung": gabung, "perbarui": perbarui, "sisip": sisip, "rapor": rapor}[cmd](*a)
