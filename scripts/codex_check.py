#!/usr/bin/env python3
"""Cek otomatis hasil kerja Codex (tanpa AI). Dipakai oleh .github/workflows/codex-check.yml.

  detect <changed.txt>        → cetak dir=… dan stage=riset|cekfakta|none (format GITHUB_OUTPUT)
  check  <dir> <stage>        → validasi; keluar 1 bila gagal (pesan dikirim balik ke Codex)
  finish <dir> <stage>        → setelah merge: tulis status.json (+ tandai ✎ verifikasi dari cek fakta)
"""
import json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOB_RE = re.compile(r"^(batches/B\d+/[^/]+)/(riset|konten|cekfakta)\.json$")
SITE_RE = re.compile(r"^(batches/B\d+/[^/]+)/site/index\.html$")
CARI_RE = re.compile(r"^(sourcing/[^/]+)/hasil\.json$")
FITUR_RE = re.compile(r"^(library/fitur/modul/[a-z0-9-]+)/")


def detect(changed_file):
    dirs, files = set(), set()
    for line in pathlib.Path(changed_file).read_text().split():
        mf = FITUR_RE.match(line.strip())
        if mf:
            dirs.add(mf.group(1)); files.add("fitur"); continue
        mc = CARI_RE.match(line.strip())
        if mc:
            dirs.add(mc.group(1)); files.add("cari"); continue
        m = JOB_RE.match(line.strip()) or SITE_RE.match(line.strip())
        if m:
            dirs.add(m.group(1)); files.add(m.group(2) if m.re is JOB_RE else "site")
    if len(dirs) != 1:
        print("dir="); print("stage=none"); return 0
    stage = "fitur" if "fitur" in files else "cari" if "cari" in files else "rakit" if "site" in files else ("cekfakta" if "cekfakta" in files else "riset")
    print(f"dir={dirs.pop()}"); print(f"stage={stage}")
    return 0


def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"file tidak ada: {p.relative_to(ROOT)}"
    except Exception as e:
        return None, f"JSON tidak valid di {p.relative_to(ROOT)}: {e}"


