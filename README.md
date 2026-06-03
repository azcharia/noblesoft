<div align="center">
  <img src="logo/noblesoft.jpg" alt="NobleSoft Logo" width="120" height="120" style="border-radius: 24px; margin-bottom: 16px;" />
  <h1>NobleSoft</h1>
  <p><b>Aplikasi Kasir Digital & Manajemen Stok Berbasis AI yang Sangat Sederhana dan 100% Open Source</b></p>
  
  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs)](https://nextjs.org/)
  [![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
  [![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
</div>

<br />

## 📖 Tentang NobleSoft

NobleSoft adalah platform kasir digital (*point-of-sale*) dan pencatatan stok barang yang dirancang khusus untuk pedagang UMKM mikro/menengah ke bawah di Indonesia agar dapat mengelola operasional sehari-hari dengan **sangat mudah dan cepat**.

Berbeda dengan aplikasi kasir konvensional yang rumit dengan puluhan menu membingungkan, NobleSoft menghadirkan pendekatan **Chat-First Kasir** dibantu oleh AI. Cukup ketik perintah kasir alami seperti:
- *"Jual Kopi Susu 2 cup ke Budi"*
- *"Tambah stok Sabun Mandi 10 pcs"*
- *"Tampilkan invoice yang belum dibayar"*

Dan AI akan otomatis mencatat transaksi, memperbarui stok di database, serta membuat struk/invoice untuk pelanggan secara instan tanpa ribet.

## ✨ Fitur Utama

- 🤖 **AI Asisten Kasir & Stok**: Cukup mengobrol dengan AI untuk mencatat penjualan, memperbarui stok, atau bertanya tentang kondisi keuangan toko.
- 🔑 **Bring Your Own Key (BYOK)**: Keamanan privasi data maksimal dengan integrasi API Key Groq terisolasi per tenant. Selengkapnya di [SETUP_GROQ_BYOK.md](file:///D:/STUDY/Kuliah/flutter/PROJECT/noblesoft/SETUP_GROQ_BYOK.md).
- 📦 **Manajemen Inventory Sederhana**: Pantau stok produk, peringatan ketika stok menipis (*low stock*), dan nilai estimasi aset toko.
- 🧾 **Pembuat Invoice & Struk Otomatis**: Buat dan unduh struk penjualan digital langsung setelah pencatatan selesai.
- 📊 **Dasbor Keuangan Ringkas**: Tiga kartu kas minimalis (Uang Masuk, Laba Bersih Estimasi, dan Stok Habis) langsung di halaman utama.
- 🏢 **Multi-User & Multi-Tenant**: Siap digunakan oleh beberapa karyawan toko sekaligus dengan keamanan data terisolasi menggunakan Supabase.
- 🔓 **100% Gratis & Open Source**: Bebas digunakan tanpa biaya langganan bulanan, tanpa batasan fitur, dan tanpa iklan.

## 🛠 Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS + PostCSS
- **UI Components:** shadcn/ui

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **AI/ML Engine:** LlamaIndex + Groq API

### Database & Security
- **Database:** Supabase (PostgreSQL + `pgvector`)
- **Auth:** Supabase Auth (JWT)

## 📂 Struktur Repositori

```text
noblesoft/
├── backend/                 # Python FastAPI Backend
│   ├── app/                 # Kode backend (API, Core, AI Services)
│   ├── tests/               # Unit testing suite
│   └── requirements.txt     # Dependensi Python
├── frontend/                # Next.js Frontend
│   ├── src/                 # Kode frontend (React Components, Pages, Hooks)
│   └── package.json         # Dependensi Node.js
└── *.sql                    # Skema database & data awal (seed)
```

## 🚀 Panduan Instalasi Cepat (Bagi Pengguna Awam / Lokal)

Aplikasi ini dapat dijalankan di komputer lokal Anda dengan beberapa langkah mudah.

### Prasyarat
Sebelum memulai, pastikan komputer Anda sudah terpasang:
1. **Node.js** (Versi 18 ke atas) -> [Unduh di sini](https://nodejs.org/)
2. **Python** (Versi 3.10 ke atas) -> [Unduh di sini](https://www.python.org/)
3. **Akun Supabase Gratis** -> [Daftar di sini](https://supabase.com/)

---

### Langkah 1: Siapkan Database Supabase & Autentikasi
1. Masuk ke dasbor Supabase Anda dan buat proyek baru.
2. **Setup Skema Database (Pilih salah satu metode berikut):**
   - **Metode A (Migrasi CLI Otomatis - Direkomendasikan)**: 
     Tambahkan variable `DATABASE_URL` pada berkas `.env` di backend (lihat Langkah 2), lalu jalankan perintah migrasi dari folder `frontend/`:
     ```bash
     pnpm run db:migrate
     ```
   - **Metode B (Manual SQL Editor)**: Buka menu **SQL Editor** di dasbor Supabase Anda, lalu salin dan jalankan isi berkas `supabase_setup.sql`.
   - **Metode C (Supabase CLI)**: Jika Anda menggunakan Supabase CLI secara lokal, jalankan perintah berikut di folder root:
     ```bash
     supabase db push
     ```
3. **Konfigurasi Keamanan Autentikasi (Penting agar Pendaftaran Berjalan Lancar):**
   - Di dasbor Supabase, buka menu **Authentication** -> **Providers** -> **Email**.
   - **Nonaktifkan (Disable)** opsi **Confirm email** jika Anda ingin pengguna baru bisa langsung masuk (login) tanpa perlu memverifikasi email terlebih dahulu.
   - **Aktifkan (Enable)** opsi **Allow public sign-ups** agar pendaftaran toko baru dari form aplikasi dapat berjalan.

---

### Langkah 2: Konfigurasi File Lingkungan (Environment Variables)

Buat file `.env` di folder backend dan frontend Anda untuk menghubungkan ke database Supabase dan Groq AI:

**Di folder `backend/`:**
Salin berkas `.env.example` menjadi `.env` lalu isi:
```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile
```

**Di folder `frontend/`:**
Salin berkas `.env.example` menjadi `.env.local` lalu isi:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

### Langkah 3: Jalankan Otomatis (Windows)
Jika Anda menggunakan Windows, kami telah menyediakan skrip otomatis untuk mempercepat proses instalasi dan menjalankan aplikasi:

1. Buka PowerShell di folder `noblesoft`.
2. Jalankan perintah berikut untuk mengecek sistem dan menginstal dependensi:
   ```powershell
   .\preflight.ps1
   ```
3. Jalankan perintah ini untuk menyalakan backend dan frontend secara bersamaan:
   ```powershell
   .\run-dev.ps1
   ```
4. Buka browser Anda di alamat [http://localhost:3000](http://localhost:3000) untuk mulai menggunakan kasir digital NobleSoft!

*Untuk mematikan server secara aman, jalankan:*
```powershell
.\stop-dev.ps1
```

---

### Langkah 4: Jalankan Manual (Alternatif)

**Backend:**
```bash
cd backend
python -m venv venv
# Aktifkan venv:
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 🧪 Pengujian Sistem
Untuk memverifikasi bahwa semua sistem backend berjalan dengan baik:
```bash
cd backend
pytest
```

## 📄 Lisensi
Proyek ini berlisensi **MIT License** - bebas digunakan, dimodifikasi, dan didistribusikan secara gratis untuk keperluan komersial maupun non-komersial.

---
Dibuat dengan ❤️ oleh komunitas untuk memajukan UMKM Indonesia.
