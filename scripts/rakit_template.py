#!/usr/bin/env python3
"""RAKIT TANPA AI: isi templates/klinik/base.html dari riset.json + konten.json → site/index.html.

  python scripts/rakit_template.py <folder_job>

Gratis & instan (tanpa Codex). Hanya memakai fakta dari riset.json; yang tidak pasti diberi tanda ✎.
Perawatan & keluhan memakai katalog baku berbahasa Indonesia; hanya layanan yang disebut riset/konten yang tampil.
Harga hanya yang jenis 'resmi_klinik' (bukan kisaran pasar). Aturan Permenkes: tanpa testimoni/rating/promo.
"""
import hashlib, html, json, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "templates" / "klinik"

# ---------- katalog perawatan baku ----------
# id, kategori, pola kata kunci, [nama, ringkas] id/en, "cocok jika" id/en, fakta tambahan
KATALOG = [
    ("scaling", "u", r"scaling|karang gigi|pembersihan", ["Scaling", "Membersihkan karang gigi dan plak agar gusi lebih sehat."], ["Scaling & polishing", "Removes tartar and plaque for healthier gums."],
     "gusi berdarah, ada karang gigi, atau gigi terlihat kusam.", "your gums bleed, there's tartar build-up, or teeth look dull."),
    ("tambal", "u", r"tambal|filling|restorasi", ["Tambal gigi", "Memperbaiki gigi berlubang dengan bahan sewarna gigi."], ["Fillings", "Repairs cavities with tooth-coloured material."],
     "ada gigi berlubang, atau gigi ngilu saat minum dingin atau makan manis.", "there's a cavity, or a tooth is sensitive to cold or sweets."),
    ("akar", "u", r"saluran akar|root canal|\bpsa\b|endodon", ["Perawatan saluran akar", "Menyelamatkan gigi yang sarafnya terinfeksi."], ["Root canal", "Saves a tooth with an infected nerve."],
     "lubang sudah dalam sampai saraf, atau ada nyeri berdenyut atau bengkak. Dokter memastikan setelah pemeriksaan.", "a cavity has reached the nerve, or there's throbbing pain or swelling. The dentist confirms after examination."),
    ("rontgen", "u", r"rontgen|x-?ray|panoramik|\bopg\b|radiograf", ["Rontgen gigi", "Gambaran gigi dan rahang untuk membantu diagnosis."], ["Dental X-ray", "An image of teeth and jaw to support diagnosis."],
     "dokter perlu melihat posisi gigi bungsu atau kondisi di bawah gusi.", "the dentist needs to see a wisdom tooth's position or what's below the gums."),
    ("anak", "u", r"anak|pedodon|pediatri|kids", ["Perawatan gigi anak", "Pemeriksaan dan perawatan gigi untuk anak."], ["Children's dentistry", "Check-ups and dental care for children."],
     "anak mulai tumbuh gigi, ada gigi berlubang, atau waktunya periksa rutin.", "your child's teeth are coming in, there's a cavity, or it's time for a routine check."),
    ("gusi", "u", r"gusi|periodon|gingiv|kuretase|gum", ["Perawatan gusi", "Menangani gusi bengkak, berdarah, atau turun."], ["Gum treatment", "Treats swollen, bleeding or receding gums."],
     "gusi sering berdarah, bengkak, atau terlihat turun.", "your gums often bleed, swell, or look receded."),
    ("cabut", "b", r"cabut|ekstraksi|extraction", ["Cabut gigi", "Mencabut gigi yang tidak bisa dipertahankan."], ["Extraction", "Removes a tooth that can't be saved."],
     "dokter menilai gigi tidak bisa diselamatkan setelah pemeriksaan.", "the dentist finds, after examination, that the tooth can't be saved."),
    ("bungsu", "b", r"bungsu|odontektomi|impaksi|wisdom", ["Operasi gigi bungsu", "Pengangkatan gigi bungsu yang tumbuh miring atau terpendam."], ["Wisdom tooth surgery", "Removes an impacted or tilted wisdom tooth."],
     "ada nyeri atau bengkak di ujung rahang. Rontgen membantu dokter melihat posisinya.", "there's pain or swelling at the back of the jaw. An X-ray helps the dentist see its position."),
    ("behel", "o", r"behel|kawat gigi|braces|ortodon", ["Behel", "Merapikan susunan gigi secara bertahap."], ["Braces", "Straightens teeth step by step."],
     "gigi berjejal atau tidak rapi. Pemeriksaan dan rencana perawatan dibuat dulu.", "teeth are crowded or crooked. An examination and treatment plan come first."),
    ("aligner", "o", r"aligner|invisalign|clear", ["Aligner (behel bening)", "Alat bening yang bisa dilepas untuk merapikan gigi."], ["Clear aligners", "Removable clear trays that straighten teeth."],
     "ingin merapikan gigi dengan alat yang tidak terlalu terlihat.", "you'd like to straighten teeth with a less visible appliance."),
    ("bleaching", "e", r"bleaching|pemutihan|whitening", ["Pemutihan gigi", "Mencerahkan warna gigi di klinik."], ["Teeth whitening", "Brightens tooth colour in-clinic."],
     "gigi kusam atau kekuningan. Dokter menilai apakah cukup dibersihkan atau perlu pemutihan.", "teeth look dull or yellowish. The dentist checks whether cleaning is enough or whitening is needed."),
    ("veneer", "e", r"veneer", ["Veneer", "Lapisan tipis di permukaan depan gigi untuk memperbaiki bentuk dan warna."], ["Veneers", "Thin shells on the front of teeth to improve shape and colour."],
     "bentuk atau warna gigi depan ingin diperbaiki.", "you'd like to improve the shape or colour of your front teeth."),
    ("palsu", "e", r"gigi palsu|gigi tiruan|denture", ["Gigi tiruan", "Mengganti gigi yang hilang, sebagian atau penuh."], ["Dentures", "Replaces missing teeth, partial or full."],
     "ada gigi yang hilang, sebagian atau penuh.", "teeth are missing, partially or fully."),
    ("crown", "e", r"crown|mahkota|bridge|jembatan", ["Crown & bridge", "Melindungi atau mengganti gigi dengan mahkota permanen."], ["Crown & bridge", "Protects or replaces teeth with fixed crowns."],
     "gigi perlu dilindungi, atau gigi yang hilang ingin diganti secara permanen.", "a tooth needs protecting, or a missing tooth is to be replaced with a fixed one."),
    ("implan", "e", r"implan|implant", ["Implan gigi", "Akar gigi tiruan yang ditanam untuk menggantikan gigi hilang."], ["Dental implants", "An artificial root placed to replace a missing tooth."],
     "ada gigi yang hilang dan ingin diganti secara permanen. Kondisi tulang dinilai dulu.", "a tooth is missing and you want a permanent replacement. Bone condition is assessed first."),
]
# keluhan untuk "Cek 30 detik": [chip, ikon, judul, teks, urgensi, [id katalog]]
KELUHAN = [
    (["Ngilu", "Ngilu saat minum dingin atau makan manis", "Sering berkaitan dengan email gigi yang menipis, lubang kecil, atau karang gigi di dekat gusi."],
     ["Sensitive", "Sensitive to cold or sweets", "Often linked to worn enamel, small cavities or tartar near the gums."], "sens", 1, ["periksa", "scaling", "tambal"]),
    (["Berlubang", "Ada lubang, walau belum sakit", "Lubang yang dibiarkan bisa membesar sampai ke saraf. Makin cepat dirawat, biasanya makin sederhana perawatannya."],
     ["Cavity", "A hole, even if it doesn't hurt", "An untreated cavity can grow to the nerve. The earlier it's treated, the simpler the treatment usually is."], "cav", 2, ["tambal", "akar"]),
    (["Nyeri berdenyut", "Nyeri berdenyut atau bengkak", "Bisa jadi tanda peradangan saraf gigi. Sebaiknya segera diperiksa."],
     ["Throbbing pain", "Throbbing pain or swelling", "May be a sign of nerve inflammation. It's best examined soon."], "thr", 3, ["periksa", "akar", "cabut"]),
    (["Gigi bungsu", "Nyeri di ujung rahang", "Gigi bungsu yang tumbuh miring bisa menimbulkan nyeri dan bengkak. Rontgen membantu dokter melihat posisinya."],
     ["Wisdom tooth", "Pain at the back of the jaw", "An impacted wisdom tooth can cause pain and swelling. An X-ray helps the dentist see its position."], "wis", 2, ["rontgen", "bungsu"]),
    (["Gusi berdarah", "Gusi bengkak atau berdarah", "Biasanya karena karang gigi dan plak. Pembersihan oleh dokter gigi sering jadi langkah pertama."],
     ["Bleeding gums", "Swollen or bleeding gums", "Usually caused by tartar and plaque. Professional cleaning is often the first step."], "gum", 1, ["scaling", "gusi"]),
    (["Gigi kuning", "Gigi kusam atau kekuningan", "Sering karena noda kopi, teh, atau rokok. Dokter menilai apakah cukup dibersihkan atau perlu pemutihan."],
     ["Yellow teeth", "Dull or yellowish teeth", "Often stains from coffee, tea or smoking. The dentist checks whether cleaning is enough or whitening is needed."], "yel", 1, ["scaling", "bleaching"]),
    (["Tidak rapi", "Gigi berjejal atau tidak rapi", "Susunan gigi bisa dirapikan bertahap. Pemeriksaan dan rencana perawatan dibuat dulu."],
     ["Crooked", "Crowded or crooked teeth", "Teeth can be straightened step by step. An examination and treatment plan come first."], "cro", 1, ["konsul_behel", "behel", "aligner"]),
    (["Gigi hilang", "Ada gigi yang hilang", "Gigi yang hilang bisa diganti. Dokter menjelaskan pilihannya setelah pemeriksaan."],
     ["Missing tooth", "A missing tooth", "A missing tooth can be replaced. The dentist explains the options after an examination."], "mis", 1, ["palsu", "crown", "implan"]),
]
EKSTRA_NAMA = {"periksa": ("Pemeriksaan", "Examination", "?"), "konsul_behel": ("Konsultasi behel", "Braces consultation", "?")}
PALET = [  # aksen, teks-aksen, aksen-terang, tint
    ("#2a8c8a", "#1d6664", "#8fd3cf", "#e4f3f2"), ("#3a6ea5", "#2a5280", "#9fc0e6", "#e6eef7"),
    ("#a88a5c", "#7a5f34", "#d9bf8f", "#f3ede3"), ("#b0666e", "#8a4750", "#e6aab0", "#f6e8ea"),
    ("#5f8a4f", "#45663a", "#b3d3a5", "#ebf2e7"), ("#7a5c99", "#5a4174", "#c3aee0", "#efe9f6"),
]
HARI = {"min": 0, "sen": 1, "sel": 2, "rab": 3, "kam": 4, "jum": 5, "sab": 6}
TZ = {"WIB": 7, "WITA": 8, "WIT": 9}
LARANG = r"\b(terbaik|termurah|dijamin|jaminan|gratis|promo|diskon|testimoni)\b"


