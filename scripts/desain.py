#!/usr/bin/env python3
"""DESAIN PER KLINIK (pelajaran #43): preview tidak boleh seragam "khas Atabara".

Dipanggil rakit_template.py setelah template diisi. Bahan dari batches/Bxx/Wyy/desain.json
(dibuat GPT-A: warna & logo asli, foto klinik, gaya, fokus layanan). Tanpa desain.json pun
tiap klinik tetap beda: gaya & urutan ditebak dari layanan, warna dari palet cadangan.

  muat(d, riset, konten)  -> dict desain (sudah dilengkapi tebakan)
  palet(DS)               -> (aksen, teks-aksen, aksen-terang, tint) dari warna brand, atau None
  terapkan(out, DS, logo_lama, nama) -> html dengan tema, font, logo, foto, urutan bagian

Uji: python scripts/desain.py <index.html> <desain.json> <keluar.html>
"""
import base64, hashlib, io, json, pathlib, re, subprocess, sys, urllib.request

GAYA = {
    # head, body, sig, link google fonts, skala radius, latar
    "elegan": dict(head="Fraunces", body="Manrope", sig="Fraunces",
                   fonts="family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=Manrope:wght@400..700",
                   r=1.0, bg="#f6f4ef", paper="#fbfaf6", campur=0.04),
    "klinis": dict(head="Plus Jakarta Sans", body="Inter", sig="Instrument Serif",
                   fonts="family=Plus+Jakarta+Sans:ital,wght@0,400..800;1,400..800&family=Inter:wght@400..700&family=Instrument+Serif:ital@0;1",
                   r=0.55, bg="#f3f6f9", paper="#fafcfd", campur=0.03),
    "ramah": dict(head="Nunito", body="Nunito Sans", sig="Caveat",
                  fonts="family=Nunito:ital,wght@0,400..900;1,400..900&family=Nunito+Sans:wght@400..800&family=Caveat:wght@500..700",
                  r=1.3, bg="#f7f6f2", paper="#fcfbf8", campur=0.07),
    "berani": dict(head="Space Grotesk", body="DM Sans", sig="Instrument Serif",
                   fonts="family=Space+Grotesk:wght@400..700&family=DM+Sans:ital,wght@0,400..700;1,400..700&family=Instrument+Serif:ital@0;1",
                   r=0.4, bg="#f4f4f2", paper="#fafaf9", campur=0.03),
}
FOKUS = ("behel", "anak", "implan", "estetik", "umum", "spesialis", "multi-cabang")


# ---------------- warna ----------------
def _rgb(h):
    h = str(h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return None
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(x))) for x in c)


def _mix(a, b, t):  # t=0 -> a, t=1 -> b
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _lum(c):
    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _kontras(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _gelapkan(c, lawan, min_k):
    hitam = (12, 13, 15)
    for i in range(41):
        x = _mix(c, hitam, i / 40)
        if _kontras(x, lawan) >= min_k:
            return x
    return hitam


def _jenuh(c):
    return max(c) - min(c)


def palet(DS):
    a = _rgb((DS.get("warna") or {}).get("utama"))
    if not a:
        return None
    putih, kertas = (255, 255, 255), (251, 250, 247)
    if _jenuh(a) < 18 and _lum(a) < 0.05:  # brand hitam/abu gelap -> aksen dari warna kedua bila ada
        a2 = _rgb((DS.get("warna") or {}).get("kedua"))
        if a2 and _jenuh(a2) >= 18:
            a = a2
    aks = _gelapkan(a, putih, 3.0)
    teks = _gelapkan(a, kertas, 4.8)
    terang = _mix(a, putih, 0.45)
    tint = _mix(a, putih, 0.9)
    return tuple(_hex(x) for x in (aks, teks, terang, tint))


# ---------------- tebakan bila GPT belum mengisi ----------------
def _teks_layanan(riset, konten):
    t = " ".join(map(str, riset.get("layanan") or [])) + " " + json.dumps(konten.get("layanan") or [], ensure_ascii=False)
    return (t + " " + json.dumps(riset.get("keunggulan") or [], ensure_ascii=False)).lower()


def tebak_fokus(riset, konten):
    t = _teks_layanan(riset, konten)
    f = []
    if re.search(r"behel|ortodon|orthodon|braces|aligner", t):
        f.append("behel")
    if re.search(r"\banak\b|pedodon|kids|pediatri", t):
        f.append("anak")
    if re.search(r"implan|implant", t):
        f.append("implan")
    if re.search(r"veneer|bleaching|whitening|estetik|aesthetic|smile makeover", t):
        f.append("estetik")
    if re.search(r"spesialis|sp\.\s?(ort|kga|bm|pros|perio|kg)", t):
        f.append("spesialis")
    if len(riset.get("cabang") or []) > 1:
        f.append("multi-cabang")
    return f or ["umum"]


def tebak_gaya(nama, fokus):
    if "anak" in fokus:
        return "ramah"
    if "estetik" in fokus:
        return "elegan"
    if "spesialis" in fokus or "implan" in fokus:
        return "klinis"
    urut = ["klinis", "ramah", "berani", "elegan"]
    return urut[int(hashlib.md5(nama.encode()).hexdigest(), 16) % 4]


def muat(d, riset, konten):
    d = pathlib.Path(d)
    DS = {}
    f = d / "desain.json"
    if f.exists():
        try:
            DS = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            DS = {}
    if not DS and isinstance(konten.get("desain"), dict):
        DS = dict(konten["desain"])
    nama = str((riset.get("nama") or {}).get("v") if isinstance(riset.get("nama"), dict) else riset.get("nama") or d.name)
    fk = [x for x in (DS.get("fokus") or []) if x in FOKUS] or tebak_fokus(riset, konten)
    if len(riset.get("cabang") or []) > 1 and "multi-cabang" not in fk:
        fk.append("multi-cabang")
    DS["fokus"] = fk
    if DS.get("gaya") not in GAYA:
        DS["gaya"] = tebak_gaya(nama, fk)
    DS["_dir"] = str(d)
    return DS


# ---------------- unduh gambar ----------------
def _pil():
    try:
        import PIL  # noqa
        return True
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], capture_output=True)
        try:
            import PIL  # noqa
            return True
        except ImportError:
            return False


