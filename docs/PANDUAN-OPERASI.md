# Panduan Operasi — Maxi Growth Studio (pabrik preview website klinik gigi)

Dokumen ini untuk siapa pun (manusia atau AI) yang melanjutkan sistem ini tanpa pemilik. Pemilik: Muhammad Rizqi Tri Andika ("Dika"), Bandung. Kontak bisnis: WA Business 0815-7303-3507, cs@maxigrowthstudio.com.

## 1. Tujuan
Menemukan klinik gigi yang websitenya jadul atau belum punya, membuat preview website (noindex) di maxigrowthstudio.com/<slug>/, lalu pemilik mengirim penawaran lewat WA. Semua tahap sebelum pengiriman berjalan otomatis.

## 2. Arsitektur singkat
Sheet antrean → intake (robot) → GPT-A riset → GPT-B cek fakta → rakit dari template (tanpa AI) → QA → deploy.
- Repo: jntmaximindo-ctrl/maxigrowth-previews. Robot utama: `.github/workflows/orkestrator.yml` (cron tiap 30 menit) dan `intake-batch`.
- Sheet id: 1yVhvg-zzeRG_UOqEVv9xMH2e1sFBD7ZwH---X6o7-ds. Dasbor: https://claude.ai/artifact/METGtHa6j5aanAx6HDqo6p
- Drive "bus" (rclone remote `bus:`): 00 ATURAN, 01 Antrean Riset, 02 Hasil Riset, 03 Hasil Cek Fakta, 05 Antrean Cari, 08 Perintah Claude (repo), 09 Laporan Robot, 99 Arsip. File GPT tulis di root My Drive; robot yang memindahkan.
- Laporan kesehatan: Drive "09 Laporan Robot/laporan-terakhir.md" (STATUS HIJAU/KUNING/MERAH, alarm [claude]/[manusia]).

## 3. Siapa mengerjakan apa
- **GPT-A (akun ChatGPT jnt9292) dan GPT-B (akun suharti)**: pekerja chat. Tugas terjadwal per jam + sesi manual lewat teks siap salin. Riset, cek fakta, dan pencarian klinik (surat tugas per kecamatan).
- **Codex**: DIJEDA. Tidak dipakai untuk riset/pencarian. Hanya cadangan perakitan; slot Codex #2 sengaja dijeda. Jangan aktifkan tanpa perintah pemilik.
- **Robot Actions**: intake, validasi, sinkron Sheet/Drive, deploy, laporan. Tanpa AI.
- **Claude**: mandor. Merancang, memperbaiki, menerapkan perubahan lewat jembatan Drive, memantau laporan.

## 4. Keputusan pemilik (jangan diubah tanpa izin)
- TIDAK ADA batas jumlah klinik dibuat atau outreach per hari (keputusan pemilik 10 Okt 2026); batasnya hanya kuota AI. Intake 50 per ambil (`PER_BATCH`), `HARIAN`/`AKTIF_MAKS` praktis tak terbatas.
- Klinik jaringan besar (mis. FDC, Audy) di-Skip, tidak dikirimi outreach.
- Teks sesi manual GPT A/B dibuat untuk mode Work (antrean besar sekaligus).
- Sourcing klinik lewat chat GPT (`data/sourcing-engine.txt` = gpt); Codex tidak dipakai mencari.
- Kriteria klinik: rating >= 4.5 dan ulasan >= 100. Tanpa website = prioritas tertinggi.
- Pengiriman WA ke klinik HANYA dengan izin eksplisit pemilik. Robot dan AI tidak pernah menghubungi klinik.
- Konten patuh Permenkes 1787/2010 (tanpa "terbaik", "termurah", "dijamin", "gratis", "promo", "diskon", testimoni, janji hasil). Cek: `python scripts/lint_permenkes.py <file>`.
- Fakta klinik wajib punya sumber (src); tidak ketemu = null. Dilarang mengarang dokter, alamat, telepon, harga, ulasan.
- Preview online tanpa persetujuan pemilik; persetujuan hanya untuk pengiriman outreach.

## 5. Akun dan kredensial
Kredensial hanya di GitHub Secrets / Drive pemilik (CLAUDE_PAT, RCLONE_*, GOOGLE_SA_JSON, CLOUDFLARE_*). Jangan ditulis di chat, repo, atau dokumen. AI dilarang mengetik kata sandi/token atau membuat akun. Jangan menyentuh browser pribadi pemilik.