def template_dasar():
    """base.html dibuat otomatis dari contoh baku (library/referensi/atabara.html) oleh scripts/buat_base.py,
    disimpan di /tmp (tidak di-commit). Contoh baku berubah → template ikut berubah; konversi gagal → berhenti keras."""
    import subprocess
    f = TPL / "base.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    tmp = pathlib.Path("/tmp/mgs-template/base.html")
    if not tmp.exists():
        r = subprocess.run([sys.executable, str(ROOT / "scripts/buat_base.py"), str(ROOT / "library/referensi/atabara.html"), str(tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("✗ template dasar gagal dibuat dari contoh baku: " + (r.stdout + r.stderr)[-400:])
    return tmp.read_text(encoding="utf-8")


def v(x):
    """nilai fakta: {'v':..} → isi; string → string; lainnya None"""
    if isinstance(x, dict):
        return x.get("v")
    return x


def teks(x, lang="id"):
    if isinstance(x, dict):
        return x.get(lang) or x.get("id") or x.get("v") or ""
    return x or ""


def rp(n):
    n = float(n)
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}".replace(".0", "").replace(".", ",") + " jt"
    else:
        s = f"{round(n / 1000):.0f} rb"
    return s


def jam(teks_jam):
    """'10-20' / '09.00-21.00' / '08.00-12.00, 17.00-21.00' / 'tutup' → [[a,b],...] dalam jam desimal"""
    if not teks_jam or re.search(r"tutup|libur|closed", str(teks_jam), re.I):
        return []
    seg = []
    for a, b in re.findall(r"(\d{1,2}(?:[.:]\d{2})?)\s*[-–]\s*(\d{1,2}(?:[.:]\d{2})?)", str(teks_jam)):
        f = lambda t: int(re.split(r"[.:]", t)[0]) + (int(re.split(r"[.:]", t)[1]) / 60 if re.search(r"[.:]", t) else 0)
        x, y = f(a), f(b)
        if 0 <= x < y <= 24:
            seg.append([round(x, 2), round(y, 2)])
    return seg


def hp(nomor):
    nomor = re.split(r"\s*(?:/|,|;|\|\bdan\b|\batau\b|\bor\b)\s*", str(nomor or ""))[0]  # pelajaran #40: kolom berisi >1 nomor -> ambil yang pertama
    d = re.sub(r"\D", "", str(nomor or ""))
    if d.startswith("0"):
        d = "62" + d[1:]
    return d if len(d) >= 10 else ""


def tampil_tel(nomor):
    nomor = re.split(r"\s*(?:/|,|;|\|\bdan\b|\batau\b|\bor\b)\s*", str(nomor or ""))[0]  # pelajaran #40
    d = re.sub(r"\D", "", str(nomor or ""))
    if d.startswith("62"):
        d = "0" + d[2:]
    return " ".join([d[:4], d[4:8], d[8:]]).strip() if d else ""


def ringkas_jam(HRS, L):
    hari = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"] if L == "ms" else ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    f = lambda h: f"{int(h):02d}.{round((h % 1) * 60):02d}"
    grp = []
    for d in [1, 2, 3, 4, 5, 6, 0]:
        val = ", ".join(f"{f(a)}–{f(b)}" for a, b in HRS[d]) or ("Tutup" if L == "ms" else "Closed")
        if grp and grp[-1][1] == val:
            grp[-1][0].append(d)
        else:
            grp.append([[d], val])
    return "<br>".join(f"<span class='nw'>{hari[g[0]]}{'–' + hari[g[-1]] if len(g) > 1 else ''} {v}</span>" for g, v in grp[:3])


def pilih_katalog(riset, konten):
    teks_layanan = [str(x) for x in (riset.get("layanan") or [])] + [teks(l.get("nama")) for l in konten.get("layanan") or []]
    gabung = " | ".join(teks_layanan).lower()
    ada = [k for k in KATALOG if re.search(k[2], gabung, re.I)]
    # ringkasan dari konten untuk item yang cocok
    ringkas = {}
    for l in konten.get("layanan") or []:
        nm = teks(l.get("nama")).lower()
        for k in KATALOG:
            if re.search(k[2], nm, re.I) and k[0] not in ringkas:
                ringkas[k[0]] = l.get("ringkas") or {}
                break
    # layanan konten yang tidak ada di katalog → item tambahan
    tambahan = []
    for l in konten.get("layanan") or []:
        nm = teks(l.get("nama"))
        if not any(re.search(k[2], nm, re.I) for k in KATALOG):
            tambahan.append(l)
    return ada, ringkas, tambahan


def harga_resmi(riset):
    out = {}
    for h in riset.get("harga") or []:
        if h.get("jenis") != "resmi_klinik" or not h.get("min"):
            continue
        for k in KATALOG:
            if re.search(k[2], str(h.get("perawatan", "")), re.I):
                lo, hi = h.get("min"), h.get("max") or h.get("min")
                out[k[0]] = "Rp" + rp(lo) + ("" if hi == lo else "–" + rp(hi))
                break
    return out


def bangun(job_dir):
    d = pathlib.Path(job_dir)
    riset = json.loads((d / "riset.json").read_text(encoding="utf-8"))
    konten = json.loads((d / "konten.json").read_text(encoding="utf-8"))
    job = json.loads((d / "job.json").read_text(encoding="utf-8")) if (d / "job.json").exists() else {}
    T = json.loads((TPL / "teks.json").read_text(encoding="utf-8"))
    base = template_dasar()

    nama = re.sub(r"\s*\(.*?\)\s*", " ", str(v(riset.get("nama")) or job.get("nama") or "Klinik Gigi")).strip()
    kota = riset.get("kota") or job.get("kota") or ""
    pendek = nama
    cab_raw = riset.get("cabang") or []
    # pelajaran #38: riset GPT tidak menyimpulkan WA dari nomor seluler -> banyak klinik gagal rakit. Nomor seluler (628xx) di kolom telepon dipakai sebagai kontak WA.
    wa_ada = any(hp(v(c.get("wa"))) or hp(v(c.get("telepon"))).startswith("628") for c in cab_raw)
    if not cab_raw or not wa_ada:
        raise SystemExit("✗ riset.json: cabang/nomor WA kosong — tidak bisa dirakit template")

    # ---------- cabang ----------
    CAB = []
    for c in cab_raw:
        j = (v(c.get("jam")) or {})
        HRS = {i: [] for i in range(7)}
        if isinstance(j, dict):
            for k, val in j.items():
                if k[:3].lower() in HARI:
                    HRS[HARI[k[:3].lower()]] = jam(val)
        alamat = str(v(c.get("alamat")) or "")
        cn = c.get("nama") or nama
        CAB.append({"nama": cn, "pendek": alamat.split(",")[0] if alamat else cn, "alamat": alamat,
                    "wa": hp(v(c.get("wa"))) or hp(v(c.get("telepon"))), "tel": "+" + hp(v(c.get("telepon"))) if hp(v(c.get("telepon"))) else "",
                    "tel_t": tampil_tel(v(c.get("telepon")) or v(c.get("wa"))), "HRS": HRS,
                    "q": f"{cn}, {alamat}" if alamat else f"{cn} {kota}", "maps": None})
    semua_jam = [s for c in CAB for d_ in c["HRS"].values() for s in d_]
    jam_ada = bool(semua_jam)
    if not jam_ada:  # jam tidak diketahui → tampil umum 09–21 dengan tanda ✎
        for c in CAB:
            c["HRS"] = {i: [[9, 21]] for i in range(7)}

    # ---------- perawatan ----------
    ada, ringkas, tambahan = pilih_katalog(riset, konten)
    harga = harga_resmi(riset)
    spesialis = bool(re.search(r"spesialis", json.dumps(riset.get("keunggulan") or [], ensure_ascii=False) + " ".join(map(str, riset.get("layanan") or [])), re.I))
    TR = []
    for k in ada:
        kid, cat, _, ID, EN, fid, fen = k
        r = ringkas.get(kid) or {}
        item = {"c": cat, "id_k": kid, "ms": [ID[0], r.get("id") or ID[1]], "en": [EN[0], r.get("en") or EN[1]],
                "p": harga.get(kid), "fit": {"ms": fid, "en": fen}, "f": []}
        if kid == "rontgen":
            item["q"] = 1; item["f"] = ["tf_opg"]
        if kid == "bungsu" and any(x[0] == "rontgen" for x in ada):
            item["f"] = ["tf_opg"]
        if kid in ("behel", "anak") and spesialis:
            item["f"].append("tf_sp")
        if kid == "behel":
            item["calc"] = 1
        TR.append(item)
    for l in tambahan[:4]:
        TR.append({"c": "u", "ms": [teks(l.get("nama")), teks(l.get("ringkas"))], "en": [teks(l.get("nama"), "en"), teks(l.get("ringkas"), "en")],
                   "p": None, "fit": {"ms": "Anda ingin tahu apakah layanan ini sesuai dengan kebutuhan Anda.", "en": "you'd like to know whether this service suits your needs."}, "f": []})
    if not TR:
        raise SystemExit("✗ riset.json/konten.json: tidak ada layanan yang dikenali")

    nama_k = {k[0]: (k[3][0], k[4][0]) for k in KATALOG}
    nama_k.update({k: (a, b) for k, (a, b, _) in EKSTRA_NAMA.items()})
    KEL = {"ms": [], "en": []}
    for (idt, ent, ico, urg, ids) in KELUHAN:
        daftar_id, daftar_en = [], []
        for x in ids:
            p = "?" if x in EKSTRA_NAMA else harga.get(x)
            daftar_id.append([nama_k[x][0], p]); daftar_en.append([nama_k[x][1], p])
        KEL["ms"].append([idt[0], ico, idt[1], idt[2], urg, daftar_id])
        KEL["en"].append([ent[0], ico, ent[1], ent[2], urg, daftar_en])

    # ---------- FAQ ----------
    FAQ = {"ms": [], "en": []}
    for f in (konten.get("faq") or [])[:8]:
        a_id = teks(f.get("a")); a_en = teks(f.get("a"), "en")
        ragu = bool(re.search(r"\b(biaya|harga|rp|jam|buka|mulai)\b", a_id, re.I))
        FAQ["ms"].append([teks(f.get("q")), html.escape(a_id), ragu]); FAQ["en"].append([teks(f.get("q"), "en"), html.escape(a_en), ragu])

    # ---------- teks khusus klinik ----------
    hero = konten.get("hero") or {}
    anak = any(k[0] == "anak" for k in ada)
    hari_buka = [i for i in range(7) if CAB[0]["HRS"][i]]
    tutup_akhir = max((s[1] for s in semua_jam), default=21)
    fmt = lambda h: f"{int(h):02d}.{round((h % 1) * 60):02d}"
    if len(hari_buka) == 7:
        f1 = ("Buka setiap hari", f"hingga pukul {fmt(tutup_akhir)}", "Open every day", f"until {int(tutup_akhir)}:00")
    else:
        f1 = ("Jam praktik", f"hingga pukul {fmt(tutup_akhir)}", "Opening hours", f"until {int(tutup_akhir)}:00")
    chips = [("clock", "#lokasi", "", f1, not jam_ada)]
    if len(CAB) > 1:
        chips.append(("pin", "#lokasi", "", (f"{len(CAB)} lokasi", f"di {kota}" if kota else "pilih yang terdekat", f"{len(CAB)} locations", f"in {kota}" if kota else "choose the nearest"), False))
    if spesialis:
        chips.append(("cap", "#dokter", "", ("Dokter gigi spesialis", "sesuai kebutuhan perawatan", "Specialist dentists", "for specific treatments"), False))
    if anak:
        chips.append(("blocks", "#kids", "", ("Perawatan gigi anak", "untuk si kecil", "Children's dentistry", "for little ones"), False))
    if any(k[0] == "rontgen" for k in ada):
        chips.append(("scan", "#rawatan", ' data-tr="%d"' % next(i for i, x in enumerate(TR) if x.get("id_k") == "rontgen"), ("Rontgen gigi", "di klinik", "Dental X-ray", "in-clinic"), False))
    chips.append(("wa", "#", ' data-wa="book"', ("Janji lewat WhatsApp", "langsung ke klinik", "Book on WhatsApp", "straight to the clinic"), False))
    chips = chips[:4]
    proof, extra = [], {"ms": {}, "en": {}}
    for i, (ic, href, attr, tx, ragu) in enumerate(chips, 1):
        extra["ms"][f"f{i}a"], extra["ms"][f"f{i}b"], extra["en"][f"f{i}a"], extra["en"][f"f{i}b"] = tx
        proof.append(f'    <a class="pf" href="{href}"{attr}><span class="ic"><svg class="i"><use href="#i-{ic}"/></svg></span><span class="tx"><b data-i="f{i}a"></b><span class="sub" data-i="f{i}b"></span>'
                     + ('<span class="chk" data-i="chk"></span>' if ragu else '') + '</span><svg class="i go"><use href="#i-ar"/></svg></a>')

    fk = konten.get("fitur_khas") or {}
    multi = len(CAB) > 1
    dokter = [x for x in (riset.get("dokter") or []) if v(x.get("nama") if isinstance(x, dict) else x)]
    ans = None
    hb = next((h for h in riset.get("harga") or [] if h.get("jenis") == "resmi_klinik" and re.search("behel|braces|ortodon", str(h.get("perawatan")), re.I)), None)
    if hb and hb.get("min"):
        lo, hi = int(hb["min"]), int(hb.get("max") or hb["min"] * 1.5)
        ans = {"min": lo, "max": max(hi, lo + 1_000_000), "mid": round((lo + hi) / 2, -5)}
    for L, lang in (("ms", "id"), ("en", "en")):
        e = extra[L]
        e["pv"] = ("<b>Pratinjau konsep</b> · bukan situs resmi {n} · tanda <span class='chk' style='margin:0'>✎ cek</span> = info perlu dikonfirmasi klinik" if L == "ms"
                   else "<b>Concept preview</b> · not the official {n} website · <span class='chk' style='margin:0'>✎ verify</span> = details to be confirmed by the clinic").format(n=nama)
        e["ttl"] = f"{nama} — " + ("Konsep Website" if L == "ms" else "Website Concept")
        e["logo_a"] = f"Logo {nama}"
        e["h1a"] = nama
        e["h1b"] = teks(hero.get("judul"), lang) or (f"Klinik gigi di {kota}." if L == "ms" else f"A dental clinic in {kota}.")
        e["hl"] = teks(hero.get("sub"), lang)
        e["lh"] = teks(fk.get("judul"), lang) if multi and fk.get("judul") else ((f"Mudah ditemukan di {kota}." if L == "ms" else f"Easy to find in {kota}.") if kota else e.get("lk", ""))
        e["ll"] = teks(fk.get("penjelasan"), lang) if multi and fk.get("penjelasan") else ("Arahkan navigasi langsung dengan Waze atau Google Maps." if L == "ms" else "Navigate straight there with Waze or Google Maps.")
        e["lcap"] = CAB[0]["nama"]; e["lalt"] = nama
        e["f_call"] = ("Telepon " if L == "ms" else "Call ") + CAB[0]["tel_t"]
        e["f_hrs"] = ringkas_jam(CAB[0]["HRS"], L)
        e["ft_disc"] = ("Pratinjau konsep — bukan situs resmi {n}." if L == "ms" else "Concept preview — not the official {n} website.").format(n=nama)
        e["fp"] = teks(konten.get("cta"), lang) or ("Ceritakan keluhan Anda dan waktu yang cocok. Kami bantu atur janji temunya." if L == "ms" else "Tell us your concern and a time that suits you. We'll help arrange your appointment.")
        e["dl"] = (("Nama dokter di bawah dari sumber publik; keahlian dan hari praktik diisi oleh klinik. Potret adalah ilustrasi, bukan foto asli." if dokter else
                    "Nama, keahlian, dan hari praktik setiap dokter akan diisi oleh klinik. Potret di bawah adalah ilustrasi, bukan foto asli.") if L == "ms" else
                   ("Names come from public sources; expertise and practice days will be filled in by the clinic. Portraits are illustrations, not real photos." if dokter else
                    "Each dentist's name, expertise and practice days will be filled in by the clinic. The portraits below are illustrations, not real photos."))
        for i in (1, 2, 3):
            e[f"dot{i}"] = (f"Dokter {i} dari 3" if L == "ms" else f"Dentist {i} of 3")
        if not ans:
            e["n3"] = "Dokter" if L == "ms" else "Dentists"
            e["a_bc"] = ""; e["a_range"] = ""
        else:
            e["a_bc"] = ("Behel · mulai " if L == "ms" else "Braces · from ") + "<span class='nw'>Rp" + rp(ans["min"]) + "</span>"
            e["a_range"] = ("Rentang kalkulator " if L == "ms" else "Calculator range ") + f"Rp{rp(ans['min'])} – Rp{rp(ans['max'])}."
        # teks umum + sapaan klinik
        base_t = {k: (x.replace("{pendek}", pendek) if isinstance(x, str) else x) for k, x in T[lang].items()}
        base_t.update(e)
        extra[L] = base_t

    # dokter di kartu
    def nm_dok(x):
        n = v(x.get("nama")) if isinstance(x, dict) else x
        return html.escape(str(n))
    dok = [nm_dok(x) for x in dokter[:3]]
    kosong = 'drg. ____ <span class="chk" data-i="chk"></span>'

    # warna
    h = int(hashlib.md5(nama.encode()).hexdigest(), 16)
    pal = PALET[h % len(PALET)]

    CFG = {"T": extra, "KEL": KEL, "TR": TR, "FAQ": FAQ, "CAB": CAB, "tz": TZ.get(str(riset.get("zona_waktu", "WIB")).upper(), 7),
           "band": f"{nama.upper()}   ◆   {kota.upper() or 'KLINIK GIGI'}", "ans": ans}

    inisial = "".join(w[0] for w in re.findall(r"[A-Za-z]+", nama) if w.lower() not in ("dental", "klinik", "clinic", "care", "drg", "dan", "by"))[:2].upper() or nama[:2].upper()
    logo_svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="26" fill="{pal[0]}"/>'
                f'<text x="48" y="61" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-weight="700" font-size="{40 if len(inisial) == 1 else 34}" fill="#fff">{html.escape(inisial)}</text></svg>')
    logo = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(logo_svg)
    kata = nama.split()
    brand1 = " ".join(kata[:2]).upper() if len(kata) > 2 else nama.upper()
    brand2 = " ".join(kata[2:]).upper() if len(kata) > 2 else ("KLINIK GIGI" if "dental" not in nama.lower() else "")
    ig = str(v(riset.get("instagram")) or "").lstrip("@").strip()
    email = str(v(riset.get("email")) or "")
    c0 = CAB[0]
    isi = {
        "TITLE": html.escape(f"{nama} — Konsep Website"), "DESC": html.escape(f"Konsep website {nama}, {kota}. Buat janji lewat WhatsApp."),
        "LOGO": logo, "NAMA": html.escape(nama), "BRAND1": html.escape(brand1), "BRAND2": html.escape(brand2), "KOTA_UP": html.escape(kota.upper()),
        "N3": "ansuran" if ans else "dokter", "TEL_TAMPIL": html.escape(c0["tel_t"]), "TEL_URI": c0["tel"] or "+" + c0["wa"],
        "SNAP": html.escape(c0["nama"]), "PROOF": "\n".join(proof),
        "ANS_HIDDEN": "" if ans else " hidden", "KIDS_HIDDEN": "" if anak else " hidden",
        "ANS_MIN": str(ans["min"] if ans else 3000000), "ANS_MAX": str(ans["max"] if ans else 8000000), "ANS_STEP": "100000",
        "ANS_MID": str(int(ans["mid"]) if ans else 5000000), "ANS_MID_T": f"{int(ans['mid'] if ans else 5000000):,}".replace(",", "."),
        "ANS_MIN_T": "Rp" + rp(ans["min"] if ans else 3000000), "ANS_MAX_T": "Rp" + rp(ans["max"] if ans else 8000000), "ANS_DEP_T": "500.000",
        "DOK1": dok[0] if len(dok) > 0 else kosong, "DOK2": dok[1] if len(dok) > 1 else kosong, "DOK3": dok[2] if len(dok) > 2 else kosong,
        "ALAMAT_PENDEK": html.escape(c0["pendek"]), "ALAMAT": html.escape(c0["alamat"]),
        "EMAIL_LINK": (f'<a class="fa" href="mailto:{html.escape(email)}"><svg class="i" style="width:16px;height:16px"><use href="#i-mail"/></svg>{html.escape(email)}</a>' if email else ""),
        "SOSMED": (f'<div><h4 data-i="ft_f"></h4><div class="soc"><a href="https://instagram.com/{html.escape(ig)}" target="_blank" rel="noopener" aria-label="Instagram @{html.escape(ig)}"><svg class="i"><use href="#i-ig"/></svg></a></div><p style="margin-top:12px;font-size:13px">@{html.escape(ig)}</p></div>' if ig else "<div></div>"),
        "TAGLINE": html.escape(teks(hero.get("judul")) or kota),
    }
    out = base
    for k, val in isi.items():
        out = out.replace("{{" + k + "}}", val)
    js = json.dumps(CFG, ensure_ascii=False).replace("</", "<\\/")
    out = out.replace("/*@@CFG@@*/null", js)
    # warna aksen
    for lama, baru in zip(("#a88a5c", "#7a5f34", "#d9bf8f", "#f3ede3"), pal):
        out = re.sub(re.escape(lama), baru, out, flags=re.I)
    out = re.sub(r"0xa88a5c", "0x" + pal[0][1:], out, flags=re.I)
    sisa = re.findall(r"\{\{[A-Z0-9_]+\}\}", out)
    if sisa:
        raise SystemExit(f"✗ placeholder tersisa: {sisa}")
    (d / "site").mkdir(exist_ok=True)
    (d / "site" / "index.html").write_text(out, encoding="utf-8")
    return out


def periksa(out, d):
    """cek mandiri ringan (cek lengkap tetap codex_check.py)"""
    masalah = []
    teks_saja = re.sub(r"<script.*?</script>|<style.*?</style>", " ", out, flags=re.S)
    for m in re.finditer(LARANG, teks_saja + json.dumps(json.loads(re.search(r"const CFG=(\{.*?\});\n", out, re.S).group(1))["T"], ensure_ascii=False), re.I):
        masalah.append(f"kata terlarang Permenkes: {m.group(0)}")
    if re.search(r"(?i)atabara|kuantan|temujanji|pergigian|\bRM\d", out):
        masalah.append("sisa teks contoh baku / istilah Malaysia")
    if len(out) < 30_000:
        masalah.append("halaman terlalu kecil")
    return masalah


def balik_riset(d, job):
    """Pelajaran #22: riset tanpa nomor WA tidak bisa dirakit template (dan tidak boleh dikarang) → kembalikan ke GPT-A SEKALI untuk mencari WA; masih kosong → Review manual."""
    st = json.loads((d / "status.json").read_text())
    n = int(st.get("percobaan_wa", 0)) + 1
    if n >= 2:
        st.update(status="Review manual", oleh="template", percobaan_wa=n, catatan="nomor WA tidak ditemukan setelah riset ulang — putuskan manual")
        (d / "status.json").write_text(json.dumps(st, ensure_ascii=False))
        print(f"↪ {job}: tetap tanpa nomor WA setelah riset ulang → Review manual"); return
    key = job.replace("/", "-")
    lama = (d / "riset.json").read_text(encoding="utf-8") if (d / "riset.json").exists() else "{}"
    (ROOT / "bus-notes").mkdir(exist_ok=True)
    (ROOT / "bus-notes" / key).write_text(
        "REVISI: riset sebelumnya TIDAK punya nomor WhatsApp pada cabang mana pun, sehingga website tidak bisa dirakit. "
        "Cari nomor WA/telepon resmi klinik (situs, Google Maps, Instagram, Linktree, Halodoc/Alodokter) dan alamat bila masih kosong. "
        "Tidak ketemu = v null, src null (JANGAN menebak). Perbaiki riset lama berikut, jangan mulai dari nol; tulis ulang riset dan konten lengkap.\n\nRISET LAMA:\n" + lama + "\n", encoding="utf-8")
    for f in ("riset.json", "konten.json", "cekfakta.json"):
        (d / f).unlink(missing_ok=True)
    for k in [k for k in st if k.startswith("failover")]:
        st.pop(k)
    st.update(status="Riset di GPT", oleh="template", percobaan=0, percobaan_wa=n)
    (d / "status.json").write_text(json.dumps(st, ensure_ascii=False))
    with open("/tmp/wa-balik.txt", "a") as fh:
        fh.write(key + "\n")
    print(f"↪ {job}: tanpa nomor WA → dikembalikan ke GPT-A untuk riset ulang")


def antre(batas=20):
    """Rakit semua klinik 'Siap rakit' (riset+konten ada, site belum ada). Lulus cek → status Siap review (oleh=template).
    Gagal → site dihapus lagi supaya jalur Codex (mode hibrida) yang mengerjakan; kesalahan dicatat ke loop belajar."""
    import subprocess
    n_ok = n_gagal = 0
    for st in sorted((ROOT / "batches").glob("B*/*/status.json")):
        if n_ok + n_gagal >= int(batas):
            break
        d = st.parent
        try:
            if json.loads(st.read_text()).get("status") != "Siap rakit":
                continue
        except Exception:
            continue
        if (d / "site" / "index.html").exists() or not (d / "riset.json").exists() or not (d / "konten.json").exists():
            continue
        job = str(d.relative_to(ROOT / "batches"))
        log = pathlib.Path("/tmp/tpl-" + job.replace("/", "-") + ".txt")
        try:
            out = bangun(d)
            m = ["✗ " + x for x in periksa(out, d)]
            r = subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "check", str(d), "rakit"], capture_output=True, text=True)
            teks_cek = r.stdout + "\n".join(m)
            lulus = r.returncode == 0 and not m
        except SystemExit as e:
            teks_cek, lulus = str(e), False
        except Exception as e:
            teks_cek, lulus = f"✗ error rakit_template: {type(e).__name__}: {e}", False
        log.write_text(teks_cek)
        if lulus:
            subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "finish", str(d), "rakit", "template"])
            subprocess.run([sys.executable, str(ROOT / "scripts/belajar.py"), "lulus", "rakit-template", job])
            n_ok += 1; print(f"✅ {job} dirakit template → Siap review")
        else:
            (d / "site" / "index.html").unlink(missing_ok=True)
            subprocess.run([sys.executable, str(ROOT / "scripts/belajar.py"), "catat", "rakit-template", str(log), job])
            n_gagal += 1; print(f"❌ {job} gagal template (diserahkan ke Codex bila hibrida):\n" + "\n".join(l for l in teks_cek.splitlines() if l.startswith("✗"))[:600])
            if "nomor WA kosong" in teks_cek:
                balik_riset(d, job)
    print(f"rakit-template: {n_ok} lulus, {n_gagal} gagal")


if __name__ == "__main__":
    if sys.argv[1] == "--antre":
        antre(sys.argv[2] if len(sys.argv) > 2 else 20)
        sys.exit(0)
    d = sys.argv[1]
    out = bangun(d)
    m = periksa(out, d)
    for x in m:
        print("✗", x)
    print(("GAGAL" if m else "LULUS") + f" rakit-template {d} ({len(out)//1024} KB)")
    sys.exit(1 if m else 0)