def schema_errors(obj, name):
    import jsonschema
    schema = json.loads((ROOT / "schemas" / name).read_text())
    v = jsonschema.Draft202012Validator(schema)
    return [f"{name} → {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in v.iter_errors(obj)][:25]


def check(d, stage):
    d = ROOT / d
    errs = []
    if stage == "riset":
        for name in ("riset", "konten"):
            obj, e = load(d / f"{name}.json")
            if e:
                errs.append(e); continue
            errs += schema_errors(obj, f"{name}.schema.json")
            if name == "riset":
                # fakta berisi nilai tapi tanpa sumber = kemungkinan dikarang
                def walk(o, path=""):
                    if isinstance(o, dict):
                        if "v" in o and "src" in o and o.get("v") not in (None, "", []) and not o.get("src"):
                            errs.append(f"riset.json → {path}: ada nilai tapi src kosong (wajib URL sumber atau v=null)")
                        for k, val in o.items():
                            walk(val, f"{path}/{k}")
                    elif isinstance(o, list):
                        for i, val in enumerate(o):
                            walk(val, f"{path}/{i}")
                walk(obj)
        if (d / "konten.json").exists():
            r = subprocess.run([sys.executable, str(ROOT / "scripts/lint_permenkes.py"), str(d / "konten.json")],
                               capture_output=True, text=True)
            print(r.stdout)
            if r.returncode != 0:
                errs.append("konten.json melanggar aturan Permenkes (lihat daftar ✗ di atas)")
    elif stage == "cekfakta":
        obj, e = load(d / "cekfakta.json")
        if e:
            errs.append(e)
        else:
            for k in ("diperiksa", "beda", "kritis_ok"):
                if k not in obj:
                    errs.append(f"cekfakta.json: field '{k}' wajib ada")
            if not isinstance(obj.get("beda", []), list):
                errs.append("cekfakta.json: 'beda' harus list")
            if isinstance(obj.get("diperiksa"), int) and obj["diperiksa"] < 5:
                errs.append("cekfakta.json: terlalu sedikit fakta diperiksa (<5) — buka ulang semua src di riset.json")
    elif stage == "fitur":
        r = subprocess.run([sys.executable, str(ROOT / "scripts/fitur.py"), "check", str(d)], capture_output=True, text=True)
        print(r.stdout)
        if r.returncode != 0:
            errs.append("modul fitur belum memenuhi aturan (lihat daftar ✗ di atas)")
    elif stage == "cari":
        obj, e = load(d / "hasil.json")
        if e:
            errs.append(e)
        else:
            kl = obj.get("klinik")
            if not isinstance(kl, list):
                errs.append("hasil.json: 'klinik' harus list")
            else:
                if not kl and not obj.get("habis"):
                    errs.append("hasil.json: daftar klinik kosong padahal habis=false")
                for i, k in enumerate(kl):
                    for f_ in ("nama", "url", "rating", "ulasan", "punya_website"):
                        if f_ not in k:
                            errs.append(f"klinik[{i}]: field '{f_}' wajib ada (boleh null)")
                    if k.get("punya_website") and k.get("skor_jadul") is None:
                        errs.append(f"klinik[{i}] ({k.get('nama')}): punya website tapi skor_jadul kosong — jalankan scripts/skor_jadul.mjs")
                errs[:] = errs[:25]
    elif stage == "rakit":
        f = d / "site" / "index.html"
        if not f.exists():
            errs.append("site/index.html tidak ada")
        else:
            html = f.read_text(encoding="utf-8", errors="ignore")
            low = html.lower()
            job = json.loads((d / "job.json").read_text(encoding="utf-8"))
            nama = str(job.get("nama", "")).split("(")[0].strip()
            if len(html) < 30000:
                errs.append(f"site/index.html terlalu kecil ({len(html)} byte) — kemungkinan disederhanakan; ikuti kualitas contoh baku")
            if "atabara" not in nama.lower() and "atabara" in low:
                errs.append("masih ada sisa teks 'Atabara' dari contoh baku")
            if "malaysia" not in str(job.get("kota", "")).lower():
                for w in (r"temujanji", r"pergigian", r"\brm\s?\d"):
                    if re.search(w, low):
                        errs.append(f"masih ada istilah Melayu/Malaysia: '{w}'")
            if nama and nama.split()[0].lower() not in low:
                errs.append(f"nama klinik '{nama}' tidak ditemukan di halaman")
            try:
                riset = json.loads((d / "riset.json").read_text(encoding="utf-8"))
                for c in riset.get("cabang", []):
                    wa = (c.get("wa") or {}).get("v")
                    if wa and re.sub(r"\D", "", str(wa)) not in re.sub(r"\D", "", html):
                        errs.append(f"nomor WA {wa} dari riset tidak ada di halaman")
            except Exception:
                pass
            r = subprocess.run([sys.executable, str(ROOT / "scripts/lint_permenkes.py"), str(f)], capture_output=True, text=True)
            print(r.stdout)
            if r.returncode != 0:
                errs.append("site/index.html melanggar aturan Permenkes (lihat ✗ di atas)")
    else:
        errs.append(f"tahap tidak dikenal: {stage}")
    for e in errs:
        print("✗", e)
    print("LULUS" if not errs else f"GAGAL ({len(errs)} masalah)")
    _bersihkan_salinan_skrip()
    return 1 if errs else 0


def _bersihkan_salinan_skrip():
    """Orkestrator menyalin skrip versi main ke checkout branch PR (HEAD terlepas) sebelum cek.
    Kembalikan folder scripts/ ke versi branch supaya checkout berikutnya tidak gagal
    ('local changes would be overwritten'). Hanya saat HEAD terlepas (checkout PR), bukan di main."""
    try:
        head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if head == "HEAD":
            subprocess.run(["git", "checkout", "-q", "--", "scripts"], cwd=ROOT, capture_output=True)
            subprocess.run(["git", "clean", "-fdq", "--", "scripts"], cwd=ROOT, capture_output=True)
    except Exception:
        pass


def finish(d, stage, oleh="codex"):
    d = ROOT / d
    if stage == "fitur":
        subprocess.run([sys.executable, str(ROOT / "scripts/fitur.py"), "katalog"], cwd=ROOT)
        return 0
    if stage == "cari":
        print("hasil pencarian diterapkan ke Sheet oleh orkestrator")
        return 0
    if stage == "rakit":
        import datetime
        job = json.loads((d / "job.json").read_text(encoding="utf-8"))
        (d / "preview.json").write_text(json.dumps({
            "preview": None, "slug": job.get("slug"), "status": "Siap review", "oleh": oleh,
            "built": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file": "site/index.html"}, ensure_ascii=False), encoding="utf-8")
        status = "Siap review"
    elif stage == "riset":
        status = "Menunggu cek fakta"
    else:
        cek = json.loads((d / "cekfakta.json").read_text(encoding="utf-8"))
        riset = json.loads((d / "riset.json").read_text(encoding="utf-8"))
        if not cek.get("kritis_ok", False) or cek.get("beda"):
            # sama seperti research.py: fakta dipersoalkan tidak memblokir, tapi tampil sebagai ✎ verifikasi
            riset["verifikasi_manual"] = [
                {"path": b.get("path"), "tercatat": b.get("tercatat"), "catatan": b.get("di_sumber") or b.get("catatan")}
                for b in cek.get("beda", [])]
            (d / "riset.json").write_text(json.dumps(riset, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "Siap rakit"
    (d / "status.json").write_text(json.dumps({"status": status, "oleh": oleh}, ensure_ascii=False), encoding="utf-8")
    print("status:", status)
    return 0


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    sys.exit({"detect": detect, "check": check, "finish": finish}[cmd](*a))
