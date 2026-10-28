#!/usr/bin/env python3
"""Menyusun data JSON dashboard ICU dari status klinik di repo (tanpa AI, tanpa jaringan)."""
import glob
import json
import os
import sys
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "icu-data.json"
HIST = sys.argv[2] if len(sys.argv) > 2 else "icu-riwayat.json"
WIB = dt.timezone(dt.timedelta(hours=7))
NOW = dt.datetime.now(WIB)
URUT = ["riset", "cek_fakta", "rakit", "qa", "deploy", "review", "siap_reachout"]


def tahap_dari(status):
    s = (status or "").lower()
    if "reachout" in s or "siap kirim" in s:
        return "siap_reachout"
    if "review" in s:
        return "review"
    if "deploy" in s or "tayang" in s:
        return "deploy"
    if "qa" in s:
        return "qa"
    if "rakit" in s:
        return "rakit"
    if "cek fakta" in s:
        return "cek_fakta"
    if "riset" in s:
        return "riset"
    return None


def baca(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


tahap = {k: 0 for k in URUT}
OUTREACH = baca(os.path.join(ROOT, "data", "outreach.json"), {})
REVIEW = baca(os.path.join(ROOT, "data", "review.json"), {})
lain = 0
total = 0
for p in glob.glob(os.path.join(ROOT, "batches", "*", "*", "status.json")):
    st = baca(p, {})
    total += 1
    t = tahap_dari(st.get("status"))
    if (st.get("status") or "").lower() == "siap review":
        kid = os.path.basename(os.path.dirname(p))
        hasil = str(REVIEW.get(kid, "")).lower()
        if kid in OUTREACH or hasil == "gagal":
            t = None
        elif hasil == "lolos":
            t = "siap_reachout"
        else:
            t = "review"
    if t:
        tahap[t] += 1
    else:
        lain += 1

# Jumlah klinik yang sudah melewati tiap tahap (kumulatif) untuk menghitung kecepatan
lulus = {}
for i, k in enumerate(URUT):
    lulus[k] = sum(tahap[x] for x in URUT[i + 1:])

hist = baca(HIST, [])
hist = [h for h in hist if h.get("t")]
snap = {"t": NOW.isoformat(), "lulus": lulus, "siap": tahap["siap_reachout"]}
hist.append(snap)
batas = NOW - dt.timedelta(hours=48)
hist = [h for h in hist if dt.datetime.fromisoformat(h["t"]) >= batas]

# --- Riwayat harian (disimpan selamanya, 1 baris per tanggal WIB): kemarin & hari-hari sebelumnya ---
HARI_FILE = os.path.join(os.path.dirname(os.path.abspath(HIST)), "icu-harian.json")
harian = baca(HARI_FILE, {})
if not isinstance(harian, dict):
    harian = {}
for h in sorted(hist, key=lambda x: x["t"]):  # tanam dari riwayat 48 jam (awal & akhir tiap tanggal)
    tg = h["t"][:10]
    harian.setdefault(tg, {"awal": h["lulus"], "akhir": h["lulus"], "siap": h.get("siap", 0)})
    if h["t"] >= harian[tg].get("t_akhir", ""):
        harian[tg].update(akhir=h["lulus"], siap=h.get("siap", 0), t_akhir=h["t"])
daftar_harian, prev = [], None
for tg in sorted(harian):
    x = harian[tg]
    dasar = prev if prev is not None else x["awal"]
    daftar_harian.append({"tanggal": tg, "lulus_akhir": x["akhir"], "siap_reachout_akhir": x.get("siap", 0),
                          "tambahan_hari_itu": {k: max(x["akhir"].get(k, 0) - dasar.get(k, 0), 0) for k in x["akhir"]}})
    prev = x["akhir"]
hari_ini_s, kemarin_s = NOW.strftime("%Y-%m-%d"), (NOW - dt.timedelta(days=1)).strftime("%Y-%m-%d")
kemarin = next((d for d in daftar_harian if d["tanggal"] == kemarin_s), None)

kecepatan = {"cari": None}
lama = None
for h in hist:
    umur = (NOW - dt.datetime.fromisoformat(h["t"])).total_seconds() / 60
    if umur >= 50:
        lama = h  # snapshot terbaru yang umurnya minimal 50 menit
if lama:
    menit = max(1.0, (NOW - dt.datetime.fromisoformat(lama["t"])).total_seconds() / 60)
    for k in URUT[:-1]:
        kecepatan[k] = max(0, round((lulus[k] - lama["lulus"].get(k, 0)) * 60 / menit))
else:
    for k in URUT[:-1]:
        kecepatan[k] = None

awal_hari = None
for h in hist:
    if dt.datetime.fromisoformat(h["t"]).astimezone(WIB).date() == NOW.date():
        awal_hari = h
        break
# Dasar = angka siap akhir hari sebelumnya (bukan snapshot pertama hari ini, yang bisa baru terekam pagi hari
# setelah laptop/robot mati semalaman -> hasil malam hari ikut hilang; pelajaran 38)
siap_kemarin = harian.get(kemarin_s, {}).get("siap") if kemarin_s in harian else None
dasar_siap = siap_kemarin if siap_kemarin is not None else (awal_hari["siap"] if awal_hari else tahap["siap_reachout"])
siap_hari_ini = max(tahap["siap_reachout"] - dasar_siap, 0)

target = baca(os.path.join(ROOT, "data", "icu-target.json"), {})
pekerja = baca(os.path.join(ROOT, "data", "icu-pekerja.json"), [])

peringatan = []
nilai = [tahap[k] for k in URUT[:-1]]
rata = sum(nilai) / len(nilai) if nilai else 0
for k in URUT[:-1]:
    if k != "review" and tahap[k] >= 20 and rata and tahap[k] > 1.5 * rata:
        peringatan.append({
            "tingkat": "kritis",
            "judul": "Antrean " + k.replace("_", " ") + " menumpuk",
            "detail": str(tahap[k]) + " klinik menunggu di tahap " + k.replace("_", " ") + ".",
            "teks_perbaikan": "Periksa pekerja tahap " + k.replace("_", " ") + " dan dorong sampai antrean turun.",
        })
if not pekerja:
    peringatan.append({
        "tingkat": "info",
        "judul": "Status pekerja belum tersambung",
        "detail": "Data pekerja (mode, kuota, hasil terakhir) belum dikirim ke pabrik.",
        "teks_perbaikan": "Minta Claude 1 mengisi data/icu-pekerja.json.",
    })

akhir = NOW.replace(hour=23, minute=59, second=0, microsecond=0)
data = {
    "diperbarui": NOW.isoformat(timespec="seconds"),
    "sumber": "repo-pabrik",
    "target_harian": target.get("hari_ini", 600),
    "target": target,
    "akhir_hari": akhir.isoformat(timespec="seconds"),
    "total_klinik_di_batch": total,
    "klinik_status_lain": lain,
    "siap_reachout_hari_ini": siap_hari_ini,
    "tahap": dict({"cari": None}, **tahap),
    "kecepatan_per_jam": kecepatan,
    "pekerja": pekerja,
    "peringatan": peringatan,
    "kemarin": kemarin,
    "harian": daftar_harian[-14:],
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
with open(HIST, "w", encoding="utf-8") as f:
    json.dump(hist, f, ensure_ascii=False)
with open(HARI_FILE, "w", encoding="utf-8") as f:
    json.dump(harian, f, ensure_ascii=False)
print("ICU data:", json.dumps(tahap), "lain=", lain, "total=", total)
