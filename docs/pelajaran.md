# Buku pelajaran sistem (dibaca Claude sebelum memperbaiki apa pun)

Setiap error yang ditemukan dicatat di sini: gejala, akar masalah, ATURAN yang dipasang supaya kelas error itu tidak terulang,
dan PENJAGA (tes/alarm) yang membuktikan aturannya jalan. Perbaikan tanpa aturan + penjaga = belum selesai.
Penjaga berupa tes ditulis di tests/uji_regresi.py dan dijalankan SETIAP run; tes gagal = alarm ke Claude.
Kesalahan pekerja (Codex/GPT) yang berulang di ≥2 klinik otomatis masuk AGENTS.md & file ATURAN GPT (scripts/belajar.py).
Sebelum memperbaiki: cari gejala serupa di tabel ini. Kalau sudah pernah → aturan lama kurang kuat; perbaiki aturannya, jangan cuma kasusnya.

| # | tanggal | gejala | akar masalah | aturan yang dipasang | penjaga |
|---|---|---|---|---|---|
| 1 | 2026-09-29 | putaran rakit tiap jam, kuota Codex/GPT habis | workflow lama masih aktif + tidak ada batas kirim ulang | PR terbuka tidak dikirim ulang; maks 2x gagal per tugas; saklar kontrol.json | codex-dispatch berhenti "STOP ... 2 kali gagal" |
| 2 | 2026-09-30 | orkestrator gagal 5x beruntun (08:17–10:47 WIB) | push file workflow memakai GITHUB_TOKEN (header checkout menimpa PAT) | jembatan push sendiri dengan CLAUDE_PAT + header dikosongkan; perintah gagal tidak diulang tiap run (dicatat ❌, diarsipkan) | laporan "Perintah Claude": ✅ push / ❌ push gagal |
| 3 | 2026-09-30 | (ditemukan sebelum terjadi) semua slot Codex habis → langkah 1 crash | variabel slot kosong → bash error | slot kosong = tunda ke run berikutnya, bukan error | uji lokal bash -e dengan slot kosong |
| 4 | 2026-09-30 | PR rakit #96–100 diam >12 jam | Codex menjawab "selesai" tapi tidak push; tidak ada aturan untuk kasus ini | pool: balasan tanpa commit >30 menit → panggil ulang "wajib push"; maks 3x → Claude | laporan Codex pool (gagal berturut) + alarm PR tanpa aktivitas >6 jam |
| 5 | 2026-09-30 | pengecekan Claude hanya 2x sehari → error ketahuan telat 11 jam | jadwal cek terlalu jarang saat fase development | fase dev: cek tiap 30 menit; setelah terbukti 24 jam hijau → 3 jam | jadwal cek di sesi Claude |
| 6 | 2026-09-30 | PR yang baru dipanggil ulang bisa ikut ditutup | aturan tutup memakai umur PR, bukan aktivitas terakhir | tutup PR rakit hanya bila tanpa aktivitas >3 jam | 007 |
| 7 | 2026-09-30 | aturan #4 terpasang tapi PR #96–100 tetap tidak disentuh | pool hanya mengenali teks panggilan versi baru ("Kerjakan tugas"); PR lama memakai teks lain; tidak ada log pool di laporan | panggilan = komentar @codex dari siapa pun selain bot Codex; hasil pindai pool ditulis ke laporan | laporan bagian "Aksi pool run ini" |
| 8 | 2026-09-30 | pemilik: masalah yang sama tidak boleh terulang di sesi berikutnya | perbaikan hanya di kepala Claude/kasus, tidak jadi aturan pekerja & tidak dites ulang | loop belajar pekerja (belajar.py) + uji regresi tiap run + buku pelajaran wajib dibaca | tests/uji_regresi.py (7 tes) |