def _unduh(url, maks=8_000_000):
    if not url or not re.match(r"^(https?|file)://", str(url)):
        return None
    try:
        req = urllib.request.Request(str(url), headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read(maks + 1)
        return data if 200 < len(data) <= maks else None
    except Exception as e:
        print(f"  desain: gagal unduh {str(url)[:80]}: {e}")
        return None


def gambar(url, jenis):
    """-> data URI kecil (logo maks 320px PNG, foto maks 1200px JPEG) atau None"""
    data = _unduh(url)
    if not data:
        return None
    if data[:5].lower().startswith(b"<svg") or b"<svg" in data[:300].lower():
        if jenis == "logo" and len(data) < 200_000:
            return "data:image/svg+xml;base64," + base64.b64encode(data).decode()
        return None
    if not _pil():
        return ("data:image/jpeg;base64," + base64.b64encode(data).decode()) if len(data) < 300_000 else None
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    if im.width < (80 if jenis == "logo" else 400):
        return None
    buf = io.BytesIO()
    if jenis == "logo":
        im = im.convert("RGBA")
        im.thumbnail((320, 320))
        im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    im = im.convert("RGB")
    im.thumbnail((1200, 1200))
    im.save(buf, "JPEG", quality=78, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def warna_dari_logo(uri):
    """warna dominan yang 'berwarna' dari logo (abaikan putih/hitam/abu)"""
    if not uri or not uri.startswith("data:image/png") or not _pil():
        return None
    from PIL import Image
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
    im.thumbnail((64, 64))
    hit = {}
    for r, g, b, a in im.getdata():
        if a < 128 or max(r, g, b) - min(r, g, b) < 40 or max(r, g, b) < 40:
            continue
        k = (r // 24, g // 24, b // 24)
        hit[k] = hit.get(k, 0) + 1
    if not hit or sum(hit.values()) < 30:
        return None
    k = max(hit, key=hit.get)
    return _hex(tuple(x * 24 + 12 for x in k))


# ---------------- terapkan ----------------
def _ganti_root(out, var, nilai):
    return re.sub(r"(--%s:)#[0-9a-fA-F]{3,6}" % re.escape(var), r"\g<1>" + nilai, out, count=1)


def _potong_bagian(out):
    """bagian <section> tingkat atas antara hero dan footer -> (awal, [(kunci, html)], akhir).
    Dihitung dengan kedalaman tag section; isi di antara section ikut section sebelumnya."""
    a = out.find("<section id=\"semak\"")
    z = out.find("<footer>")
    if a < 0 or z < 0:
        return None
    tengah = out[a:z]
    blok, dalam, mulai = [], 0, None
    for m in re.finditer(r"<section\b[^>]*>|</section>", tengah):
        if m.group(0).startswith("<section"):
            if dalam == 0:
                if mulai is not None and blok and blok[-1][2] < m.start():
                    blok[-1] = (blok[-1][0], blok[-1][1], m.start())
                mulai = m.start()
                k = re.search(r'id="(\w+)"|class="(\w+)"', m.group(0))
                kunci = (k.group(1) or k.group(2)) if k else f"x{len(blok)}"
            dalam += 1
        else:
            dalam -= 1
            if dalam == 0:
                blok.append((kunci, mulai, m.end()))
            if dalam < 0:
                return None
    if dalam != 0 or not blok:
        return None
    hasil = []
    for i, (k, s_, e) in enumerate(blok):
        e2 = blok[i + 1][1] if i + 1 < len(blok) else len(tengah)
        hasil.append((k, tengah[s_:e2]))
    if "".join(h for _, h in hasil) != tengah[blok[0][1]:]:
        return None
    return out[:a], hasil, out[z:]


def _urutkan(out, DS, nama):
    p = _potong_bagian(out)
    if not p:
        return out
    awal, blok, akhir = p
    kunci = [k for k, _ in blok]
    peta = dict(blok)
    fk = DS["fokus"]
    urut = list(kunci)

    def pindah(k, sebelum):
        if k in urut and sebelum in urut and k != sebelum:
            urut.remove(k)
            urut.insert(urut.index(sebelum), k)

    h = int(hashlib.md5((nama + "urut").encode()).hexdigest(), 16)
    if "multi-cabang" in fk:
        pindah("lokasi", "semak")
    if "behel" in fk and "ansuran" in urut:
        pindah("rawatan", "semak")
        pindah("ansuran", "semak")
    elif "estetik" in fk or "implan" in fk or h % 3 == 0:
        pindah("rawatan", "semak")
    if "spesialis" in fk or h % 2:
        pindah("docs", "journey")
    if h % 4 == 1:
        pindah("soalan", "lokasi")
    if urut == kunci:
        return out
    return awal + "".join(peta[k] for k in urut) + akhir


def css_gaya(g, DS, pal, ink):
    G = GAYA[g]
    c = [f'h1,h2,h3,h4,.mont{{font-family:"{G["head"]}",{G["body"]!r},sans-serif}}'.replace("'", '"'),
         f'body{{font-family:"{G["body"]}",system-ui,sans-serif}}',
         f'.sig{{font-family:"{G["sig"]}",Georgia,serif}}',
         '.brand img,.fbr img,.badge{object-fit:contain;background:#fff}',
         '.brand img{border-radius:12px}.fbr img{border-radius:14px}',
         '.stage .hfoto{position:absolute;inset:4% 2% 8% 6%;margin:0;border-radius:calc(28px*var(--rs));overflow:hidden;box-shadow:var(--sh2);z-index:3;background:var(--gold-l)}',
         '.stage .hfoto img{width:100%;height:100%;object-fit:cover}',
         '.stage .hfoto figcaption{position:absolute;left:14px;bottom:14px;right:14px;color:#fff;font-size:13px;font-weight:600;text-shadow:0 1px 8px rgba(0,0,0,.5)}',
         '.stage.has-foto canvas,.stage.has-foto .halo,.stage.has-foto .glow,.stage.has-foto .orbit,.stage.has-foto .fb{display:none!important}',
         '.stage.has-foto .badge{z-index:4}',
         '.rail+section{padding-top:clamp(76px,10vw,128px)!important}']
    if g == "klinis":
        c += ['h1,h2{font-weight:750;letter-spacing:-.025em}',
              '.kicker{letter-spacing:.14em}',
              '.card,.pf,.tdy{box-shadow:0 1px 2px rgba(15,30,50,.05),0 10px 28px -22px rgba(15,30,50,.25)}']
    elif g == "ramah":
        c += ['h1,h2,h3{font-weight:850;letter-spacing:-.01em}',
              '.sig{font-style:normal;font-weight:600;font-size:clamp(28px,3.2vw,42px)}',
              '.hero::before{content:"";position:absolute;width:520px;height:520px;right:-140px;top:-160px;border-radius:50%;background:var(--gold-l);z-index:0}',
              '.hero::after{content:"";position:absolute;width:220px;height:220px;left:-80px;bottom:-60px;border-radius:50%;background:var(--gold-l);opacity:.7;z-index:0}',
              '.hero .wrap{position:relative;z-index:1}',
              '.btn{border-radius:999px}']
    elif g == "berani":
        dua = (DS.get("warna") or {}).get("kedua") or pal[0]
        c += ['h1,h2{font-weight:700;letter-spacing:-.035em;text-transform:none}',
              f'.hero{{background:linear-gradient(140deg,{ink} 0%,{ink} 45%,{pal[0]} 140%);color:#fff}}',
              '.hero .sig{color:var(--gold-d)}.hero .sig::before{background:var(--gold-d)}',
              '.hero h1,.hero .lead{color:#fff}.hero .lead{opacity:.82}',
              '.hero .btn-dark{background:#fff;color:var(--ink)}',
              '.hero .btn-ghost{color:#fff;border-color:rgba(255,255,255,.35)}',
              '.hero .tdy{color:var(--ink)}',
              f'.rail{{background:{dua}}}']
    elif g == "elegan":
        c += ['h1,h2{font-weight:560;letter-spacing:-.02em}',
              '.sig{font-weight:400}']
    return "<style id=\"gaya-klinik\">\n" + "\n".join(c) + "\n</style>\n"


def terapkan(out, DS, logo_lama=None, nama=""):
    g = DS.get("gaya") if DS.get("gaya") in GAYA else "klinis"
    G = GAYA[g]
    d = pathlib.Path(DS.get("_dir", "."))

    # logo & foto asli (diunduh sekali, disimpan di folder klinik)
    cache = d / "aset.json"
    aset = {}
    if cache.exists():
        try:
            aset = json.loads(cache.read_text())
        except Exception:
            aset = {}
    for k in ("logo", "foto"):
        url = DS.get(k + "_url")
        if url and aset.get(k + "_url") != url:
            aset[k] = gambar(url, k)
            aset[k + "_url"] = url
    try:
        cache.write_text(json.dumps(aset))
    except Exception:
        pass
    logo, foto = aset.get("logo"), aset.get("foto")

    # warna: brand dari GPT; bila kosong coba dari logo
    pal = palet(DS)
    if not pal and logo:
        w = warna_dari_logo(logo)
        if w:
            DS.setdefault("warna", {})["utama"] = w
            pal = palet(DS)
            if pal:  # template sudah memakai palet cadangan -> tukar ke palet logo
                lama = re.search(r"--gold:(#[0-9a-f]{6});--gold-t:(#[0-9a-f]{6});--gold-d:(#[0-9a-f]{6});--gold-l:(#[0-9a-f]{6})", out, re.I)
                if lama:
                    for a, b in zip(lama.groups(), pal):
                        out = re.sub(re.escape(a), b, out, flags=re.I)
    m = re.search(r"--gold:(#[0-9a-fA-F]{6})", out)
    aksen = _rgb(m.group(1)) if m else (122, 92, 153)

    # tema dasar: hitam ikut warna brand, latar ikut gaya
    tinta = _mix(aksen, (13, 14, 16), 0.72 if g == "berani" else 0.86)
    while _kontras(tinta, (255, 255, 255)) < 12:
        tinta = _mix(tinta, (8, 9, 10), 0.25)
    ink = _hex(tinta)
    bg = _hex(_mix(_rgb(G["bg"]), aksen, G["campur"]))
    paper = _hex(_mix(_rgb(G["paper"]), aksen, G["campur"] / 2))
    for var, val in (("ink", ink), ("ink2", _hex(_mix(tinta, (255, 255, 255), .06))), ("ink3", _hex(_mix(tinta, (255, 255, 255), .16))),
                     ("bg", bg), ("paper", paper), ("line", _hex(_mix(_rgb(G["bg"]), tinta, .09))), ("line2", _hex(_mix(_rgb(G["bg"]), tinta, .15)))):
        out = _ganti_root(out, var, val)
    r, g_, b = tinta
    out = out.replace("#111214", ink).replace("0x111214", "0x" + ink[1:]).replace("rgba(17,18,20", f"rgba({r:.0f},{g_:.0f},{b:.0f}")

    # radius
    s = G["r"]
    out = re.sub(r"border-radius:(\d+)px", lambda m_: f"border-radius:{max(4, round(int(m_.group(1)) * s)) if 6 <= int(m_.group(1)) <= 40 else int(m_.group(1))}px", out)
    out = out.replace(":root{--ink", f":root{{--rs:{s};--ink", 1)

    # font
    out = re.sub(r"https://fonts\.googleapis\.com/css2\?[^\"']+", "https://fonts.googleapis.com/css2?" + G["fonts"] + "&display=swap", out, count=1)
    for lama, baru in (("Bricolage Grotesque", G["head"]), ("Instrument Serif", G["sig"])):  # pelajaran #45: ganti nama font di seluruh CSS, bukan hanya ditimpa
        out = out.replace('"%s"' % lama, '"%s"' % baru).replace("'%s'" % lama, "'%s'" % baru)
    out = re.sub(r"(?<![\w\"'+])Figtree(?![\w\"'])", '"%s"' % G["body"], out)

    # logo asli
    if logo and logo_lama:
        out = out.replace(logo_lama, logo)

    # foto klinik di hero (panel lokasi tetap peta Google Maps)
    if foto:
        alt = nama.replace('"', "")
        out = out.replace('<div class="stage rv" id="stage" aria-hidden="true">',
                          f'<div class="stage rv has-foto" id="stage" aria-hidden="true"><figure class="hfoto"><img src="{foto}" alt=""><figcaption>{alt}</figcaption></figure>', 1)

    # urutan bagian sesuai fokus
    out = _urutkan(out, DS, nama)

    # css gaya
    gaya_css = css_gaya(g, DS, pal or (m.group(1) if m else "#7a5c99",), ink)
    i_ = out.rfind("</body>")  # setelah CSS template supaya tidak tertimpa
    out = out[:i_] + gaya_css + out[i_:] if i_ > 0 else out + gaya_css
    out = out.replace("<body", f'<body data-gaya="{g}"', 1)
    print(f"  desain: gaya={g} fokus={','.join(DS['fokus'])} logo={'asli' if logo else 'inisial'} foto={'ada' if foto else '-'} warna={(DS.get('warna') or {}).get('utama', 'cadangan')}")
    return out


def masuk(folder, root=None):
    """pelajaran #46: hasil GPT-A DESAIN-hasil-*.json(.md) -> batches/Bxx/Wyy/desain.json, lalu klinik dirakit ulang."""
    root = pathlib.Path(root or pathlib.Path(__file__).resolve().parents[1])
    kunci = ("logo_url", "foto_url", "warna", "gaya", "fokus", "alasan")
    n_baru = n_ulang = 0
    for f in sorted(pathlib.Path(folder).glob("DESAIN-hasil-*")):
        teks = f.read_text(encoding="utf-8", errors="ignore")
        teks = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", teks.strip())
        teks = teks.replace("\\[", "[").replace("\\]", "]").replace("\\_", "_").replace("\\#", "#").replace("\\&", "&")
        a, b = teks.find("["), teks.rfind("]")
        try:
            data = json.loads(teks[a:b + 1])
        except Exception as e:
            print(f"✗ {f.name}: JSON rusak ({e})")
            continue
        for it in data:
            if not isinstance(it, dict) or not it.get("id") or not it.get("batch"):
                continue
            d = root / "batches" / str(it["batch"]) / str(it["id"])
            if not d.exists():
                print(f"  {it['id']}: folder {d} tidak ada, dilewati")
                continue
            ds = {k: it[k] for k in kunci if it.get(k) not in (None, [], {}, "")}
            if isinstance(ds.get("warna"), dict):
                ds["warna"] = {k: v for k, v in ds["warna"].items() if v}
            ds["nama"] = it.get("nama")
            fj = d / "desain.json"
            lama = fj.read_text(encoding="utf-8") if fj.exists() else ""
            baru = json.dumps(ds, ensure_ascii=False, indent=1)
            if lama == baru:
                continue
            fj.write_text(baru, encoding="utf-8")
            n_baru += 1
            stf = d / "status.json"
            try:
                st = json.loads(stf.read_text(encoding="utf-8"))
            except Exception:
                st = {}
            if (d / "site" / "index.html").exists() and (d / "riset.json").exists() and (d / "konten.json").exists():
                (d / "site" / "index.html").unlink()
                st.update(status="Siap rakit", oleh="desain-gpt", catatan="rakit ulang dengan desain asli klinik (pelajaran #43)")
                stf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
                n_ulang += 1
    print(f"desain masuk: {n_baru} desain.json baru/berubah, {n_ulang} klinik dirakit ulang")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "masuk":
    masuk(sys.argv[2])
    sys.exit(0)

if __name__ == "__main__":
    src, dj, dst = sys.argv[1:4]
    html = pathlib.Path(src).read_text(encoding="utf-8")
    DS = json.loads(pathlib.Path(dj).read_text())
    DS.setdefault("fokus", ["umum"])
    DS["_dir"] = str(pathlib.Path(dst).parent)
    pal = palet(DS)
    if pal:
        lama = re.search(r"--gold:(#[0-9a-f]{6});--gold-t:(#[0-9a-f]{6});--gold-d:(#[0-9a-f]{6});--gold-l:(#[0-9a-f]{6})", html, re.I)
        for a, b in zip(lama.groups(), pal):
            html = re.sub(re.escape(a), b, html, flags=re.I)
    lg = re.search(r'class="brand"><img src="([^"]+)"', html).group(1)
    pathlib.Path(dst).write_text(terapkan(html, DS, lg, DS.get("nama", "Klinik")), encoding="utf-8")
