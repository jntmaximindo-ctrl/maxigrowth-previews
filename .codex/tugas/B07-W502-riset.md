# Tugas Codex GPT-A · RISET + KONTEN · job B07/W502

Folder kerja: `batches/B07/W502` (sudah berisi `job.json` dan mungkin `branding/`).

1. Baca `job.json`, lalu kerjakan RISET persis mengikuti `prompts/riset.md`
   (ganti {{SCHEMA}} dengan isi `schemas/riset.schema.json`, {{JOB_JSON}} dengan isi `job.json`).
   Buka website klinik dan sumber lain dengan akses internet. Setiap fakta: `v`, `src` (URL yang benar-benar dibuka), `tgl`, `yakin`.
   Tidak ketemu → `v: null, src: null`. DILARANG menebak.
   Simpan sebagai `batches/B07/W502/riset.json`.
2. Dari riset itu, tulis KONTEN persis mengikuti `prompts/konten.md`
   (skema `schemas/konten.schema.json`, slug = field `slug` di job.json atau id huruf kecil).
   Simpan sebagai `batches/B07/W502/konten.json`.
3. Cek sendiri sebelum push:
   - `pip install jsonschema && python scripts/codex_check.py check batches/B07/W502 riset` harus mencetak LULUS.
4. Push HANYA dua file itu ke branch PR ini. Jangan ubah file lain.
5. Di ringkasan PR tulis: jumlah fakta terisi vs null, sumber utama, dan bagian "UNTUK CLAUDE" bila ada yang ragu.
