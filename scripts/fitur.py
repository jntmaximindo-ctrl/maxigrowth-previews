#!/usr/bin/env python3
"""R&D fitur klinik gigi: ide dari GPT → pilihan Claude → modul dibangun Codex → katalog library.

  pull <dir>        baca FITUR-*_ide.json* dari GPT (hasil unduhan Drive) → library/fitur/ide/, INDEX.md; tulis /tmp/fitur-arsip.txt
  check <dir_modul> validasi modul (dipakai codex_check tahap 'fitur')
  katalog           bangun library/fitur/katalog.json + KATALOG.md; status pilihan dikirim→selesai bila modul ada
  kirim             cetak slug berstatus 'pilih' (data/fitur-pilihan.json) untuk dikirim ke Codex
  tandai <slug> <status>
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FITUR = ROOT / "library" / "fitur"
PILIHAN = ROOT / "data" / "fitur-pilihan.json"
HOST_OK = {"fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.cloudflare.com", "wa.me", "www.google.com", "maps.googleapis.com",
           "maps.gstatic.com", "www.w3.org", "waze.com", "www.waze.com"}
BAWAAN = ["Cek gigi 30 detik (denah 32 gigi → pesan WA)", "Hero gigi 3D + bakteri bisa di-tap", "Status Buka sekarang (zona waktu lokal)",
          "Pemilih cabang + Maps/Waze", "Pencari dokter per spesialis", "Kalkulator cicilan behel", "Perencana kunjungan sepulang kerja",
          "Toggle bahasa ID/EN", "Pesan WA siap kirim yang bisa diedit"]


def baca(p, default):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def check_modul(d):
    d = pathlib.Path(d)
    if not d.is_absolute():
        d = ROOT / d
    slug, errs = d.name, []
    m = baca(d / "manifest.json", None)
    if m is None:
        return ["manifest.json tidak ada / bukan JSON"]
    for k in ("slug", "nama", "ringkas", "manfaat_pasien", "cocok_untuk", "butuh_data", "cara_pasang", "versi"):
        if k not in m:
            errs.append(f"manifest.json: field '{k}' wajib ada")
    if m.get("slug") != slug or not re.fullmatch(r"[a-z0-9-]{3,40}", slug):
        errs.append("manifest.json: slug harus sama dengan nama folder (huruf kecil/angka/-)")
    for nama, kecil in (("fitur.html", 1500), ("demo.html", 2500)):
        f = d / nama
        if not f.exists():
            errs.append(f"{nama} tidak ada"); continue
        h = f.read_text(encoding="utf-8", errors="ignore")
        if len(h) < kecil or len(h) > 90000:
            errs.append(f"{nama}: ukuran {len(h)} byte di luar batas ({kecil}-90000)")
        if f'id="fitur-{slug}"' not in h:
            errs.append(f'{nama}: wajib ada elemen id="fitur-{slug}"')
        if "wa.me" not in h:
            errs.append(f"{nama}: wajib berujung ke pesan WhatsApp (wa.me)")
        if "prefers-reduced-motion" not in h:
            errs.append(f"{nama}: wajib menghormati prefers-reduced-motion")
        if re.search(r"\beval\(|document\.write\(", h):
            errs.append(f"{nama}: eval/document.write dilarang")
        for host in set(re.findall(r"https?://([a-z0-9.\-]+)", h, flags=re.I)):
            if host.lower() not in HOST_OK:
                errs.append(f"{nama}: host eksternal tidak diizinkan: {host}")
        if nama == "fitur.html" and re.search(r"<(html|body)\b", h, flags=re.I):
            errs.append("fitur.html harus berupa potongan (section+style+script), bukan halaman penuh")
        r = subprocess.run([sys.executable, str(ROOT / "scripts/lint_permenkes.py"), str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout); errs.append(f"{nama} melanggar aturan Permenkes (lihat ✗ di atas)")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/lint_permenkes.py"), str(d / "manifest.json")], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout); errs.append("manifest.json melanggar aturan Permenkes")
    return errs


def cmd_check(d):
    errs = check_modul(d)
    for e in errs:
        print("✗", e)
    print("LULUS" if not errs else f"GAGAL ({len(errs)} masalah)")
    return 1 if errs else 0


def cmd_pull(src):
    sys.path.insert(0, str(ROOT / "scripts"))
    from bus import parse
    import jsonschema
    schema = json.loads((ROOT / "schemas" / "ide-fitur.schema.json").read_text())
    (FITUR / "ide").mkdir(parents=True, exist_ok=True)
    arsip = []
    for f in sorted(pathlib.Path(src).glob("FITUR-*")):
        try:
            obj = parse(f.read_text(encoding="utf-8", errors="ignore"))
            es = [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in jsonschema.Draft202012Validator(schema).iter_errors(obj)][:6]
            if es:
                raise ValueError("; ".join(es))
            (FITUR / "ide" / f"{obj['tanggal']}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"✅ {f.name}: {len(obj['ide'])} ide")
        except Exception as e:
            print(f"✗ {f.name}: {e}")
            with open(FITUR / "ide" / "LOG.md", "a", encoding="utf-8") as lg:
                lg.write(f"- {f.name}: GAGAL {str(e)[:200]}\n")
        arsip.append(f.name)
    pathlib.Path("/tmp/fitur-arsip.txt").write_text("".join(f"ARSIP {n}\n" for n in arsip))
    baris = ["# Ide fitur (diurutkan skor)\n", "| skor | id | nama | tanggal | status |", "|---|---|---|---|---|"]
    pil, rows = baca(PILIHAN, {}), []
    for p in sorted((FITUR / "ide").glob("*.json")):
        for i in baca(p, {}).get("ide", []):
            s = i["skor"]; rows.append((sum(s.values()), i, p.stem))
    for tot, i, tgl in sorted(rows, key=lambda x: -x[0]):
        baris.append(f"| {tot}/20 | {i['id']} | {i['nama']} | {tgl} | {pil.get(i['id'], {}).get('status', 'baru')} |")
    (FITUR / "ide" / "INDEX.md").write_text("\n".join(baris) + "\n", encoding="utf-8")
    return 0


def cmd_katalog():
    mods = []
    for mf in sorted((FITUR / "modul").glob("*/manifest.json")):
        m = baca(mf, None)
        if m:
            mods.append({k: m.get(k) for k in ("slug", "nama", "ringkas", "manfaat_pasien", "cocok_untuk", "butuh_data", "versi")})
    FITUR.mkdir(parents=True, exist_ok=True)
    (FITUR / "katalog.json").write_text(json.dumps({"fitur": mods}, ensure_ascii=False, indent=1), encoding="utf-8")
    pil = baca(PILIHAN, {})
    for m in mods:
        if m["slug"] in pil and pil[m["slug"]].get("status") in ("dikirim", "pilih"):
            pil[m["slug"]]["status"] = "selesai"
    if pil:
        PILIHAN.write_text(json.dumps(pil, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# KATALOG FITUR (jangan usulkan ide yang sudah ada di sini)\n", "## Sudah ada di semua situs klinik"] + [f"- {b}" for b in BAWAAN]
    md += ["\n## Modul library (siap dipakai)"] + [f"- {m['nama']}: {m['ringkas']}" for m in mods]
    md += ["\n## Sudah diusulkan / sedang dibangun / ditolak"] + [f"- {k}: {v.get('nama', '')} [{v.get('status')}]" for k, v in sorted(pil.items())]
    for p in sorted((FITUR / "ide").glob("*.json")):
        md += [f"- (usulan {p.stem}) {i['nama']}" for i in baca(p, {}).get("ide", []) if i["id"] not in pil]
    (FITUR / "KATALOG.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"katalog: {len(mods)} modul")
    return 0


def cmd_kirim():
    for k, v in baca(PILIHAN, {}).items():
        if v.get("status") == "pilih":
            print(k)
    return 0


def cmd_tandai(slug, status):
    pil = baca(PILIHAN, {})
    pil.setdefault(slug, {})["status"] = status
    PILIHAN.write_text(json.dumps(pil, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    c, *a = sys.argv[1:]
    sys.exit({"pull": cmd_pull, "check": cmd_check, "katalog": cmd_katalog, "kirim": cmd_kirim, "tandai": cmd_tandai}[c](*a))
