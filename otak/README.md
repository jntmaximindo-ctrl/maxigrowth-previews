# Otak perusahaan — Maxi Growth Studio

Semua kepintaran perusahaan disimpan DI SINI, bukan di kepala satu AI. Setiap AI (Claude, GPT, Codex, AI baru)
wajib membaca bagian yang relevan sebelum bekerja. Kalau AI diganti, pengetahuannya tetap tinggal.

| file | isi | siapa menulis | siapa membaca |
|---|---|---|---|
| otak/mandat.md | apa yang boleh diputuskan Claude sendiri vs wajib ke pemilik | pemilik (Claude mengusulkan) | Claude (setiap sesi) |
| otak/keputusan.md | log keputusan penting + alasannya | Claude | Claude |
| docs/pelajaran.md | error teknis → aturan → penjaga | Claude | Claude |
| AGENTS.md (+ bagian otomatis) | aturan kerja Codex + kesalahan umum | Claude + robot belajar.py | Codex |
| Drive "00 ATURAN KLINIK-BUS" (+ bagian otomatis) | aturan kerja GPT-A/GPT-B + kesalahan umum | Claude + robot belajar.py | GPT |
| prompts/, schemas/ | surat tugas & format keluaran per peran | Claude | Codex/GPT |
| library/referensi/ | contoh terbaik (bank contoh) | robot (dari preview yang disetujui) | Codex |
| data/qa-log.jsonl | catatan lulus/gagal setiap hasil kerja | robot | robot rapor |
| data/rapor.md | rapor pekerja per peran (tingkat lulus, revisi) | robot rapor.py | Claude |

## Empat putaran belajar
1. Operasional (tiap 30 menit): error → aturan + tes regresi (tests/uji_regresi.py) + docs/pelajaran.md
2. Kualitas pekerja (tiap run): kesalahan berulang → masuk instruksi pekerja otomatis; rapor pekerja
3. Hasil bisnis (mingguan, setelah outreach dibangun): terkirim → dibalas → deal; 1–2 eksperimen/minggu
4. Strategi (bulanan): evaluasi Claude → keputusan kecil dijalankan, keputusan besar ke pemilik

## Peran (saat ini)
- Claude — mandor: merancang, menilai rapor, menulis ulang instruksi, memperbaiki aturan
- GPT-A (scheduled task) — peneliti klinik + penulis konten
- GPT-B (scheduled task) — pemeriksa fakta independen
- Codex (pool akun) — pencari klinik, perakit website, revisi, cadangan riset/cek fakta
- Robot GitHub Actions — jalur, cek otomatis, merge, deploy, sinkron, laporan, loop belajar (tanpa AI)
Peran baru ditambah di sini + wajib lulus "ujian masuk" (kasus lama berjawaban benar) sebelum kerja sungguhan.
