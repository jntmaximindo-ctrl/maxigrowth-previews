#!/usr/bin/env python3
"""Pencari Klinik: jembatan hasil Codex (sourcing/<kota>/hasil.json) → Sheet Waiting List.

  known                → tulis data/known.txt (nama & domain yang sudah ada di Sheet) untuk dilewati Codex
  apply                → tambahkan kandidat baru dari hasil.json yang belum diterapkan ke Sheet
  next                 → cetak "<slug>\t<kota>\t<negara>" kota berikutnya bila antrean Menunggu < BUFFER, selain itu kosong
Env: GOOGLE_SA_JSON, SHEET_ID.
Aturan (dari pemilik): rating ≥ 4.5 & ulasan ≥ 3 → layak.
  tanpa website → Menunggu, Prioritas Tinggi; website jadul (skor ≥ 40) → Menunggu (Tinggi bila ≥ 70);
  website sudah bagus (skor < 40) → "Review manual" (pemilik yang memutuskan).
"""
import json, os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sheet import svc, read  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "sourcing-state.json"
BUFFER = int(os.environ.get("SOURCING_BUFFER", "40"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def norm_url(u):
    u = (u or "").lower().strip()
    u = re.sub(r"^https?://(www\.)?", "", u).split("?")[0].rstrip("/")
    return u


def norm_nama(n):
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"habis": [], "applied": [], "diminta": []}


def save(st):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2))


def kota_list():
    out = []
    for line in (ROOT / "data" / "kota.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, n = line.partition("|")
        out.append((k.strip(), (n.strip() or "Indonesia")))
    return out


def known():
    _, _, recs = read(svc())
    lines = set()
    for r in recs:
        if r.get("Nama klinik"):
            lines.add(r["Nama klinik"].strip())
        if r.get("URL / IG"):
            lines.add(norm_url(r["URL / IG"]))
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "known.txt").write_text("\n".join(sorted(x for x in lines if x)) + "\n", encoding="utf-8")
    print("known:", len(lines))
    return 0


def next_city():
    _, _, recs = read(svc())
    menunggu = sum(1 for r in recs if r.get("Status", "").strip().lower() == "menunggu")
    if menunggu >= BUFFER:
        print(f"antrean cukup ({menunggu})", file=sys.stderr)
        return 0
    st = state()
    for k, n in kota_list():
        s = slug(k)
        if s not in st["habis"] and s not in st.get("diminta", []):
            print(f"{s}\t{k}\t{n}")
            return 0
    print("semua kota habis", file=sys.stderr)
    return 0


def apply():
    s = svc()
    tab, hdr, recs = read(s)
    st = state()
    seen_n = {norm_nama(r.get("Nama klinik")) for r in recs}
    seen_u = {norm_url(r.get("URL / IG")) for r in recs if r.get("URL / IG")}
    ids = [int(m.group(1)) for r in recs if (m := re.match(r"W(\d+)$", r.get("ID", "")))]
    nos = [int(r["No"]) for r in recs if str(r.get("No", "")).isdigit()]
    next_id, next_no = (max(ids) + 1 if ids else 1), (max(nos) + 1 if nos else 1)
    rows, log = [], []
    for f in sorted((ROOT / "sourcing").glob("*/hasil.json")):
        import hashlib
        key = str(f.relative_to(ROOT)) + "#" + hashlib.sha1(f.read_bytes()).hexdigest()[:10]
        if key in st["applied"]:
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        kota, negara = data.get("kota", ""), data.get("negara", "Indonesia")
        baru = 0
        for k in data.get("klinik", []):
            try:
                rating, ulasan = float(k.get("rating") or 0), int(k.get("ulasan") or 0)
            except Exception:
                continue
            if rating < 4.5 or ulasan < 3:
                continue
            n, u = norm_nama(k.get("nama")), norm_url(k.get("url"))
            if not n or n in seen_n or (u and u in seen_u):
                continue
            seen_n.add(n); seen_u.add(u)
            skor = int(k.get("skor_jadul") or (100 if not k.get("punya_website") else 0))
            if not k.get("punya_website"):
                status, prio, cat = "Menunggu", "Tinggi", "Tanpa website"
            elif skor >= 40:
                status, prio, cat = "Menunggu", ("Tinggi" if skor >= 70 else "Normal"), f"Website jadul (skor {skor})"
            else:
                status, prio, cat = "Review manual", "Normal", f"Website sudah bagus (skor {skor}) — putuskan: Menunggu/Skip"
            val = {"No": str(next_no), "ID": f"W{next_id}", "Nama klinik": k.get("nama", ""), "URL / IG": k.get("url") or k.get("maps_url") or "",
                   "Kota": kota, "Prioritas": prio, "Tingkat": "Penuh", "Rating": str(rating), "Ulasan Google": str(ulasan),
                   "Status": status, "Catatan": f"[Pencari {negara}] {cat}. " + "; ".join(k.get("masalah") or [])[:300]}
            rows.append([val.get(h, "") for h in hdr])
            next_id += 1; next_no += 1; baru += 1
        st["applied"].append(key)
        if data.get("habis") or (baru == 0 and not data.get("area")):  # hasil per area kosong ≠ kota habis
            s_k = slug(kota)
            if s_k not in st["habis"]:
                st["habis"].append(s_k)
        st["diminta"] = [x for x in st.get("diminta", []) if x != slug(kota)]
        log.append(f"{kota}: {baru} klinik baru")
    if rows:
        s.values().append(spreadsheetId=os.environ["SHEET_ID"], range=f"'{tab}'!A1", valueInputOption="USER_ENTERED",
                          insertDataOption="INSERT_ROWS", body={"values": rows}).execute()
    save(st)
    print("\n".join(log) or "tidak ada hasil baru")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "mark-diminta":
        st = state(); st.setdefault("diminta", []).append(sys.argv[2]); save(st); sys.exit(0)
    sys.exit({"known": known, "apply": apply, "next": next_city}[cmd]())
