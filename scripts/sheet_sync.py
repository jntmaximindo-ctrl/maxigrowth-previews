#!/usr/bin/env python3
"""Sinkron status repo → Sheet Waiting List.

Membaca batches/<Batch>/<ID>/status.json lalu menulis kolom Status (dan Batch bila kosong)
di baris Sheet dengan ID yang sama. Status yang sudah diputuskan manusia tidak ditimpa.
Env: GOOGLE_SA_JSON, SHEET_ID.
"""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sheet import svc, read  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Status yang ditetapkan pemilik / tahap setelah review — jangan ditimpa robot.
PROTECT = {"Disetujui", "Selesai", "Skip", "Dikirim", "Deal", "Ditolak", "Live"}


def col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def main():
    s = svc()
    tab, hdr, _ = read(s)
    sid = os.environ["SHEET_ID"]
    rows = s.values().get(spreadsheetId=sid, range=f"'{tab}'!A1:ZZ").execute().get("values", [])
    ci = {h: i for i, h in enumerate(rows[0])} if rows else {}
    if not {"ID", "Status"} <= ci.keys():
        print("header ID/Status tidak ditemukan"); return 1
    get = lambda r, h: (r[ci[h]] if ci.get(h) is not None and ci[h] < len(r) else "").strip()
    by_id = {get(r, "ID"): n for n, r in enumerate(rows[1:], start=2) if get(r, "ID")}
    data, log = [], []
    for st in sorted((ROOT / "batches").glob("B*/*/status.json")):
        try:
            status = json.loads(st.read_text(encoding="utf-8")).get("status", "").strip()
        except Exception:
            continue
        batch, kid = st.parent.parent.name, st.parent.name
        n = by_id.get(kid)
        if not status or not n:
            continue
        r = rows[n - 1]
        cur = get(r, "Status")
        sb = get(r, "Batch") if "Batch" in ci else ""
        # baris yang sudah dikembalikan ke antrean (Batch dikosongkan) atau pindah ke batch lain: jangan disentuh
        if (not sb and cur == "Menunggu") or (sb and sb != batch):
            continue
        if cur in PROTECT or cur == status:
            pass
        else:
            data.append({"range": f"'{tab}'!{col(ci['Status'])}{n}", "values": [[status]]})
            log.append(f"{kid}: {cur or '-'} → {status}")
        if "Batch" in ci and not get(r, "Batch"):
            data.append({"range": f"'{tab}'!{col(ci['Batch'])}{n}", "values": [[batch]]})
    if data:
        s.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED", "data": data}).execute()
    print("\n".join(log) or "Sheet sudah sinkron")
    return 0


def links():
    """Isi kolom 'Link preview' yang masih kosong dari data/preview-links.json (butuh env PREVIEW_BASE)."""
    base = os.environ.get("PREVIEW_BASE", "").rstrip("/")
    f = ROOT / "data" / "preview-links.json"
    if not base or not f.exists():
        print("PREVIEW_BASE / preview-links.json belum ada"); return 0
    m = json.loads(f.read_text(encoding="utf-8"))
    s = svc()
    tab, hdr, _ = read(s)
    sid = os.environ["SHEET_ID"]
    rows = s.values().get(spreadsheetId=sid, range=f"'{tab}'!A1:ZZ").execute().get("values", [])
    ci = {h: i for i, h in enumerate(rows[0])}
    if "Link preview" not in ci:
        print("kolom Link preview tidak ada"); return 1
    get = lambda r, h: (r[ci[h]] if ci[h] < len(r) else "").strip()
    data, log = [], []
    for n, r in enumerate(rows[1:], start=2):
        kid = get(r, "ID")
        if kid in m and not get(r, "Link preview"):
            url = f"{base}/{m[kid]}/"
            data.append({"range": f"'{tab}'!{col(ci['Link preview'])}{n}", "values": [[url]]})
            log.append(f"{kid}: {url}")
    if data:
        s.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": data}).execute()
    print("\n".join(log) or "semua link sudah terisi")
    return 0


if __name__ == "__main__":
    sys.exit(links() if sys.argv[1:] == ["links"] else main())
