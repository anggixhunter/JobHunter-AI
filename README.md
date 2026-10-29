# JobHunter AI

> Dibuat oleh sesama pencari kerja, untuk sesama pencari kerja.

Mencari kerja itu melelahkan. Bukan cuma soal jumlah lowongan, tapi soal waktu: membaca puluhan deskripsi, menilai mana yang benar-benar cocok, lalu menulis ulang CV dan surat lamaran untuk setiap perusahaan — berulang, setiap hari, sering tanpa jawaban.

Saya membuat JobHunter AI karena mengalaminya sendiri. Aplikasi ini mengerjakan bagian yang paling menyita tenaga, supaya Anda bisa fokus pada hal yang benar-benar penting: memutuskan di mana ingin melamar, dan mempersiapkan diri untuk wawancara.

Isinya sederhana — tiga langkah: pahami diri Anda, temukan lowongan yang pantas, siapkan dokumen yang tepat sasaran.

Saya bagikan secara gratis. Semoga sedikit banyak membantu Anda menemukan pekerjaan yang layak, dan semoga masa sulit ini segera berlalu.

## Gratis, dan tetap gratis

Di luar sana, aplikasi seperti ini umumnya berlangganan. Wajar — menjalankannya butuh biaya. Tapi justru orang yang paling butuh bantuan mencari kerja adalah orang yang paling tidak mampu membayar langganan di saat belum punya penghasilan.

Karena itu proyek ini dirancang supaya **tidak ada biaya sepeser pun** untuk memakainya:

| Komponen | Biaya |
|---|---|
| Kode aplikasi | Gratis, sumber terbuka |
| Pencarian lowongan (jobspy + Freehire) | Gratis, tanpa API key |
| AI (Gemini + Groq) | Gratis, dalam kuota harian |
| Penyimpanan data | Lokal di komputer Anda |

Semua data Anda — profil, CV, riwayat lamaran — tersimpan di folder proyek, tidak dikirim ke mana pun selain ke penyedia AI saat menilai lowongan. Tidak ada akun, tidak ada langganan, tidak ada iklan.

---

Asisten pencarian kerja: bangun profil dari CV, cari lowongan dari Indeed/LinkedIn/Freehire, nilai kecocokan pakai AI, lalu siapkan CV + cover letter yang sudah disesuaikan per lowongan. Anda tetap melamar sendiri — aplikasi ini yang menyiapkan bahannya.

## Alur

```
Fase 1 (Profiler)  -> profil_user.json
Fase 2 (Scout)     -> lowongan_cocok.json
Fase 3 (Tailor)    -> PATH_CV/LAMAR/<tanggal>/<perusahaan>_<posisi>/
```

| Fase | Script | Fungsi |
|------|--------|--------|
| 1 | `job_hunter.py` | Baca CV (PDF/DOCX), tanya pengalaman, gabung jadi profil berbahasa Inggris siap ATS |
| 2 | `fase2_scout_v2.py` | Scrape lowongan via `jobspy` (Indeed + LinkedIn) dan Freehire API, nilai skor 0-100 |
| 3 | `fase3_tailor_v2.py` | Scrape detail lowongan, tulis ulang ringkasan + cover letter, ekspor DOCX/PDF |

`main.py` adalah menu utama. Skor bisa di input langsung. Default hanya lowongan dengan skor >= 65 yang masuk database.

