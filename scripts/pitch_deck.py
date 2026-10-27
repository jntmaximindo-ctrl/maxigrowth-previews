#!/usr/bin/env python3
"""Membuat PDF pitch deck per klinik (tanpa AI). Pemakaian: pitch_deck.py <folder_keluar> [id ...]"""
import glob, json, os, sys
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "decks"
ONLY = set(sys.argv[2:])
FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("R", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("B", FD + "DejaVuSans-Bold.ttf"))
W, H = landscape(A4)
HIJAU, GELAP, ABU, KRIM = HexColor("#0b7a5a"), HexColor("#10231d"), HexColor("#5c6b66"), HexColor("#f4f8f6")

PAKET = [
    ("HEMAT", "Rp 5.500.000", "Rp 4.950.000", [
        "Halaman inti: beranda, layanan, dokter, kontak",
        "Tombol WhatsApp",
        "Google Business: penyiapan sekali",
        "Perawatan 1 bulan setelah tayang"]),
    ("STANDAR", "Rp 8.500.000", "Rp 7.650.000", [
        "Semua isi Hemat",
        "Halaman layanan lengkap, galeri, blog dasar",
        "Sebagian fitur interaktif",
        "Google Business: optimasi + SEO dasar",
        "Perawatan 3 bulan setelah tayang"]),
    ("PREMIUM", "Rp 12.500.000", "Rp 11.250.000", [
        "Semua isi Standar",
        "Fitur interaktif penuh: maskot, pemeriksaan gigi, estimasi biaya",
        "SEO lokal awal + laporan",
        "Perawatan 6 bulan setelah tayang"]),
]


def teks(c, x, y, s, f="R", z=12, w=None, warna=GELAP, lh=None, maks=None):
    c.setFillColor(warna)
    c.setFont(f, z)
    if not w:
        c.drawString(x, y, s)
        return y
    baris, cur = [], ""
    for kata in s.split():
        t = (cur + " " + kata).strip()
        if pdfmetrics.stringWidth(t, f, z) <= w:
            cur = t
        else:
            baris.append(cur)
            cur = kata
    baris.append(cur)
    lh = lh or z * 1.45
    for b in baris:
        c.drawString(x, y, b)
        y -= lh
    return y


def latar(c, n, total, gelap=False):
    c.setFillColor(GELAP if gelap else white)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    if not gelap:
        c.setFillColor(HIJAU)
        c.rect(0, H - 8, W, 8, fill=1, stroke=0)
        teks(c, 40, 24, "Maxi Growth Studio  |  cs@maxigrowthstudio.com  |  WhatsApp 0815-7303-3507", "R", 9, warna=ABU)
        teks(c, W - 70, 24, f"{n} / {total}", "R", 9, warna=ABU)


