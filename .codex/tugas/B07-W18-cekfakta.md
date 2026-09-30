# Tugas Codex GPT-B · CEK FAKTA INDEPENDEN · job B07/W18

Kamu pemeriksa independen. Riset di `batches/B07/W18/riset.json` dibuat oleh pekerja lain.

1. Ikuti `prompts/cekfakta.md` (ganti {{RISET_JSON}} dengan isi `batches/B07/W18/riset.json`).
   Buka ULANG setiap URL `src` dengan akses internet dan periksa apakah nilainya benar-benar tertulis di halaman itu.
2. Simpan hasil sebagai `batches/B07/W18/cekfakta.json` dengan field: id, diperiksa, beda[], tidak_bisa_dibuka[], kritis_ok.
3. JANGAN mengubah riset.json atau file lain. Jangan mengarang isi halaman yang tidak bisa dibuka.
4. Cek sendiri: `pip install jsonschema && python scripts/codex_check.py check batches/B07/W18 cekfakta` harus LULUS.
5. Push HANYA cekfakta.json ke branch PR ini.