Fase 3 berhenti setelah dokumen siap. **Lamaran tetap dikirim manual oleh Anda** — lihat [Fase 3 tidak mengirim lamaran](#fase-3-tidak-mengirim-lamaran--anda-yang-melamar).

## Instalasi

### 0. Prasyarat

**Python 3.10 atau lebih baru** wajib terpasang. Cek dulu:

```bash
python --version
```

Kalau muncul `Python was not found` atau versinya di bawah 3.10:

1. Buka https://www.python.org/downloads/
2. Unduh **Python 3.12** (versi yang stabil dan banyak dipakai library di proyek ini)
3. Jalankan installer, dan **centang "Add python.exe to PATH"** di halaman pertama — ini yang paling sering terlewat
4. Tutup semua terminal, buka baru, cek lagi `python --version`

Tanpa Python, `Run.bat` akan langsung menutup atau menampilkan `'python' is not recognized`.

Selain Python, tidak ada yang perlu dipasang manual — Git hanya diperlukan kalau Anda meng-clone repo. Kalau mengunduh ZIP, lewati langkah `git clone`.

### 1. Unduh proyek

```bash
git clone https://github.com/anggixhunter/JobHunter-AI
cd JobHunter-AI
```

### 2. Siapkan environment

```bash
python -m venv venv
venv\Scripts\activate
```

Prompt terminal akan berubah jadi `(venv)`. Kalau tidak berubah, aktivasi gagal — jangan lanjut.

### 3. Pasang dependensi

```bash
pip install -r requirements.txt
```

Proses ini beberapa menit dan mengunduh cukup banyak paket (`python-jobspy` menarik pandas, numpy, dan lainnya).

### Windows: konversi PDF

`docx2pdf` butuh **Microsoft Word** terpasang. Tanpa Word, output tetap `.docx`.

## Konfigurasi API Key (gratis)

Aplikasi ini memakai **dua** layanan AI, keduanya gratis:

- **Gemini** — model utama (`gemini-3.6-flash`)
- **Groq** — cadangan otomatis kalau Gemini gagal atau kuota habis (`openai/gpt-oss-120b`)

Anda butuh satu key dari masing-masing. Keduanya gratis, cukup daftar dengan akun Google.

Langkah pertama, salin template:

```bash
copy .env.example api_key.env
```

Lalu isi kedua key di bawah ini.

---

### 1. Gemini API Key

1. Buka https://aistudio.google.com/apikey
2. Login dengan akun Google (akun Gmail biasa, tidak perlu kartu kredit)
3. Klik **Create API key** / **Buat API key**
4. Kalau diminta memilih project, pilih **Create new project** — nama bebas
5. Salin key yang muncul (diawali `AIza...`)

Tempel ke `api_key.env`:

```
GEMINI_API_KEY=AIza...
```

**Kuota gratis:** level gratis Gemini cukup untuk ratusan penilaian lowongan per hari. Kalau habis, error akan muncul di log dan aplikasi otomatis pindah ke Groq — jadi tidak berhenti.

---

### 2. Groq API Key

1. Buka https://console.groq.com/keys
2. Login dengan Google atau GitHub
3. Klik **Create API Key**
4. Beri nama (misal `jobhunter`), lalu **Submit**
5. Salin key yang muncul (diawali `gsk_...`) — **hanya ditampilkan sekali**, simpan baik-baik

Tempel ke `api_key.env`:

```
GROQ_API_KEY=gsk_...
```

**Kuota gratis:** Groq memberi kuota harian gratis dengan batas per menit yang cukup untuk keperluan pribadi. Kalau kena batas, tunggu semenit lalu jalankan ulang.

---

### 3. Verifikasi

```bash
python TesAPI.py
```

Harus muncul:

```
✅ Groq API Key : MASIH BERFUNGSI (Aktif)
✅ Gemini API Key: MASIH BERFUNGSI (Aktif)
✅ jobspy       : BERFUNGSI
```

Kalau ada yang merah, periksa lagi key-nya (spasi di ujung, key terpotong, atau sudah kedaluwarsa).

---

### Ringkasan

| Key | Wajib | Biaya | Batas gratis |
|-----|-------|-------|--------------|
| `GEMINI_API_KEY` | ya | Rp 0 | Ratusan request/hari |
| `GROQ_API_KEY` | ya | Rp 0 | Kuota harian |
| jobspy | tidak perlu | Rp 0 | — |
| Freehire | tidak perlu | Rp 0 | — |

> **Jangan pernah** membagikan file `api_key.env` ke siapa pun atau mengunggahnya ke GitHub. File ini sudah masuk `.gitignore`, tapi tetap periksa sebelum `git push`.

---

### Folder CV

Taruh file CV (`.pdf` / `.docx`) di `PATH_CV/`. Fase 1 akan memindai folder ini otomatis.

## Struktur Proyek

```
Seeker-GIT/
├── main.py                  # Menu utama (orchestrator)
├── job_hunter.py            # Fase 1 - Profiler
├── fase2_scout_v2.py        # Fase 2 - Scout
├── fase3_tailor_v2.py       # Fase 3 - Tailor
├── TesAPI.py                # Cek status API key & jobspy
├── cek_model.py             # Daftar model AI yang tersedia
├── cek_freehire.py          # Uji pencarian Freehire
├── Run.bat                  # Launcher Windows
├── requirements.txt
├── .env.example             # Template API key
├── api_key.env              # Key Anda (tidak ikut repo)
├── PATH_CV/                 # Taruh CV di sini
│   ├── .gitkeep
│   └── LAMAR/               # Output Fase 3 (dibuat otomatis)
├── profil_user.json         # Hasil Fase 1 (tidak ikut repo)
└── lowongan_cocok.json      # Database lowongan (tidak ikut repo)
```

## Menjalankan

```
Run.bat
```

atau:

```bash
python main.py
```

### Menu

| No | Aksi |
|----|------|
| 1 | Fase 1 — buat/ubah profil, baca CV |
| 2 | Fase 2 — cari lowongan baru |
| 3 | Fase 3 — buat dokumen untuk lowongan pending |
| 4 | Auto-pilot — Fase 2 lalu Fase 3 |
| 5 | Lihat detail lowongan |
| 6 | Update status (`pending` / `applied` / `not_suitable` / `rejected`) |
| 7 | Arsipkan lowongan `not_suitable` + `rejected` ke `lowongan_archive_YYYY-MM.json` |

Status lowongan menentukan Fase 3: hanya `pending` yang diproses. Fase 3 hanya menyiapkan dokumen — lamaran dikirim manual, lalu ubah statusnya ke `applied` lewat menu `[6]`.

## Output Fase 3

```
PATH_CV/LAMAR/2026-10-20/Xendit_Merchant_T/
├── CV_<nama>_<posisi>.pdf
├── Resume_<nama>.pdf          # cover letter
├── Email_Body_<perusahaan>.txt
└── info_loker.txt             # berisi URL lowongan asli
```

Semua file ini adalah bahan untuk Anda kirim sendiri. Tidak ada lamaran yang terkirim otomatis.

## Fase 3 tidak mengirim lamaran — Anda yang melamar

Fase 3 berhenti di penyiapan dokumen. Folder `<perusahaan>_<posisi>/` sudah berisi CV, cover letter, email body, dan info lowongan yang siap pakai — tapi **tidak ada yang dikirim ke mana pun**.

Melamar tetap dilakukan manual:

1. Buka `info_loker.txt` untuk URL lowongan aslinya
2. Buka URL tersebut, unggah CV dari folder itu, tempel cover letter
3. Kalau lowongan minta lamaran via email, salin teks dari `Email_Body_<perusahaan>.txt`
4. Setelah benar-benar terkirim, ubah status di menu `[6]` menjadi `applied`

**Kenapa tidak otomatis?** Setiap portal kerja (LinkedIn, JobStreet, Glints, Indeed, situs karir perusahaan) punya formulir, login, dan CAPTCHA sendiri. Mengotomatiskan pelamaran berarti membeli layanan browser/proxy berbayar, dan sebagian besar portal melarangnya di ToS. Itu bertentangan dengan dua hal yang dipegang proyek ini: nol biaya, dan tidak membuat akun Anda berisiko diblokir.

Fase 3 menghemat bagian yang paling melelahkan — menulis ulang CV dan surat lamaran per lowongan. Sisanya, beberapa menit klik dan unggah per lamaran, tetap di tangan Anda.

## Struktur Data

`profil_user.json` — hasil Fase 1. Field utama: `posisi_target`, `hard_skills`, `pencapaian_kunci`, `cv_mentah`.

`lowongan_cocok.json` — daftar lowongan. Field penting: `url`, `skor`, `alasan`, `status`, `tanggal_ditemukan`.

Keduanya masuk `.gitignore` karena berisi data pribadi. **Setelah clone, kedua file ini belum ada** — jalankan menu `[1]` (Fase 1) sekali untuk membuat `profil_user.json`, lalu menu `[2]` (Fase 2) untuk mengisi `lowongan_cocok.json`.

Untuk melihat bentuk datanya, ada `profil_user.example.json` dan `lowongan_cocok.example.json` — isinya dummy, bukan data siapa pun.

## Catatan & Troubleshooting

### Umum

- **LinkedIn 429** — IP residensial cepat diblokir LinkedIn. Indeed + Freehire tetap jalan. Atur jeda di `JEDA_DETIK`, atau isi `PROXY` di `api_key.env` kalau punya proxy. LinkedIn otomatis dimatikan untuk sesi itu kalau tetap kena.
- **Glassdoor & Google** — tidak didukung untuk Indonesia, hasil selalu kosong. Sengaja dimatikan.
- **Hasil lowongan sedikit** — perlebar `posisi_target` di profil, atau naikkan `JRESULT` / `JRESULT2` di `fase2_scout_v2.py`.
- **Model Gemini 404** — nama model berubah. Jalankan `python cek_model.py` untuk daftar model valid yang tersedia untuk key Anda.

### CV non-ATS

Parser `parse_cv()` membaca CV berdasarkan heading section (`Professional Experience`, `Key Skills`, `Education`, dst). CV dengan layout kolom, tabel, atau grafis akan menghasilkan teks PDF yang berantakan.

Gejalanya: CV hasil Fase 3 hanya berisi ringkasan, pengalaman kosong.

Solusi:

1. Set `DEBUG_CV = True` di `fase3_tailor_v2.py`
2. Jalankan Fase 3, lihat isi `cv_parsed_debug.json`
3. Perbaiki CV jadi format satu kolom dengan heading standar, atau andalkan `cv_mentah` di profil

### Error saat instalasi

| Error | Penyebab | Solusi |
|---|---|---|
| `'python' is not recognized` | Python belum terpasang atau tidak masuk PATH | Install ulang dari python.org, centang "Add python.exe to PATH" |
| `ModuleNotFoundError: No module named 'groq'` | venv tidak aktif | `venv\Scripts\activate` lalu `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'jobspy'` | terinstal di Python lain | aktifkan venv dulu, baru `pip install python-jobspy` |
| `name 'load_dotenv' is not defined` | import hilang | `pip install python-dotenv` |
| `docx2pdf` gagal convert | Microsoft Word tidak ada | output tetap `.docx`, buka manual |
| `PermissionError` saat convert PDF | file sedang terbuka di Word | tutup file lalu ulangi |

### Kuota AI habis

Tanda: log menampilkan `⚠️ Gemini: Gagal` terus-menerus, lalu `❌ Error AI: Kedua AI gagal`.

- Gemini: kuota gratis direset per hari
- Groq: dibatasi per menit dan per hari

Kalau keduanya habis, tunggu beberapa jam. Tidak ada biaya yang muncul — aplikasi hanya berhenti menilai.

---

## Berkontribusi

Pull request, laporan bug, dan saran fitur sangat diterima. Kalau aplikasi ini membantu Anda, bagikan ke teman yang sedang mencari kerja — itu sudah cukup sebagai balas budi.

### Sumber data lowongan

Proyek ini bergantung pada dua layanan pihak ketiga yang **tidak** dikelola oleh saya:

| Sumber | Jenis | Catatan |
|---|---|---|
| [jobspy](https://github.com/speedyapply/JobSpy) | Library open source | Membaca Indeed & LinkedIn. Kalau situs mengubah struktur halaman, scraper bisa rusak sampai library diperbarui. |
| [Freehire](https://freehire.me) | API publik, tanpa key | Tidak ada dokumentasi resmi atau janji ketersediaan. Endpoint bisa berubah sewaktu-waktu. |

Konsekuensinya:

- **Bukan layanan yang bisa dijamin.** Kalau salah satu mati, Fase 2 tetap jalan dengan sumber yang tersisa — cukup lebih sedikit hasil.
- **Jangan buka issue soal 429 atau hasil kosong dari Indeed/LinkedIn.** Itu pembatasan dari situsnya, bukan bug aplikasi. Solusinya proxy atau jeda waktu.
- **Jangan menambahkan API key berbayar** (SerpAPI, Bright Data, dan sejenisnya) sebagai default. Proyek ini harus tetap nol biaya; kalau ingin memakai proxy, sediakan lewat variabel `PROXY` yang opsional.

Kalau menemukan sumber lowongan gratis lain yang stabil, usulkan dulu lewat issue sebelum membuat PR.

## Dukungan

Aplikasi ini gratis dan akan tetap gratis. Kalau Anda ingin membalas sedikit, donasi sepenuhnya sukarela dan dipakai untuk biaya operasional (domain, kopi saat memperbaiki bug).

- **Trakteer** — https://trakteer.id/anggi_linden (QRIS, GoPay, OVO, DANA, transfer bank)
- Tombol **Sponsor** juga ada di kanan atas halaman repo ini.

Terima kasih sudah memakai. Semoga lekas dapat kerja.

---

## Lisensi

MIT — bebas dipakai, diubah, dan dibagikan.

---

## Disclaimer

Scraping Indeed/LinkedIn melanggar ToS mereka. Gunakan untuk pemakaian pribadi dengan volume wajar. Aplikasi ini tidak menjamin Anda mendapat pekerjaan; ia hanya menghemat waktu Anda dalam mencari.
