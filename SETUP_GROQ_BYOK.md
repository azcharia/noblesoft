# Panduan Integrasi Mandiri API Key Groq (BYOK) di NobleSoft

NobleSoft dirancang dengan arsitektur multi-tenant yang terisolasi. Setiap pemilik toko (tenant) bisa memasukkan API Key Groq mereka sendiri agar asisten kasir AI bekerja tanpa batas kuota sistem. Dengan menggunakan API resmi dari Groq secara langsung, data bisnis Anda tetap aman dari kebijakan pelatihan data model gratis seperti yang terjadi jika menggunakan OpenRouter free-tier.

---

## 1. Langkah Mendapatkan API Key Groq

Anda bisa mendapatkan API Key secara gratis langsung dari konsol resmi pengembang Groq:

1. **Daftar atau Masuk**: Buka halaman [Groq Console](https://console.groq.com/) di peramban Anda. Anda bisa mendaftar menggunakan email baru atau masuk langsung dengan akun Google.
2. **Buka Menu API Keys**: Setelah masuk ke dasbor, temukan opsi **API Keys** di menu bagian kiri layar Anda.
3. **Buat Key Baru**: Klik tombol **Create API Key**.
4. **Beri Nama Key**: Berikan nama yang mudah diingat, misalnya `NobleSoft-Asisten-Kasir`.
5. **Salin Key**: Klik tombol salin pada kode API Key yang muncul. Kode ini akan selalu diawali dengan huruf `gsk_`.
   > [!WARNING]
   > Groq hanya memperlihatkan kode API Key ini satu kali demi keamanan. Simpan kode ini di tempat yang aman sebelum menutup kotak dialog.

---

## 2. Memasukkan API Key ke Dasbor NobleSoft

Setelah memegang kode API Key Anda, hubungkan key tersebut ke ruang kerja toko Anda:

1. **Buka Halaman Pengaturan**: Masuk ke aplikasi kasir NobleSoft Anda, lalu klik menu **Settings** dan pilih **AI & API Settings** (atau akses langsung ke alamat `/settings/ai`).
2. **Isi Formulir Integrasi**:
   - **Groq API Key**: Tempel kode API Key (`gsk_...`) yang sudah disalin sebelumnya.
   - **Custom Base URL (Opsional)**: Kosongkan bagian ini untuk menggunakan server standar Groq. Jika Anda memakai proxy atau gateway API kustom yang kompatibel dengan format OpenAI, Anda bisa memasukkan URL tersebut di sini.
   - **Model Name**: Secara default, sistem memakai `llama-3.1-8b-instant`. Anda bisa menggantinya dengan model resmi Groq lainnya:
     - `llama-3.3-70b-versatile` (Model Meta 70 miliar parameter, sangat cerdas untuk memahami instruksi rumit dan pemanggilan fungsi penjualan).
     - `llama-3.1-8b-instant` (Model Meta 8 miliar parameter, memberikan respons yang sangat cepat dengan latency rendah).
     - `mixtral-8x7b-32768` (Model dari Mistral AI yang handal untuk analisis teks).
     - `gemma2-9b-it` (Model efisien rancangan Google).
   - **Temperature**: Kami sarankan di angka `0.2`. Nilai yang rendah membuat asisten AI tetap konsisten, akurat, dan tidak mengarang data saat memproses transaksi barang.
3. **Simpan Perubahan**:
   - Klik tombol **Simpan Perubahan**.
   - Aplikasi akan melakukan tes koneksi (ping) secara otomatis ke server Groq untuk memverifikasi validitas key sebelum disimpan.
   - Jika verifikasi berhasil, pengaturan terenkripsi akan tersimpan dengan aman khusus untuk database toko Anda.

---

## 3. Keamanan Data dan Alur Kerja

- **Isolasi Penuh**: API Key yang Anda masukkan disimpan dalam tabel khusus `tenant_ai_settings` yang dilindungi oleh sistem keamanan Supabase Row Level Security (RLS). Hanya akun dari toko Anda yang bisa mengakses atau menggunakan key ini.
- **Koneksi Langsung ke Groq**: Semua perintah suara atau teks kasir Anda dikirim langsung ke endpoint API pengembang Groq resmi. Data transaksi Anda tidak akan bocor ke tenant lain atau digunakan untuk melatih model publik.
- **Pemrosesan Data Lokal**: Pembuatan vektor pencarian (embedding) untuk produk inventory dan struk penjualan berjalan seutuhnya di server lokal Anda menggunakan model gratis `sentence-transformers/all-MiniLM-L6-v2`. Tidak ada data mentah inventory Anda yang dikirim ke API luar untuk sekadar di-index.