def buat(klinik, path):
    c = canvas.Canvas(path, pagesize=(W, H))
    c.setTitle("Penawaran website untuk " + klinik["nama"])
    c.setAuthor("Maxi Growth Studio")
    total = 4
    nama, kota, link = klinik["nama"], klinik["kota"], klinik["link"]

    # 1 sampul
    latar(c, 1, total, gelap=True)
    teks(c, 60, H - 90, "MAXI GROWTH STUDIO", "B", 12, warna=HexColor("#6fe0b9"))
    y = teks(c, 60, H - 170, "Website baru untuk", "R", 22, warna=white)
    y = teks(c, 60, y - 34, nama, "B", 38, w=W - 120, warna=white, lh=48)
    teks(c, 60, y - 20, f"Klinik gigi di {kota}", "R", 16, warna=HexColor("#b9d4ca"))
    teks(c, 60, 130, "Contoh website Anda sudah kami buat. Silakan lihat:", "R", 14, warna=white)
    c.setFillColor(HIJAU)
    c.roundRect(60, 78, W - 120, 36, 8, fill=1, stroke=0)
    teks(c, 76, 91, link, "B", 15, warna=white)
    c.linkURL(link, (60, 78, W - 60, 114))
    c.showPage()

    # 2 yang sudah dibuat
    latar(c, 2, total)
    teks(c, 40, H - 60, "Yang sudah kami siapkan untuk " + nama, "B", 22, w=W - 80, lh=28)
    poin = [
        ("Contoh website jadi", "Bukan sekadar desain di kertas. Anda bisa membukanya di ponsel dan komputer lewat tautan di sampul."),
        ("Dibuat dari data klinik Anda", "Nama, layanan, dan informasi umum klinik disusun dari sumber publik yang dapat diperiksa."),
        ("Gratis, tanpa kewajiban", "Contoh website ini gratis. Biaya baru ada jika Anda memutuskan untuk lanjut."),
        ("Pengerjaan dimulai dari contoh", "Karena contohnya sudah ada, pengerjaan versi final sekitar 7 hari kerja setelah DP dan data diterima."),
    ]
    y = H - 140
    for j, (a, b) in enumerate(poin):
        x = 40 + (j % 2) * ((W - 100) / 2 + 20)
        yy = y - (j // 2) * 150
        c.setFillColor(KRIM)
        c.roundRect(x, yy - 110, (W - 100) / 2, 125, 10, fill=1, stroke=0)
        teks(c, x + 16, yy - 14, a, "B", 14, warna=HIJAU)
        teks(c, x + 16, yy - 38, b, "R", 11.5, w=(W - 100) / 2 - 32, warna=GELAP)
    teks(c, 40, 56, "Tautan contoh: " + link, "R", 10, warna=ABU)
    c.linkURL(link, (40, 50, W - 40, 68))
    c.showPage()

    # 3 paket
    latar(c, 3, total)
    teks(c, 40, H - 60, "Tiga paket, tahun pertama sudah termasuk domain dan hosting", "B", 20, w=W - 80, lh=26)
    lebar = (W - 80 - 40) / 3
    for j, (n, harga, diskon, isi) in enumerate(PAKET):
        x = 40 + j * (lebar + 20)
        c.setFillColor(KRIM)
        c.roundRect(x, 90, lebar, H - 190, 12, fill=1, stroke=0)
        c.setFillColor(HIJAU)
        c.roundRect(x, H - 150, lebar, 42, 12, fill=1, stroke=0)
        teks(c, x + 16, H - 136, "PAKET " + n, "B", 15, warna=white)
        teks(c, x + 16, H - 188, harga, "B", 22, warna=GELAP)
        teks(c, x + 16, H - 208, "Keputusan + DP dalam 7 hari (diskon 10%):", "R", 9.5, warna=HIJAU)
        teks(c, x + 16, H - 228, diskon, "B", 14, warna=HIJAU)
        yy = H - 262
        for p in isi:
            yy = teks(c, x + 16, yy, "- " + p, "R", 10.5, w=lebar - 32, warna=GELAP) - 6
    teks(c, 40, 56, "SEO dan Google Business di paket adalah penyiapan dan optimasi awal, bukan layanan SEO bulanan.", "R", 9.5, warna=ABU)
    c.showPage()

    # 4 proses dan langkah
    latar(c, 4, total)
    teks(c, 40, H - 60, "Cara kerja dan langkah berikutnya", "B", 22)
    kiri = [
        "Pembayaran: DP 50 persen di awal, pelunasan 50 persen saat website selesai.",
        "Waktu: sekitar 7 hari kerja setelah DP dan data diterima.",
        "Revisi tanpa batas sampai puas, dalam lingkup paket dan 14 hari setelah draf final.",
        "Setelah lunas, domain dan seluruh kode website menjadi milik klinik.",
        "Setelah tahun pertama: perpanjangan domain dan hosting sekitar Rp 1,5-2 juta per tahun.",
        "Tidak ada pengembalian dana; revisi tanpa batas adalah jaminan kepuasan.",
    ]
    y = H - 110
    for k in kiri:
        y = teks(c, 56, y, "- " + k, "R", 12.5, w=W / 2 - 40, warna=GELAP) - 10
    x = W / 2 + 30
    c.setFillColor(GELAP)
    c.roundRect(x, 90, W / 2 - 70, H - 200, 14, fill=1, stroke=0)
    teks(c, x + 24, H - 140, "Tertarik?", "B", 22, warna=white)
    yy = teks(c, x + 24, H - 176, "Balas pesan kami dan sebutkan paket pilihan Anda. Rekening, invoice, dan kontrak dikirim langsung oleh Dika setelah Anda memilih paket.", "R", 12, w=W / 2 - 118, warna=white)
    yy = teks(c, x + 24, yy - 14, "Diskon 10 persen berlaku jika Anda memutuskan dan membayar DP dalam 7 hari sejak penawaran dikirim.", "R", 12, w=W / 2 - 118, warna=HexColor("#6fe0b9"))
    teks(c, x + 24, 150, "cs@maxigrowthstudio.com", "B", 13, warna=white)
    teks(c, x + 24, 128, "WhatsApp bisnis 0815-7303-3507", "B", 13, warna=white)
    teks(c, x + 24, 106, "Maxi Growth Studio, Bandung", "R", 11, warna=HexColor("#b9d4ca"))
    c.showPage()
    c.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    try:
        review = json.load(open(os.path.join(ROOT, "data", "review.json"), encoding="utf-8"))
    except Exception:
        review = {}
    ada = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "batches", "*", "*", "job.json"))):
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        kid, slug = j.get("id"), j.get("slug")
        if not kid or not slug or (ONLY and kid not in ONLY):
            continue
        if not ONLY and str(review.get(kid, "")).lower() != "lolos":
            continue
        k = {"nama": j.get("nama") or slug.replace("-", " ").title(), "kota": j.get("kota") or "Indonesia",
             "link": "https://maxigrowthstudio.com/%s/" % slug}
        buat(k, os.path.join(OUT, "%s-%s.pdf" % (kid, slug)))
        ada += 1
    print("dibuat", ada)


if __name__ == "__main__":
    main()
