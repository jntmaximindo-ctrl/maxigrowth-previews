# Library fitur klinik gigi

Alur: GPT (mingguan) → `ide/<tanggal>.json` + `ide/INDEX.md` → Claude memilih (edit `data/fitur-pilihan.json`, status "pilih") → Codex membangun modul di `modul/<slug>/` → cek otomatis (`scripts/fitur.py check`) → merge → `katalog.json` / `KATALOG.md`.

Modul = `fitur.html` (potongan section+style+script, semua nama berawalan `<slug>-`), `demo.html`, `manifest.json`, `README.md`. Data klinik dibaca dari `window.KLINIK_FITUR`; warna dari CSS variable brand. Wajib berujung ke pesan WhatsApp, patuh Permenkes 1787/2010.

Perakit (Codex/template) memakai `katalog.json` untuk memilih fitur yang cocok dengan klinik baru dan menyalin `fitur.html` ke `site/index.html`.
