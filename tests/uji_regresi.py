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
    # pelajaran #20: tes perilaku pool tidak boleh bergantung pada saklar aktif/nonaktif slot di konfigurasi live
    cfg = json.loads((d / "data" / "codex-pool.json").read_text())
    for x in cfg["slot"]: x["aktif"] = True
    (d / "data" / "codex-pool.json").write_text(json.dumps(cfg))
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


@uji("#9 panggilan gh gagal → dicatat sebagai galat (bukan dianggap 0 PR)")
def _():
    d = salin()
    m = modul(d, "codex_pool"); m.OUT = d / "pool"
    import types
    m.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="GraphQL: too complex"))
    m.pindai()
    assert "too complex" in (d / "pool" / "galat.txt").read_text()


@uji("#11 codex_pool dijalankan dari salinan skrip (tanpa folder data) → tidak crash, pakai slot A")
def _():
    d = pathlib.Path(tempfile.mkdtemp()); shutil.copytree(ROOT / "scripts", d / "scripts-main")
    r = subprocess.run([sys.executable, str(d / "scripts-main" / "codex_pool.py"), "pilih", "A"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip().startswith("A "), r.stdout + r.stderr


@uji("#13 cek PR di checkout terlepas → salinan skrip dibersihkan (checkout berikutnya tidak gagal)")
def _():
    d = pathlib.Path(tempfile.mkdtemp()); g = lambda *a: subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (d / "scripts").mkdir(); shutil.copy(ROOT / "scripts/codex_check.py", d / "scripts/codex_check.py")
    g("add", "."); g("commit", "-qm", "a"); g("checkout", "-q", "--detach")
    (d / "scripts/codex_check.py").write_text((d / "scripts/codex_check.py").read_text() + "\n# ubah\n"); (d / "scripts/baru.py").write_text("x=1")
    m = modul(d, "codex_check"); m.ROOT = d; m._bersihkan_salinan_skrip()
    assert g("status", "--porcelain").stdout.strip() == "", g("status", "--porcelain").stdout


@uji("#14 hasil sudah ada & lulus cek tapi status tertinggal → status dimajukan otomatis")
def _():
    d = salin(); b = d / "batches/B1/W1"; b.mkdir(parents=True)
    (b / "status.json").write_text('{"status": "Riset di Codex"}'); (b / "riset.json").write_text("{}"); (b / "konten.json").write_text("{}")
    (d / "scripts/codex_check.py").write_text(
        "import sys,json,pathlib\nR=pathlib.Path(__file__).resolve().parents[1]\n"
        "if sys.argv[1]=='finish': (R/sys.argv[2]/'status.json').write_text(json.dumps({'status':'Menunggu cek fakta'}))\n")
    m = modul(d, "failover"); m.ROOT = d; m.pulihkan()
    assert "Menunggu cek fakta" in (b / "status.json").read_text()


@uji("rakit template tanpa AI: klinik contoh → halaman lengkap, WA ada, tanpa placeholder/sisa contoh baku")
def _():
    d = pathlib.Path(tempfile.mkdtemp())
    for x in ("scripts", "templates", "library"):
        shutil.copytree(ROOT / x, d / x)
    j = d / "job"; j.mkdir()
    fakta = lambda x: {"v": x, "src": "https://contoh.id"}
    cab = lambda n, wa: {"nama": n, "alamat": fakta(f"Jl. {n} No. 1, Bandung"), "telepon": fakta("0" + wa[2:]), "wa": fakta(wa),
                         "jam": fakta({"sen": "09.00-21.00", "sel": "09-21", "rab": "09-21", "kam": "09-21", "jum": "13-21", "sab": "09-17", "min": "tutup"})}
    (j / "job.json").write_text(json.dumps({"nama": "Klinik Contoh Sehat", "kota": "Bandung"}))
    (j / "riset.json").write_text(json.dumps({"nama": fakta("Klinik Contoh Sehat"), "kota": "Bandung", "zona_waktu": "WIB",
        "cabang": [cab("Contoh Dago", "6281111111111"), cab("Contoh Buah Batu", "6282222222222")], "dokter": [],
        "layanan": ["Scaling", "Tambal Gigi", "Behel", "Perawatan Gigi Anak", "Rontgen Panoramik", "Veneer"],
        "harga": [{"perawatan": "scaling", "jenis": "resmi_klinik", "min": 300000, "max": 300000}, {"perawatan": "behel", "jenis": "kisaran_pasar", "min": 5000000, "max": 9000000}]}))
    (j / "konten.json").write_text(json.dumps({"hero": {"judul": {"id": "Klinik gigi keluarga di Bandung", "en": "Family dental clinic in Bandung"}, "sub": {"id": "Dua cabang.", "en": "Two branches."}},
        "layanan": [{"nama": {"id": "Scaling", "en": "Scaling"}, "ringkas": {"id": "Bersihkan karang gigi.", "en": "Remove tartar."}}],
        "faq": [{"q": {"id": "Buka hari Minggu?", "en": "Open Sunday?"}, "a": {"id": "Tidak, Minggu tutup.", "en": "No, closed on Sunday."}}]}))
    m = modul(d, "rakit_template"); out = m.bangun(j)
    assert not m.periksa(out, j), m.periksa(out, j)
    assert "6281111111111" in out and "6282222222222" in out and "{{" not in out and "@@CFG" not in out
    assert "Rp300 rb" in out and "5 jt" not in out, "harga resmi tampil, kisaran pasar tidak"
    r = json.loads((j / "riset.json").read_text()); r["cabang"] = []; (j / "riset.json").write_text(json.dumps(r))
    try:
        m.bangun(j); raise AssertionError("riset tanpa cabang/WA harus ditolak")
    except SystemExit:
        pass


@uji("#15 Codex balas 'create an environment' → tidak dipanggil ulang, slot ditandai butuh_env + alarm [manusia]")
def _():
    d = salin()
    cfg = json.loads((d / "data/codex-pool.json").read_text())
    cfg["slot"] = [x for x in cfg["slot"] if x["id"] == "A"]; cfg["slot"][0]["aktif"] = True  # satu-satunya slot
    (d / "data/codex-pool.json").write_text(json.dumps(cfg))
    k = [{"author": {"login": "pemilik"}, "body": "@codex Kerjakan tugas", "createdAt": LAMA},
         {"author": {"login": "chatgpt-codex-connector"}, "body": "To use Codex here, [create an environment for this repo](https://chatgpt.com/codex/cloud/settings/environments).", "createdAt": BALAS}]
    aksi, st = jalankan_pindai(d, [pr(5, k), pr(6, k)])
    assert aksi.strip() == "", aksi
    assert st["A"].get("butuh_env") and st["A"].get("gagal_berturut", 0) == 0, st
    log = (d / "pool" / "log.txt").read_text()
    assert log.startswith("[manusia]") and "#5–#6" in log and "settings/environments" in log, log


@uji("#16 slot A butuh environment tapi slot B siap → PR dipanggil ulang ke B, hanya 1 PR per run sampai B terbukti")
def _():
    d = salin()
    cfg = json.loads((d / "data/codex-pool.json").read_text())
    for x in cfg["slot"]: x["aktif"] = True
    (d / "data/codex-pool.json").write_text(json.dumps(cfg))
    k = [{"author": {"login": "pemilik"}, "body": "@codex Kerjakan tugas", "createdAt": LAMA},
         {"author": {"login": "chatgpt-codex-connector"}, "body": "To use Codex here, [create an environment for this repo](https://chatgpt.com/codex/cloud/settings/environments).", "createdAt": BALAS}]
    aksi, st = jalankan_pindai(d, [pr(7, k), pr(8, k), pr(9, k)])
    baris = [x for x in aksi.splitlines() if x.strip()]
    assert len(baris) == 1 and baris[0].split("\t")[1] == "B", aksi
    assert st["A"].get("butuh_env"), st


@uji("#17 QA lolos → Siap review (qc_visual=otomatis); QA gagal → QA gagal; status akhir manusia tidak ditimpa")
def _():
    d = salin()
    m = modul(d, "qa_status")
    a = d / "B9" / "X1"; a.mkdir(parents=True)
    (a / "status.json").write_text(json.dumps({"status": "QC visual"}))
    assert m.tetapkan(a, "lolos") == "Siap review"
    s = json.loads((a / "status.json").read_text()); assert s["qc_visual"] == "otomatis", s
    assert m.tetapkan(a, "gagal") == "QA gagal"
    assert "qc_visual" not in json.loads((a / "status.json").read_text())
    (a / "status.json").write_text(json.dumps({"status": "Terkirim"}))
    assert m.tetapkan(a, "gagal") == "Terkirim" and m.tetapkan(a, "lolos") == "Terkirim"


@uji("#18 R&D fitur: ide GPT valid dimuat, ide cacat ditolak; modul valid lulus, modul melanggar gagal; detect tahap fitur; katalog")
def _():
    d = salin()
    shutil.copytree(ROOT / "schemas", d / "schemas")
    (d / "library" / "fitur" / "modul").mkdir(parents=True)
    ide = {"tanggal": "2026-10-12", "ide": [{"id": "pengingat-kontrol", "nama": "Pengingat kontrol 6 bulan", "masalah_pasien": "Pasien lupa kontrol rutin dan baru datang saat sakit.",
           "solusi": "Pasien memilih tanggal perawatan terakhir lalu mendapat pesan WA pengingat siap kirim.", "alur_pengguna": ["pilih tanggal", "kirim WA"],
           "referensi": [{"nama": "contoh", "url": "https://example.com"}], "skor": {"manfaat": 4, "kemudahan": 5, "keunikan": 3, "aman_permenkes": 5},
           "risiko_permenkes": "rendah", "butuh_data": ["nomor WA"]}]}
    s = d / "src"; s.mkdir()
    (s / "FITUR-20261012_ide.json.md").write_text(json.dumps(ide))
    (s / "FITUR-20261013_ide.json.md").write_text('{"tanggal": "x", "ide": []}')
    subprocess.run([sys.executable, str(d / "scripts/fitur.py"), "pull", str(s)], cwd=d, check=True, capture_output=True)
    assert (d / "library/fitur/ide/2026-10-12.json").exists() and not (d / "library/fitur/ide/x.json").exists()
    assert "pengingat-kontrol" in (d / "library/fitur/ide/INDEX.md").read_text()
    arsip = pathlib.Path("/tmp/fitur-arsip.txt").read_text(); assert "FITUR-20261013_ide.json.md" in arsip
    m = d / "library/fitur/modul/pengingat-kontrol"; m.mkdir()
    isi = '<section id="fitur-pengingat-kontrol"><a href="https://wa.me/6281">Kirim</a></section><style>@media (prefers-reduced-motion: reduce){*{animation:none}}</style><script>var a=1;</script>' + "<!--x-->" * 400
    (m / "fitur.html").write_text(isi); (m / "demo.html").write_text("<html><body>" + isi * 2 + "</body></html>")
    (m / "manifest.json").write_text(json.dumps({"slug": "pengingat-kontrol", "nama": "Pengingat kontrol", "ringkas": "r", "manfaat_pasien": "m",
                                                "cocok_untuk": ["umum"], "butuh_data": ["wa"], "cara_pasang": "salin", "versi": "1.0"}))
    f = modul(d, "fitur")
    assert f.check_modul(m) == [], f.check_modul(m)
    (m / "fitur.html").write_text(isi.replace("</script>", "</script><p>diskon gratis</p><img src='https://evil.example/x.png'>"))
    assert len(f.check_modul(m)) >= 2
    (m / "fitur.html").write_text(isi); f.cmd_katalog()
    assert json.loads((d / "library/fitur/katalog.json").read_text())["fitur"][0]["slug"] == "pengingat-kontrol"
    c = modul(d, "codex_check"); ch = d / "ch.txt"; ch.write_text("library/fitur/modul/abc/fitur.html\n.codex/tugas/x.md\n")
    import io, contextlib
    b = io.StringIO()
    with contextlib.redirect_stdout(b): c.detect(str(ch))
    assert "stage=fitur" in b.getvalue() and "dir=library/fitur/modul/abc" in b.getvalue(), b.getvalue()


@uji("rapor pekerja: lulus sekali jalan dihitung benar")
def _():
    d = salin(); (d / "AGENTS.md").write_text("#\n")
    m = modul(d, "belajar"); m.TMP = d / "tmp"
    f = d / "o.txt"; f.write_text("✗ site/index.html tidak ada\n")
    m.catat("rakit", str(f), "B1/W1"); m.lulus("rakit", "B1/W1"); m.lulus("rakit", "B1/W2")
    m.gabung(); m.rapor()
    r = (d / "data" / "rapor.md").read_text()
    assert "| rakit | 7 hari | 2 | 1 | 50% |" in r, r


@uji("#20 slot live semua nonaktif → tes pool tetap memakai konfigurasi aktif sendiri; status menyebut SEMUA SLOT NONAKTIF")
def _():
    d = salin()
    cfg = json.loads((d / "data/codex-pool.json").read_text())
    assert all(x.get("aktif", True) for x in cfg["slot"]), cfg
    for x in cfg["slot"]: x["aktif"] = False
    (d / "data/codex-pool.json").write_text(json.dumps(cfg))
    r = subprocess.run([sys.executable, str(d / "scripts/codex_pool.py"), "status"], capture_output=True, text=True)
    assert r.returncode == 0 and "SEMUA SLOT NONAKTIF" in r.stdout, r.stdout + r.stderr


@uji("#21 klinik 'Menunggu cek fakta' yang risetnya dari Codex otomatis disediakan ke folder 02 untuk GPT-B")
def _():
    t = (ROOT / ".github/workflows/orkestrator.yml").read_text()
    assert "2d · Bus GPT · Sediakan riset hasil Codex untuk GPT-B" in t and "_riset.json.md" in t and "Menunggu cek fakta" in t, "langkah 2d hilang dari orkestrator.yml"


@uji("#22 riset tanpa nomor WA → kembali ke GPT-A sekali (riset lama dibawa di catatan), lalu Review manual; tidak ada WA yang dikarang")
def _():
    d = salin()
    shutil.copytree(ROOT / "templates", d / "templates")
    j = d / "batches" / "B1" / "W1"; j.mkdir(parents=True)
    def siapkan():
        (j / "job.json").write_text("{}"); (j / "konten.json").write_text("{}")
        (j / "riset.json").write_text(json.dumps({"nama": {"v": "Klinik Uji", "src": "u"}, "cabang": [{"nama": "A"}]}))
        (j / "status.json").write_text(json.dumps({"status": "Siap rakit", "oleh": "gpt-bus"}))
    pathlib.Path("/tmp/wa-balik.txt").unlink(missing_ok=True)
    siapkan(); m = modul(d, "rakit_template"); m.antre(5)
    st = json.loads((j / "status.json").read_text())
    assert st["status"] == "Riset di GPT" and st["percobaan_wa"] == 1, st
    assert not (j / "riset.json").exists() and "RISET LAMA" in (d / "bus-notes" / "B1-W1").read_text()
    assert pathlib.Path("/tmp/wa-balik.txt").read_text().strip() == "B1-W1"
    siapkan(); (j / "status.json").write_text(json.dumps({"status": "Siap rakit", "percobaan_wa": 1})); m.antre(5)
    st = json.loads((j / "status.json").read_text())
    assert st["status"] == "Review manual", st


@uji("#23 klinik 'Riset di GPT' tanpa surat tugas di Drive otomatis dibuatkan surat (pemulihan)")
def _():
    t = (ROOT / ".github/workflows/orkestrator.yml").read_text()
    assert "2e · Bus GPT · Pulihkan surat tugas yang hilang" in t and "Riset di GPT" in t and "RISET LAMA" in t, "langkah 2e hilang dari orkestrator.yml"


@uji("#24 pencari klinik via chat GPT: hasil CARI-* (dengan pagar ```json) masuk ke sourcing/<kota>-<waktu>/hasil.json; file rusak tetap diarsipkan")
def _():
    d = salin(); m = modul(d, "cari_chat")
    m.ROOT = d; (d / "data").mkdir(exist_ok=True); (d / "data" / "kota.txt").write_text("Bandung | Indonesia\nBogor | Indonesia\n")
    i = d / "in"; i.mkdir()
    (i / "CARI-bandung-1_hasil.json.md").write_text('```json\n{"kota": "Bandung", "klinik": [{"nama": "X", "rating": 4.8, "ulasan": 150}]}\n```')
    (i / "CARI-rusak_hasil.json.md").write_text("bukan json")
    m.ingest(str(i))
    hs = list((d / "sourcing").glob("bandung-*/hasil.json")); assert len(hs) == 1, hs
    assert json.loads(hs[0].read_text())["klinik"][0]["nama"] == "X"
    assert len(pathlib.Path("/tmp/cari-arsip.txt").read_text().split()) == 2


@uji("#25 perintah jembatan dengan variable terlarang tidak boleh mengubah file sama sekali; hasil CARI tipis tidak boleh menandai kota habis")
def _():
    d = salin(); m = modul(d, "jembatan")
    (d / "docs").mkdir(); (d / "docs" / "x.txt").write_text("a")
    cmd = d / "cmd"; cmd.mkdir()
    (cmd / "1.json").write_text(json.dumps({"id": "1", "ganti": {"docs/x.txt": [["a", "b"]]}, "variabel": {"JAHAT": "1"}}))
    m.terapkan(str(cmd))
    assert (d / "docs" / "x.txt").read_text() == "a", "file berubah walau perintah gagal"
    c = modul(d, "cari_chat"); c.ROOT = d
    i = d / "in2"; i.mkdir()
    (i / "CARI-x-1_hasil.json.md").write_text(json.dumps({"kota": "Kotax", "habis": True, "klinik": [{"nama": "A", "rating": 4.8, "ulasan": 150}]}))
    c.ingest(str(i))
    h = list((d / "sourcing").glob("kotax-*/hasil.json"))[0]
    assert json.loads(h.read_text())["habis"] is False


print("\n".join(f"{a} {b}" + (f" — {c}" if c else "") for a, b, c in hasil))
gagal = [h for h in hasil if h[0] == "❌"]
pathlib.Path("/tmp/jb").mkdir(exist_ok=True)
pathlib.Path("/tmp/jb/uji.txt").write_text("\n".join(f"{a} {b}" + (f" — {c}" if c else "") for a, b, c in gagal))
sys.exit(1 if gagal else 0)
