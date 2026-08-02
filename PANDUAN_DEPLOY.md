# 🚀 PANDUAN DEPLOY CLAUDE CHAT APP

## 📋 DAFTAR ISI
1. [Buat GitHub Repository Baru](#1-buat-github-repository-baru)
2. [Upload File ke GitHub](#2-upload-file-ke-github)
3. [Deploy ke Railway](#3-deploy-ke-railway)
4. [Set Environment Variables](#4-set-environment-variables)
5. [Test Aplikasi](#5-test-aplikasi)
6. [Troubleshooting](#troubleshooting)

---

## 1️⃣ BUAT GITHUB REPOSITORY BARU

### Langkah:
1. Buka: https://github.com/new
2. **Repository name:** `claude-chat-app`
3. **Visibility:** Public (atau Private jika mau)
4. **❌ JANGAN centang** "Add a README file"
5. **❌ JANGAN pilih** .gitignore atau license
6. Klik **"Create repository"**

✅ **Repo kosong sudah dibuat!**

---

## 2️⃣ UPLOAD FILE KE GITHUB

### Cara 1: Via Web (Upload Manual)

1. Di halaman repo baru, klik **"uploading an existing file"**
2. **Drag & drop SEMUA file** dari folder `claude-chat-app-clean`:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `.gitignore`
   - `.python-version`
   - `README.md`
   - Folder `templates/` (dengan `index.html` di dalamnya)
   - Folder `uploads/` (dengan `.gitkeep` di dalamnya)

3. **Commit message:** "Initial commit - clean rebuild"
4. Klik **"Commit changes"**

### Cara 2: Via Git Command Line (Jika paham Git)

```bash
cd claude-chat-app-clean
git init
git add .
git commit -m "Initial commit - clean rebuild"
git branch -M main
git remote add origin https://github.com/widodobudi/claude-chat-app.git
git push -u origin main
```

✅ **Semua file sudah di GitHub!**

---

## 3️⃣ DEPLOY KE RAILWAY

### Langkah:

1. Buka: https://railway.app
2. Login dengan GitHub
3. Klik **"New Project"**
4. Pilih **"Deploy from GitHub repo"**
5. **Pilih repository:** `widodobudi/claude-chat-app`
6. Railway akan auto-detect:
   - ✅ Python runtime
   - ✅ requirements.txt
   - ✅ Procfile
7. Klik **"Deploy"**

⏳ **Tunggu build selesai (2-5 menit)**

Railway akan:
- Install dependencies dari `requirements.txt`
- Run command dari `Procfile`: `gunicorn app:app`
- Generate public URL

✅ **Deployment berhasil!** (Status: Active)

---

## 4️⃣ SET ENVIRONMENT VARIABLES

### Langkah:

1. Di Railway, klik service **"web"**
2. Klik tab **"Variables"**
3. Klik **"New Variable"** (4x untuk 4 variables)

### Variables yang HARUS diset:

```
AI_MODEL = claude-sonnet-4
```

```
CRAZYROUTER_API_KEY = <API key Anda dari crazyrouter.com>
```

```
GITHUB_TOKEN = <GitHub Personal Access Token Anda>
```

```
GOOGLE_CREDENTIALS_JSON = <JSON credentials Google Service Account>
```

### Cara buat GitHub Token (jika belum punya):
1. https://github.com/settings/tokens
2. Generate new token (classic)
3. Pilih scope: `repo` (full control)
4. Copy token

### Cara buat Google Credentials (jika belum punya):
1. https://console.cloud.google.com
2. Create Service Account
3. Download JSON key
4. Copy seluruh isi JSON ke variable

4. Setelah set semua variables, klik **"Redeploy"**

⏳ **Tunggu redeploy selesai**

✅ **Environment variables sudah aktif!**

---

## 5️⃣ TEST APLIKASI

### Langkah:

1. Di Railway, klik **"View Logs"** untuk monitoring
2. Klik tombol **"Open App"** atau copy URL public
3. Aplikasi akan terbuka di browser

### Test Checklist:

- ✅ **Homepage muncul?** 
  - Harus ada greeting "Halo, widodobudi!"
  - Ada 4 suggestion cards

- ✅ **Chat berfungsi?**
  - Ketik pesan: "ini apa"
  - Tekan Enter
  - Harus dapat response dari AI

- ✅ **Upload file berfungsi?**
  - Klik icon Attach
  - Pilih file (gambar/text)
  - Upload berhasil tanpa error

- ✅ **Dropdown model selector?**
  - Klik dropdown di atas (Claude Opus 4.8 / Sonnet 4.6)
  - Bisa ganti model

---

## ⚠️ TROUBLESHOOTING

### Problem 1: Build Failed di Railway

**Gejala:**
```
ERROR: Could not install packages
```

**Solusi:**
- Cek `requirements.txt` formatnya benar (tidak ada typo)
- Pastikan Railway pakai Python 3.12.x (cek `.python-version`)

---

### Problem 2: Error 404 atau "Koneksi error"

**Gejala:**
- Homepage muncul, tapi chat/upload error 404
- Console browser: `POST /chat 404`

**Solusi:**
1. Cek Railway logs:
   - Klik "View Logs"
   - Cari error: `ImportError`, `ModuleNotFoundError`, dll
2. Pastikan `app.py` ada di root repo (bukan di subfolder)
3. Pastikan `templates/index.html` ada (bukan di root)

---

### Problem 3: "Model not found" Error

**Gejala:**
```
Error: Model claude-opus-4-8 is not provided by Crazyrouter
```

**Solusi:**
1. Di Railway Variables, set:
   ```
   AI_MODEL = claude-sonnet-4
   ```
2. Redeploy

---

### Problem 4: Upload Error

**Gejala:**
- Upload file muncul "Upload error"

**Solusi:**
1. Cek folder `uploads/` ada di repo
2. Cek Railway logs untuk error detail
3. Pastikan file size < 10MB

---

### Problem 5: Aplikasi Crash Terus

**Gejala:**
- Railway status: "Crashed"
- Logs: `Application Error`

**Solusi:**
1. Cek Railway logs baris paling atas (root cause error)
2. Biasanya:
   - Missing environment variable → set di Variables
   - Module not found → cek requirements.txt
   - Syntax error di app.py → perbaiki code

---

## 📞 BUTUH BANTUAN LEBIH?

Jika masih error setelah ikuti troubleshooting:

1. **Screenshot:**
   - Railway Deploy Logs (bagian error)
   - Browser Console (F12 → Console tab)
   - Error message yang muncul

2. **Kirim ke AI assistant** dengan info:
   - Kapan error muncul (saat deploy/saat test)
   - Error message lengkap
   - Screenshot logs

---

## ✅ SELESAI!

Jika semua test ✅, aplikasi Anda **SUDAH JALAN SEMPURNA!**

Selamat! 🎉

---

**📝 Catatan:**
- File ini ada di folder `claude-chat-app-clean/`
- Simpan sebagai referensi jika perlu deploy ulang
- Jangan upload file ini ke GitHub (sudah ada di .gitignore)
