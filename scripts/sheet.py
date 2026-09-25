#!/usr/bin/env python3
"""Jembatan Google Sheet ↔ repo (dipakai GitHub Actions dengan service account).

python scripts/sheet.py intake [--size 10]   → ambil batch berikutnya dari Sheet, tulis batches/Bxx/<ID>/job.json,
                                               cetak daftar ID (untuk dibuatkan issue), tandai Sheet: Batch + Status.
python scripts/sheet.py status               → gabungkan preview.json (hasil rakit) ke status.json, cerminkan Skip dari
                                               Sheet, lalu tulis Status + Link preview ke Sheet.

Env: GOOGLE_SA_JSON (isi JSON service account), SHEET_ID. Sheet harus dibagikan (Editor) ke email service account.
Kolom yang dibaca/ditulis mengikuti header baris 1 (urutan kolom boleh berubah).
"""
import json, os, pathlib, re, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
PRIO = {"tinggi": 0, "normal": 1, "": 1, "rendah": 2}


def svc():
    info = json.loads(os.environ["GOOGLE_SA_JSON"])
    cred = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=cred, cache_discovery=False).spreadsheets()


def read(s):
    meta = s.get(spreadsheetId=os.environ["SHEET_ID"]).execute()
    tab = meta["sheets"][0]["properties"]["title"]
    rows = s.values().get(spreadsheetId=os.environ["SHEET_ID"], range=f"'{tab}'").execute().get("values", [])
    hdr = rows[0]
    recs = [dict(zip(hdr, r + [""] * (len(hdr) - len(r))), _row=i + 2) for i, r in enumerate(rows[1:])]
    return tab, hdr, recs


def col(hdr, name):
    n, s = hdr.index(name) + 1, ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def write(s, tab, hdr, updates):
    data = [{"range": f"'{tab}'!{col(hdr, k)}{row}", "values": [[v]]} for row, k, v in updates]
    if data:
        s.values().batchUpdate(spreadsheetId=os.environ["SHEET_ID"],
                               body={"valueInputOption": "USER_ENTERED", "data": data}).execute()


def next_batch_name():
    existing = [int(m.group(1)) for p in (ROOT / "batches").glob("B*") if (m := re.match(r"B(\d+)", p.name))]
    return f"B{(max(existing) + 1) if existing else 1:02d}"


def slugify(name):
    """Slug pendek: pakai singkatan dalam kurung (mis. RSKGM, BDC) bila ada, jika tidak 2 kata pertama yang bermakna."""
    m = re.search(r"[\(\[]([A-Z]{2,6})[\)\]]", name)
    if m:
        return m.group(1).lower()
    base = re.sub(r"\(.*?\)|\[.*?\]", " ", name).lower()
    generik = {"klinik", "clinic", "praktek", "praktik", "dokter", "gigi", "pt", "utama", "dental", "care", "the", "dan", "&"}
    kata = [w for w in re.split(r"[^a-z0-9]+", base) if w and w not in generik]
    if not kata:
        kata = [w for w in re.split(r"[^a-z0-9]+", base) if w]
    kata = list(dict.fromkeys(kata))
    return "-".join(kata[:2])[:28] or "klinik"


def intake(size=10):
    s = svc()
    tab, hdr, recs = read(s)
    todo = [r for r in recs if r.get("Status", "").strip().lower() == "menunggu" and r.get("ID")]
    todo.sort(key=lambda r: (PRIO.get(r.get("Prioritas", "").strip().lower(), 1), int(r.get("No") or 9999)))
    todo = todo[:size]
    if not todo:
        print("KOSONG")
        return
    batch = next_batch_name()
    ups = []
    for r in todo:
        d = ROOT / "batches" / batch / r["ID"]
        d.mkdir(parents=True, exist_ok=True)
        job = {"id": r["ID"], "batch": batch, "nama": r["Nama klinik"], "url": r["URL / IG"], "kota": r.get("Kota", ""),
               "prioritas": r.get("Prioritas", ""), "tingkat": r.get("Tingkat") or "Penuh", "catatan": r.get("Catatan", ""),
               "maps": {"rating": r.get("Rating"), "ulasan": r.get("Ulasan Google")}, "slug": slugify(r["Nama klinik"])}
        (d / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2))
        (d / "status.json").write_text(json.dumps({"status": "Riset"}, ensure_ascii=False))
        ups += [(r["_row"], "Batch", batch), (r["_row"], "Status", "Riset")]
        print(f"{batch}/{r['ID']}\t{r['Nama klinik']}")
    write(s, tab, hdr, ups)


SKIP = ("skip", "batal", "dilewati")
AKHIR = ("Disetujui", "Terkirim", "Skip")  # status yang tidak boleh ditimpa preview.json


def merge_preview(f: pathlib.Path, st: dict) -> dict:
    """preview.json ditulis perakit (Claude) di Drive lalu ditarik sync-drive → gabungkan ke status.json."""
    p = f.parent / "preview.json"
    if not p.exists():
        return st
    try:
        pv = json.loads(p.read_text())
    except Exception:
        return st
    if st.get("status") in AKHIR:
        return st
    new = dict(st, status=pv.get("status") or "Siap review")
    for k in ("preview", "slug", "built", "catatan"):
        if pv.get(k):
            new[k] = pv[k]
    return new


def status():
    s = svc()
    tab, hdr, recs = read(s)
    by_id = {r["ID"]: r for r in recs}
    ups = []
    for f in (ROOT / "batches").glob("B*/*/status.json"):
        st = json.loads(f.read_text())
        r = by_id.get(f.parent.name)
        if not r:
            continue
        if r.get("Status", "").strip().lower() in SKIP:
            # keputusan pemilik di Sheet tidak ditimpa sistem; dicerminkan ke status.json agar gate intake tahu
            if st.get("status") != "Skip":
                f.write_text(json.dumps(dict(st, status="Skip"), ensure_ascii=False))
            continue
        merged = merge_preview(f, st)
        if merged != st:
            f.write_text(json.dumps(merged, ensure_ascii=False))
            st = merged
        if st.get("status") and st["status"] != r.get("Status"):
            ups.append((r["_row"], "Status", st["status"]))
        if st.get("preview") and st["preview"] != r.get("Link preview"):
            ups.append((r["_row"], "Link preview", st["preview"]))
    write(s, tab, hdr, ups)
    print("diperbarui:", len(ups))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "intake":
        intake(int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 10)
    elif cmd == "status":
        status()
