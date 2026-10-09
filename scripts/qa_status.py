#!/usr/bin/env python3
"""Tetapkan status setelah QA otomatis (dipanggil qa.yml).

lolos  → "Siap review" + qc_visual="otomatis" (belum dilihat mata; Claude cek visual SEBELUM klinik dikirimi pesan)
gagal  → "QA gagal"
Status yang sudah diputuskan manusia / tahap lanjut TIDAK ditimpa (pelajaran #17).
"""
import json, pathlib, sys

AKHIR = {"Disetujui", "Terkirim", "Dikirim", "Deal", "Live", "Selesai", "Skip", "Ditolak"}


def tetapkan(d, hasil):
    p = pathlib.Path(d) / "status.json"
    s = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    if s.get("status") in AKHIR:
        return s["status"]
    if hasil == "lolos":
        s["status"] = "Siap review"; s["qc_visual"] = "otomatis"
    else:
        s["status"] = "QA gagal"; s.pop("qc_visual", None)
    p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    return s["status"]


if __name__ == "__main__":
    print(tetapkan(sys.argv[1], sys.argv[2]))
