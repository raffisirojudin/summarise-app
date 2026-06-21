# SummaRise - AI Text Summarizer & Assistant

Aplikasi web untuk merangkum, menerjemahkan, dan tanya-jawab dengan teks/dokumen (PDF, DOCX, TXT) menggunakan Google Gemini API. Dibangun dengan Streamlit.

## Fitur

- 🔒 **Proteksi Password (opsional)** — set `APP_PASSWORD` di Secrets, app akan minta password sebelum bisa dipakai
- 📱 **Dropdown Pilih Fitur** — navigasi pakai dropdown (bukan tab), lebih ringkas di layar HP

- 📋 **Ringkas** — rangkum teks panjang jadi poin-poin penting (Pendek/Sedang/Panjang)
- 🌐 **Terjemahkan** — terjemahkan teks ke 9 bahasa pilihan
- 💬 **Tanya Jawab** — chat dan tanya apa saja tentang isi dokumen
- 🎭 **Analisis Sentimen** — deteksi nada teks (positif/negatif/netral/campuran) beserta alasannya
- 🔑 **Ekstrak Kata Kunci & Topik** — ambil kata kunci dan topik utama, cocok buat tag artikel
- 🧠 **Buat Kuis dari Teks** — generate soal pilihan ganda otomatis (3/5/10 soal) untuk belajar
- ✍️ **Ubah Gaya Penulisan** — tulis ulang teks jadi Formal / Santai / Persuasif / Naratif / Akademis / Jurnalistik
- 📄 **Upload File** — bisa paste teks langsung, atau upload PDF/DOCX/TXT, **atau foto** (JPG/PNG/WEBP)
- 📸 **Baca Teks dari Foto** — upload foto artikel/koran/screenshot, Gemini langsung membaca teksnya (tanpa OCR lokal)
- 📊 **Token & Cost Tracker** — info input/output/total token plus estimasi biaya (USD) di setiap respons
- 🕘 **Riwayat Sesi** — semua hasil yang sudah dibuat tersimpan dalam satu tab, bisa dilihat ulang
- 📥 **Download Hasil** — unduh ringkasan/terjemahan/riwayat chat sebagai file `.txt`
- 🧹 **Reset Semua** — bersihkan semua input dan riwayat dengan satu klik
- 📝 **Word Count** — jumlah kata & karakter dari teks yang dimasukkan

## 1. Dapatkan API Key (gratis)

1. Buka https://aistudio.google.com/apikey
2. Login dengan akun Google kamu
3. Klik "Create API Key", lalu salin key tersebut

## 2. Install dependencies (untuk jalan lokal)

```bash
pip install -r requirements.txt
```

## 3. Simpan API Key permanen (Secrets) — opsional tapi disarankan

Supaya nggak perlu ketik API key setiap buka app:

**Untuk dijalankan lokal di komputer:**
1. Salin file `.streamlit/secrets.toml.example` jadi `.streamlit/secrets.toml`
2. Buka file itu, ganti `"masukkan-api-key-kamu-di-sini"` dengan API key asli kamu
3. **Jangan upload file `secrets.toml` ke GitHub** — isinya rahasia

**Untuk app yang sudah di-deploy ke Streamlit Community Cloud:**
1. Buka [share.streamlit.io](https://share.streamlit.io), masuk ke app kamu
2. Klik menu **⋮ (titik tiga)** di app kamu → **Settings** → tab **Secrets**
3. Isi dengan:
   ```toml
   GEMINI_API_KEY = "api-key-asli-kamu"
   ```
4. Klik **Save** — app akan otomatis restart dan kolom API key di sidebar hilang sendiri

Kalau secret belum diisi, app tetap jalan normal — kolom API key manual di sidebar akan muncul seperti biasa.

## 3b. Lindungi app dengan password (opsional, disarankan)

Karena app yang di-deploy punya URL publik, siapapun yang punya link bisa memakainya (dan kuota API key kamu kalau pakai Secrets). Supaya cuma kamu yang bisa akses:

1. Buka Settings → Secrets di Streamlit Cloud (sama seperti langkah di atas)
2. Tambahkan baris:
   ```toml
   APP_PASSWORD = "password-rahasia-kamu"
   ```
3. Klik Save — app akan otomatis minta password ini sebelum bisa dipakai

Kalau `APP_PASSWORD` tidak diisi di Secrets, app akan jalan seperti biasa tanpa proteksi (cocok untuk development lokal).

## 4. Jalankan aplikasi (lokal)

```bash
streamlit run app.py
```

## 5. Cara pakai

1. Pilih sumber teks: **Paste Teks** atau **Upload File** (PDF/DOCX/TXT)
2. Pilih fitur dari dropdown sesuai kebutuhan:
   - **Ringkas** → pilih panjang ringkasan, klik "Rangkum Teks"
   - **Terjemahkan** → pilih bahasa tujuan, klik "Terjemahkan Teks"
   - **Tanya Jawab** → ketik pertanyaan tentang isi teks di kolom chat
   - **Riwayat** → lihat semua hasil sebelumnya di sesi ini, download atau hapus
3. Hasil, info Token Usage, dan estimasi biaya akan muncul di bawahnya
4. Klik **🧹 Reset Semua** di sidebar kalau mau mulai dari awal lagi

## Catatan teknis

- Model: `gemini-2.5-flash-lite` (Gemini 1.5 sudah tidak aktif per 2026)
- SDK: `google-genai` (pengganti `google-generativeai` yang sudah deprecated)
- Ekstraksi PDF: `pypdf` | Ekstraksi DOCX: `python-docx`
- Tab Tanya Jawab menjawab berdasarkan isi teks yang dimasukkan, bukan pengetahuan umum model
- **Riwayat hanya tersimpan selama sesi browser aktif** (memakai `st.session_state`) — kalau refresh/tutup tab, riwayat akan hilang. Ini bukan database permanen.
- **Estimasi biaya** dihitung manual dari harga resmi `gemini-2.5-flash-lite` ($0.10/1M token input, $0.40/1M token output per Juni 2026). Angka ini hanya estimasi kasar — cek billing asli di Google AI Studio untuk angka pasti, karena harga API bisa berubah dari waktu ke waktu.
- **Upload foto** memakai 1 panggilan API tambahan (Gemini Vision) untuk membaca teksnya sebelum diproses lebih lanjut — token & estimasi biayanya juga ditampilkan dan masuk ke Riwayat.
- **Versi library di-pin minimum** (`requirements.txt`) supaya nggak ada update mendadak yang merusak app tanpa kamu sadari.
- **Tema warna** diatur lewat `.streamlit/config.toml` (palet indigo/slate). Pastikan folder `.streamlit` ikut di-upload ke GitHub (termasuk file ini, tapi JANGAN upload `secrets.toml` yang asli) supaya tampilannya konsisten di Streamlit Cloud.

## Mapping panjang ringkasan

| Pilihan | Maks. Poin | max_output_tokens |
|---|---|---|
| Pendek  | 3 | 100 |
| Sedang  | 5 | 200 |
| Panjang | 7 | 300 |
