#!/usr/bin/env python3
"""Failover GPT scheduled task → Codex pool.

Klinik yang tertahan di jalur GPT (bus) melebihi batas jam dialihkan ke Codex:
  "Riset di GPT"       → tugas riset Codex   (status jadi "Riset di Codex")
  "Menunggu cek fakta" → tugas cekfakta Codex (status jadi "Cek fakta di Codex")
Cetak baris "<B/W>\t<tugas>" untuk dikirim orkestrator ke codex-dispatch. Maks MAKS per putaran.
Umur dihitung dari commit terakhir status.json (git log).
"""
import datetime, json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAKS = int(os.environ.get("FAILOVER_MAKS", 3))
# status: (tugas Codex, status baru, batas jam). GPT-A ±2 klinik/jam, GPT-B ±3 klinik/jam.
PETA = {"Riset di GPT": ("riset", "Riset di Codex", 8), "Menunggu cek fakta": ("cekfakta", "Cek fakta di Codex", 6),
        # sudah dialihkan tapi belum selesai (dispatch tertunda / Codex gagal) → kirim ulang, maks 2x
        "Riset di Codex": ("riset", "Riset di Codex", 6), "Cek fakta di Codex": ("cekfakta", "Cek fakta di Codex", 6)}
MAKS_ULANG = 2


def umur_jam(p):
    out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", str(p)], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if not out:
        return 0
    return (datetime.datetime.utcnow().timestamp() - int(out)) / 3600


TAHAP_HASIL = {  # status macet → (tahap, file wajib) : hasil sudah ada di main tapi status tidak maju (mis. crash setelah merge)
    "Riset di GPT": ("riset", ("riset.json", "konten.json")), "Riset di Codex": ("riset", ("riset.json", "konten.json")),
    "Menunggu cek fakta": ("cekfakta", ("cekfakta.json",)), "Cek fakta di Codex": ("cekfakta", ("cekfakta.json",)),
}


def pulihkan():
    """Hasil sudah ada & lulus cek, tapi status tertinggal → majukan status (tanpa AI, tanpa kirim ulang)."""
    for st in sorted((ROOT / "batches").glob("B*/*/status.json")):
        try:
            cur = json.loads(st.read_text(encoding="utf-8")).get("status", "")
        except Exception:
            continue
        if cur not in TAHAP_HASIL:
            continue
        tahap, wajib = TAHAP_HASIL[cur]
        if not all((st.parent / w).exists() for w in wajib):
            continue
        rel = str(st.parent.relative_to(ROOT))
        cek = subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "check", rel, tahap], capture_output=True, text=True, cwd=ROOT)
        if cek.returncode == 0:
            subprocess.run([sys.executable, str(ROOT / "scripts/codex_check.py"), "finish", rel, tahap], capture_output=True, text=True, cwd=ROOT)
            print(f"pulih {rel}: {cur} → hasil {tahap} sudah ada & lulus cek, status dimajukan", file=sys.stderr)


def main():
    pulihkan()
    n = 0
    for st in sorted((ROOT / "batches").glob("B*/*/status.json")):
        try:
            s = json.loads(st.read_text(encoding="utf-8"))
        except Exception:
            continue
        cur = s.get("status", "")
        if cur not in PETA or umur_jam(st) < PETA[cur][2]:
            continue
        tugas, baru, batas = PETA[cur]
        if tugas == "cekfakta" and not (st.parent / "riset.json").exists():
            continue
        ulang = s.get("failover_n", 0) + 1
        if cur.endswith("di Codex") and ulang > MAKS_ULANG:
            s.update(status="Butuh cek riset", catatan_failover=f"Codex {tugas} gagal {MAKS_ULANG}x")
            st.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
            print(f"{st.parent.name}: {tugas} di Codex gagal berulang → Butuh cek riset", file=sys.stderr)
            continue
        s.update(status=baru, failover_dari=s.get("failover_dari", cur), failover_n=ulang,
                 failover_t=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        st.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
        job = str(st.parent.relative_to(ROOT / "batches"))
        print(f"{job}\t{tugas}")
        print(f"failover {job}: {cur} > {batas} jam → Codex {tugas}", file=sys.stderr)
        n += 1
        if n >= MAKS:
            break


if __name__ == "__main__":
    main()
