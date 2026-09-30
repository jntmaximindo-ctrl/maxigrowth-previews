#!/usr/bin/env python3
"""Uji regresi: setiap pelajaran di docs/pelajaran.md punya tes di sini, dijalankan tiap run orkestrator.
Kalau ada yang GAGAL, laporan robot menyalakan alarm → Claude memperbaiki ATURAN-nya (bukan kasusnya).
Semua tes berjalan di salinan sementara; repo tidak disentuh.
"""
import datetime, importlib.util, json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
hasil = []


def uji(nama):
    def bungkus(fn):
        try:
            fn(); hasil.append(("✅", nama, ""))
        except Exception as e:
            hasil.append(("❌", nama, f"{type(e).__name__}: {e}"))
        return fn
    return bungkus


def salin():
    d = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "scripts", d / "scripts")
    (d / "data").mkdir()
    for f in ("codex-pool.json",):
        shutil.copy(ROOT / "data" / f, d / "data" / f)
    (d / "data" / "codex-pool-state.json").write_text("{}")
    return d


def modul(d, nama):
    spec = importlib.util.spec_from_file_location(nama + str(id(d)), d / "scripts" / f"{nama}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


NOW = datetime.datetime.utcnow()
LAMA = iso(NOW - datetime.timedelta(hours=5))
BALAS = iso(NOW - datetime.timedelta(hours=4))


def pr(nomor, komentar, commit_t=None):
    return {"number": nomor, "headRefName": f"codex/rakit-B99-T{nomor}", "createdAt": LAMA,
            "commits": [{"committedDate": commit_t or iso(NOW - datetime.timedelta(hours=6))}], "comments": komentar}


def jalankan_pindai(d, prs):
    m = modul(d, "codex_pool")
    m.OUT = d / "pool"
    m.gh = lambda *a: json.dumps(prs)
    m.pindai()
    return (d / "pool" / "aksi.tsv").read_text(), json.loads((d / "data" / "codex-pool-state.json").read_text())


@uji("#3 semua slot habis → pilih kosong tanpa error, dan bash tidak crash")
def _():
    d = salin()
    st = {s["id"]: {"habis_sampai": iso(NOW + datetime.timedelta(hours=3))} for s in json.loads((d / "data/codex-pool.json").read_text())["slot"]}
    (d / "data/codex-pool-state.json").write_text(json.dumps(st))
    out = subprocess.run([sys.executable, str(d / "scripts/codex_pool.py"), "pilih"], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "", out.stdout + out.stderr
    r = subprocess.run(["bash", "-ec", 'PAT_A=x; SL=""; SEC=${SL#* }; [ -n "$SL" ] || SEC=CODEX_PAT_A; PAT=${!SEC:-$PAT_A}; echo ok'],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@uji("#4/#7 Codex balas 'selesai' tanpa push (format panggilan lama) → dipanggil ulang dengan 'wajib push'")
def _():
    d = salin()
    aksi, st = jalankan_pindai(d, [pr(1, [
        {"author": {"login": "pemilik"}, "body": "@codex baca surat tugas dan kerjakan", "createdAt": LAMA},
        {"author": {"login": "chatgpt-codex-connector"}, "body": "### Summary built", "createdAt": BALAS}])])
    assert aksi.startswith("1\t"), aksi
    assert "WAJIB commit dan push" in (d / "pool" / "pr1.md").read_text()


@uji("#4 Codex sudah push (commit baru) → tidak dipanggil ulang")
def _():
    d = salin()
    aksi, _ = jalankan_pindai(d, [pr(2, [
        {"author": {"login": "pemilik"}, "body": "@codex Kerjakan tugas", "createdAt": LAMA},
        {"author": {"login": "chatgpt-codex-connector"}, "body": "### Summary", "createdAt": BALAS}], commit_t=BALAS)])
    assert aksi.strip() == "", aksi


@uji("#4 banyak PR lama gagal sekaligus → gagal_berturut naik maks 1 per run (tidak memicu alarm palsu)")
def _():
    d = salin()
    k = lambda n: [{"author": {"login": "pemilik"}, "body": "@codex Kerjakan tugas", "createdAt": LAMA},
                   {"author": {"login": "chatgpt-codex-connector"}, "body": "done", "createdAt": BALAS}]
    _, st = jalankan_pindai(d, [pr(n, k(n)) for n in range(10, 15)])
    assert st["A"]["gagal_berturut"] == 1, st


@uji("limit kuota → slot ditandai habis & tugas dipindah/ditunda, bukan error")
def _():
    d = salin()
    t = iso(NOW - datetime.timedelta(minutes=10))
    aksi, st = jalankan_pindai(d, [pr(3, [
        {"author": {"login": "pemilik"}, "body": f"<!-- slot=A t={t} -->\n@codex Kerjakan tugas", "createdAt": t},
        {"author": {"login": "chatgpt-codex-connector"}, "body": "You have reached your Codex usage limits.", "createdAt": t}])])
    assert st["A"].get("habis_sampai", "") > iso(NOW), st


@uji("#2 jembatan 'ganti': teks lama tidak unik → perintah ditolak utuh, file tidak berubah")
def _():
    d = pathlib.Path(tempfile.mkdtemp()); (d / "scripts").mkdir(); (d / "cmd").mkdir()
    shutil.copy(ROOT / "scripts/jembatan.py", d / "scripts/jembatan.py")
    (d / "a.txt").write_text("x\nx\n")
    (d / "cmd/1.json").write_text(json.dumps({"id": "t", "ganti": {"a.txt": [["x", "y"]]}}))
    m = modul(d, "jembatan"); m.ROOT = d; m.OUT = d / "jb"   # jangan menimpa /tmp/jb milik run sungguhan
    m.terapkan(str(d / "cmd"))
    h = (d / "jb" / "hasil.md").read_text()
    assert "❌" in h and (d / "a.txt").read_text() == "x\nx\n", h


@uji("loop belajar: kesalahan yang sama di 2 klinik → masuk AGENTS.md, idempoten")
def _():
    d = salin()
    (d / "AGENTS.md").write_text("# AGENTS\n")
    m = modul(d, "belajar"); m.TMP = d / "tmp"
    for job in ("B1/W1", "B1/W2"):
        f = d / f"out{job[-1]}.txt"; f.write_text(f"✗ riset.json → /cabang/0/wa: ada nilai tapi src kosong\n")
        m.catat("riset", str(f), job)
    m.gabung(); m.perbarui(); m.perbarui()
    ag = (d / "AGENTS.md").read_text()
    assert ag.count(m.MULAI) == 1 and "src" in ag and "2 klinik" in ag, ag
    at = d / "aturan.txt"; at.write_text("ATURAN GPT\n")
    m.sisip(str(at))
    try:
        m.sisip(str(at)); raise AssertionError("sisip kedua harus 'tidak berubah'")
    except SystemExit as e:
        assert e.code == 3
    assert at.read_text().count(m.MULAI) == 1 and "src" in at.read_text()


print("\n".join(f"{a} {b}" + (f" — {c}" if c else "") for a, b, c in hasil))
gagal = [h for h in hasil if h[0] == "❌"]
pathlib.Path("/tmp/jb").mkdir(exist_ok=True)
pathlib.Path("/tmp/jb/uji.txt").write_text("\n".join(f"{a} {b}" + (f" — {c}" if c else "") for a, b, c in gagal))
sys.exit(1 if gagal else 0)
