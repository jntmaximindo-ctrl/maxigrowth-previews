# Tugas Codex · REVISI PREVIEW · job {{JOB}}

Pemilik (Rizqi) meminta revisi pada preview yang sudah jadi: `{{DIR}}/site/index.html`.
Permintaan revisi ada di file TERBARU di folder `{{DIR}}/revisi/` (nama file berupa tanggal-jam). Baca seluruhnya.

## Aturan
1. Ubah HANYA yang diminta. Bagian lain (desain, fitur, teks, warna) tetap persis seperti sekarang.
2. Kalau permintaan butuh fakta baru (jam, alamat, dokter, harga), pakai hanya dari `riset.json` atau yang ditulis pemilik di file revisi. Jangan mengarang.
3. Tetap patuh AGENTS.md dan Permenkes 1787/2010 (`python scripts/lint_permenkes.py {{DIR}}/site/index.html` = 0 pelanggaran).
4. Kalau ada permintaan yang tidak bisa/berisiko dikerjakan, kerjakan sisanya dan jelaskan di ringkasan bagian "UNTUK CLAUDE".

## Cek & push
- `python scripts/codex_check.py check {{DIR}} rakit` harus LULUS.
- Cek tampilan 375px dan 1440px dengan Playwright, tanpa error console.
- Commit lalu `git push origin HEAD:<branch PR ini>`. Push HANYA `{{DIR}}/site/index.html`.