## 6. Menjalankan sesi manual (opsional, tambahan di luar tugas per jam)
- Riset/cek fakta: teks siap salin dari pemilik (Teks 1 = GPT-A riset, Teks 2 = GPT-B cek fakta). Surat di "01 Antrean Riset".
- Pencarian klinik: Teks 3A (GPT-A, surat dari A ke Z) dan 3B (GPT-B, dari Z ke A), surat di "05 Antrean Cari". Tempel ulang setiap sesi berhenti. Hasil: `CARI-<id>_hasil.json.md` di root My Drive.
Sistem tetap berjalan tanpa sesi manual karena tugas terjadwal per jam.

## 7. Perubahan kode (jembatan Drive)
Claude menaruh `NNN-nama.json` di Drive "08 Perintah Claude (repo)": kunci id, pesan, tulis, ganti, hapus, variabel (hanya RAKIT_ENGINE, RISET_ENGINE, SHEET_ID), jalankan, paket. `ganti` harus cocok tepat 1x. Perubahan workflow baru berlaku run berikutnya, jadi dispatch orkestrator dua kali. Perintah gagal dicatat di laporan dan tidak diulang. Jangan mengunggah ke GitHub lewat web.

## 8. Aturan perbaikan diri
Setiap error = ATURAN + PENJAGA + PELAJARAN: aturan di kode, tes di `tests/uji_regresi.py`, baris di `docs/pelajaran.md`. Sebelum memperbaiki, baca pelajaran.md; kalau gejala sudah ada berarti aturan lamanya kurang kuat. Salinan pelajaran.md dan panduan ini disinkronkan ke Drive "09 Laporan Robot" tiap run.

## 8b. Tugas terjadwal ChatGPT (per jam)
- Akun jnt9292 (GPT-A): "GPT-A Klinik-Bus" (riset) dan "Klinik-Bus GPT-A Cari Klinik" (surat dari A ke Z, target 60 surat per run).
- Akun suharti (GPT-B): "Klinik-Bus GPT-B Cek Fakta" dan "Klinik-Bus GPT-B Cari Klinik" (surat dari Z ke A, target 60 surat per run). Satu lagi: "Klinik-RnD Fitur Mingguan".
- Dibuat 2026-10-10; cek di https://chatgpt.com/scheduled (maks 5 tugas per akun). Kalau teks surat berubah, tugas harus diedit agar sama dengan teks manual.
- Aturan browser: automasi Chrome HANYA di dua profil: jnt9292 dan suharti. Profil pribadi pemilik (kudakuda) DILARANG disentuh, termasuk lewat sesi terjadwal. Kalau pemilik melihat notifikasi "Claude started debugging this browser" di profil pribadi, itu pelanggaran: hentikan dan perbaiki.

Cakupan: seluruh Indonesia (data/area.txt = kota besar per kecamatan; data/area-nusantara.txt = ~700 area urut prioritas Jawa, Sumatra, Kalimantan, Sulawesi, Bali/NT, Maluku/Papua). Setelah semua area terbit, robot memulai putaran berikutnya (5 putaran, tiap putaran fokus berbeda di VARIAN scripts/cari_chat.py), total >4000 surat: pasokan kerja cukup berbulan-bulan. Tambah area/fokus dengan menambah baris di file area atau VARIAN.

Metode kerja GPT (sejak 2026-10-10): berbasis RENCANA dan PROGRES. Tiap run GPT menulis RENCANA-CARI-A.md atau RENCANA-CARI-B.md di root My Drive (daftar surat dibagi tahap 5 surat), mengerjakan per tahap, mencentang progres, lalu lanjut tanpa laporan akhir. Target jumlah murni (15 atau 60 surat) terbukti tidak mengikat. Tugas terjadwal per jam di akun A dan B memakai teks yang sama dengan teks manual. Catatan lama tentang target: 15 surat selesai hanya dalam ~2 menit (terlalu cepat, kualitas dipertanyakan), jadi target dinaikkan ke 60 agar run memakan sekitar 15 menit dan surat butuh minimal 5 pencarian. Stok surat maksimal 120 belum selesai (OUTSTANDING_MAKS).

## 9. Pemantauan
Fase development: cek laporan tiap ~30 menit. Setelah satu siklus penuh tanpa campur tangan dan 24 jam hijau: tiap 3 jam. Alarm [manusia] hanya untuk hal yang tidak bisa diperbaiki Claude (mis. akun/izin).
