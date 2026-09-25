# maxigrowth-previews

Meja kerja otomatis Maxi Growth Studio untuk preview website klinik gigi.
Google Drive = bank data (arsip lengkap). Repo ini = tempat kerja bersama Claude, GPT, dan GitHub Actions.

## Alur per batch (10 klinik)

1. `intake.yml` (tiap hari 06:00 WIB atau manual) membaca Sheet **Waiting List Klinik**,
   mengambil 10 baris `Status = Menunggu` (urut Prioritas → No), membuat `batches/Bxx/<ID>/job.json`
   dan satu issue per klinik berlabel `riset`.
2. `research.yml` (issue berlabel `riset`) menjalankan `scripts/research.py` (OpenAI API + web search)
   → `riset.json` + `konten.json`, lalu cek fakta silang → PR `riset/<ID>`.
3. `branding.yml` (issue berlabel `riset`) menjalankan `scripts/brand_capture.mjs`
   → screenshot situs lama + kandidat warna hex + URL logo → folder `branding/`.
4. Claude (scheduled task) mengambil klinik yang riset + branding-nya lengkap: logo SVG bersih,
   memilih resep section + tema, merakit `site/index.html`, PDF, outreach.
5. `qa.yml` (push ke `batches/**/site/`) menjalankan `scripts/qa.mjs` + `scripts/lint_permenkes.py`.
   Gagal → komentar di issue, label `qa-gagal`.
6. `sync-drive.yml` (setiap push ke `main`) menyalin `batches/` dan `library/` ke Drive
   `Maxi Growth – Previews/02 Batch` dan `01 Library` via rclone, lalu menulis status ke Sheet.

## Secrets yang diisi pemilik sendiri (Settings → Secrets and variables → Actions)

| Nama | Isi |
|---|---|
| `OPENAI_API_KEY` | Kunci API OpenAI (billing terpisah dari ChatGPT Plus) |
| `GOOGLE_SA_JSON` | Isi file JSON service account Google Cloud (untuk Sheet) |
| `RCLONE_DRIVE_TOKEN` | Token OAuth Drive akun pemilik dari `rclone authorize "drive"` (untuk upload ke Drive) |
| `GOOGLE_PLACES_KEY` | (opsional) kunci Google Places API untuk rating & ulasan |

Variables (bukan rahasia): `SHEET_ID`, `DRIVE_BATCH_ID`, `DRIVE_LIBRARY_ID`, `DRIVE_REPO_ID`.

## Aturan

- Tidak ada pesan/email ke klinik dari sistem ini. Outreach dikirim manusia.
- Tidak deploy ke Cloudflare otomatis. Deploy manual setelah review pemilik.
- Semua fakta di `riset.json` wajib punya `src`. Tanpa sumber → tampil sebagai ✎ verifikasi.
- Kepatuhan Permenkes 1787/2010: lihat `scripts/lint_permenkes.py`.
