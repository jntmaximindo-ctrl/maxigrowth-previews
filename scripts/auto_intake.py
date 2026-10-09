#!/usr/bin/env python3
"""Intake otomatis: cetak jumlah klinik yang perlu diambil dari antrean 'Menunggu' sekarang (0 = tidak perlu).

Aturan: hanya bila klinik yang sedang diriset < AKTIF_MAKS, maksimal PER_BATCH sekali ambil,
dan maksimal HARIAN klinik baru per hari (WIB). Pemakaian harian dicatat di data/intake-log.json.
Env: GOOGLE_SA_JSON, SHEET_ID.
"""
import datetime, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sheet import svc, read  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "intake-log.json"
HARIAN, PER_BATCH, AKTIF_MAKS = int(os.environ.get("INTAKE_HARIAN", 20)), 10, int(os.environ.get("INTAKE_AKTIF_MAKS", 12))
AKTIF = {"Riset", "Riset di GPT", "Menunggu cek fakta", "Riset di Codex", "Cek fakta di Codex"}


def main():
    s = svc()
    tab, hdr, recs = read(s)
    st = [str(r.get("Status", "")).strip() for r in recs]
    aktif, menunggu = sum(x in AKTIF for x in st), sum(x == "Menunggu" for x in st)
    hari = (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    dipakai = int(log.get(hari, 0))
    n = 0 if aktif >= AKTIF_MAKS else min(PER_BATCH, menunggu, HARIAN - dipakai)
    n = max(n, 0)
    print(f"aktif={aktif} menunggu={menunggu} hari_ini={dipakai}/{HARIAN} → ambil {n}", file=sys.stderr)
    if n:
        log = {k: v for k, v in log.items() if k >= hari[:8]}  # simpan bulan ini saja
        log[hari] = dipakai + n
        LOG.parent.mkdir(exist_ok=True)
        LOG.write_text(json.dumps(log, indent=1, sort_keys=True))
    print(n)


if __name__ == "__main__":
    main()
